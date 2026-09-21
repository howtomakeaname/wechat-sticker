#!/usr/bin/env python3
"""Local PNG inspection, proportional export and 3×3 slicing. No generation or matting."""

import argparse
import json
import sys
from pathlib import Path

from PIL import Image, ImageColor, ImageOps


PROFILES = {"grid": None, "banner": (750, 400), "cover": (240, 240)}


class ValidationFailure(ValueError):
    """A readable input does not meet an asset requirement."""


def alpha_stats(image):
    alpha = image.convert("RGBA").getchannel("A")
    histogram = alpha.histogram()
    total = image.width * image.height
    return {
        "has_alpha_channel": "A" in image.getbands() or "transparency" in image.info,
        "has_transparency": histogram[255] < total,
        "transparent_pixels": histogram[0],
        "partial_alpha_pixels": sum(histogram[1:255]),
        "opaque_pixels": histogram[255],
        "visible_pixels": total - histogram[0],
        "alpha_content_bbox": alpha.getbbox(),
    }


def target_size(args, required=False):
    width, height = args.width, args.height
    if (width is None) != (height is None):
        raise ValueError("--width and --height must be supplied together")
    size = (width, height) if width is not None else PROFILES.get(args.profile)
    if size and min(size) <= 0:
        raise ValueError("Dimensions must be positive")
    if required and not size:
        raise ValueError("Export needs --width/--height or a banner/cover profile")
    return size


def inspect_file(path, args):
    expected = target_size(args)
    if args.max_kb is not None and args.max_kb <= 0:
        raise ValueError("--max-kb must be positive")
    with Image.open(path) as image:
        image.load()
        stats = alpha_stats(image)
        report = {
            "path": str(path), "format": image.format, "mode": image.mode,
            "width": image.width, "height": image.height,
            "bytes": path.stat().st_size,
            "frames": getattr(image, "n_frames", 1), **stats,
        }
    errors, notes = [], []
    if report["format"] != "PNG":
        errors.append("Expected PNG format")
    if report["frames"] != 1:
        errors.append("This workflow expects a static single-frame image")
    if expected and (report["width"], report["height"]) != expected:
        errors.append("Expected dimensions: {}×{}".format(*expected))
    if args.profile == "grid" and report["width"] != report["height"]:
        errors.append("A grid sheet should be square")
    if report["visible_pixels"] == 0:
        errors.append("Image is fully transparent and has no visible content")
    if args.require_transparent or args.profile == "cover":
        if report["transparent_pixels"] == 0:
            errors.append("No fully transparent pixels; a background cutout is required")
        notes.append("Visually inspect background residue, white halos and subject edges")
    limit = args.max_kb if args.max_kb is not None else (500 if args.profile == "cover" else None)
    if limit is not None and report["bytes"] > limit * 1000:
        notes.append("Exceeds {} KB; the platform may compress it".format(limit))
    report.update(ok=not errors, errors=errors, warnings=notes)
    return report


def load_static(path):
    with Image.open(path) as source:
        if getattr(source, "n_frames", 1) != 1:
            raise ValidationFailure("Animated input is not supported; supply one static frame")
        return ImageOps.exif_transpose(source).convert("RGBA")


def ensure_destination(source, destination, force):
    if destination.suffix.lower() != ".png":
        raise ValueError("Output must use a .png extension")
    if source.resolve() == destination.resolve() or (destination.exists() and source.samefile(destination)):
        raise ValueError("Output must not replace the input image, even with --force")
    if destination.is_dir():
        raise ValueError("Output path is a directory")
    if destination.exists() and not force:
        raise FileExistsError("Output exists; choose a new path or explicitly use --force")


def write_png(image, path, force):
    path.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation by default prevents accidental overwrites between checks.
    with path.open("wb" if force else "xb") as stream:
        image.save(stream, format="PNG", optimize=True)


def color_rgba(value):
    return (0, 0, 0, 0) if value == "transparent" else ImageColor.getcolor(value, "RGBA")


def export_image(args):
    size = target_size(args, required=True)
    # Validate all check options before creating any output.
    if args.max_kb is not None and args.max_kb <= 0:
        raise ValueError("--max-kb must be positive")
    if args.profile == "grid" and size[0] != size[1]:
        raise ValueError("Grid export must be square")
    for anchor in (args.anchor_x, args.anchor_y):
        if not 0 <= anchor <= 1:
            raise ValueError("Anchor values must be between 0 and 1")
    cover = args.profile == "cover"
    fit = args.fit or ("contain" if cover else "crop")
    padding = args.padding if args.padding is not None else (3 if cover else 0)
    if padding < 0 or 2 * padding >= min(size):
        raise ValueError("Padding must leave a positive inner canvas")
    if fit == "crop" and padding:
        raise ValueError("--padding is supported only with --fit contain")
    if cover and fit != "contain":
        raise ValueError("Cover exports use contain to preserve the full silhouette")
    background = color_rgba(args.background or ("transparent" if cover else "#EAF3FF"))
    if cover and background[3] != 0:
        raise ValueError("Cover exports need a transparent background")
    ensure_destination(args.input, args.output, args.force)
    image = load_static(args.input)
    stats = alpha_stats(image)
    if not stats["visible_pixels"]:
        raise ValidationFailure("Source has no visible content")
    if cover or args.require_transparent:
        if not stats["transparent_pixels"]:
            raise ValidationFailure("Source has no fully transparent background; this tool does not remove backgrounds")
    if cover:
        image = image.crop(stats["alpha_content_bbox"])
    if fit == "crop":
        result = ImageOps.fit(image, size, method=Image.Resampling.LANCZOS,
                              centering=(args.anchor_x, args.anchor_y))
    else:
        inner = (size[0] - 2 * padding, size[1] - 2 * padding)
        scaled = ImageOps.contain(image, inner, method=Image.Resampling.LANCZOS)
        result = Image.new("RGBA", size, background)
        offset = ((size[0] - scaled.width) // 2, (size[1] - scaled.height) // 2)
        result.alpha_composite(scaled, offset)
    final_stats = alpha_stats(result)
    if not final_stats["visible_pixels"]:
        raise ValidationFailure("Export would be empty; adjust the crop or use contain")
    if (cover or args.require_transparent) and not final_stats["transparent_pixels"]:
        raise ValidationFailure("Export would lose the transparent background; adjust the layout")
    write_png(result, args.output, args.force)
    return inspect_file(args.output, args)


def split_grid(args):
    image = load_static(args.input)
    width, height = image.size
    if args.boxes:
        boxes = json.loads(args.boxes.read_text(encoding="utf-8"))
    else:
        if min(image.size) < 3:
            raise ValueError("Image is too small for a 3×3 grid")
        xs = [i * width // 3 for i in range(4)]
        ys = [i * height // 3 for i in range(4)]
        boxes = [[xs[c], ys[r], xs[c + 1], ys[r + 1]]
                 for r in range(3) for c in range(3)]
    if not isinstance(boxes, list) or len(boxes) != 9:
        raise ValueError("--boxes must contain exactly nine pixel rectangles")
    for box in boxes:
        if not isinstance(box, list) or len(box) != 4 or any(type(v) is not int for v in box):
            raise ValueError("Each rectangle must be four integer coordinates")
        left, top, right, bottom = box
        if not (0 <= left < right <= width and 0 <= top < bottom <= height):
            raise ValueError("Rectangle is empty or outside the image: {}".format(box))
    for index, box in enumerate(boxes):
        for other in boxes[:index]:
            if max(box[0], other[0]) < min(box[2], other[2]) and max(box[1], other[1]) < min(box[3], other[3]):
                raise ValueError("Crop rectangles must not overlap")
    outputs = [args.output_dir / "sticker-{:02d}.png".format(i) for i in range(1, 10)]
    # Preflight every target before writing the first file.
    for path in outputs:
        ensure_destination(args.input, path, args.force)
    for path, box in zip(outputs, boxes):
        write_png(image.crop(box), path, args.force)
    return {"ok": True, "files": [str(p) for p in outputs], "boxes": boxes,
            "warnings": ["Cropping preserves backgrounds and borders; inspect each tile"]}


class JsonParser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError(message)


def parser():
    root = JsonParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)
    check = commands.add_parser("check", help="Inspect and validate a static PNG")
    export = commands.add_parser("export", help="Export a new PNG without stretching")
    for command in (check, export):
        command.add_argument("input", type=Path)
        command.add_argument("--profile", choices=list(PROFILES))
        command.add_argument("--width", type=int)
        command.add_argument("--height", type=int)
        command.add_argument("--require-transparent", action="store_true")
        command.add_argument("--max-kb", type=int)
    export.add_argument("output", type=Path)
    export.add_argument("--fit", choices=["crop", "contain"])
    export.add_argument("--background", help="Pillow color string or transparent")
    export.add_argument("--padding", type=int)
    export.add_argument("--anchor-x", type=float, default=0.5)
    export.add_argument("--anchor-y", type=float, default=0.5)
    export.add_argument("--force", action="store_true")
    split = commands.add_parser("split-grid", help="Crop nine tiles, without background removal")
    split.add_argument("input", type=Path)
    split.add_argument("output_dir", type=Path)
    split.add_argument("--boxes", type=Path)
    split.add_argument("--force", action="store_true")
    return root


def main(argv=None):
    try:
        args = parser().parse_args(argv)
        if args.command == "check":
            result = inspect_file(args.input, args)
        elif args.command == "export":
            result = export_image(args)
        else:
            result = split_grid(args)
        code = 0 if result["ok"] else 1
    except ValidationFailure as exc:
        result, code = {"ok": False, "errors": [str(exc)]}, 1
    except (OSError, ValueError, Image.DecompressionBombError) as exc:
        result, code = {"ok": False, "errors": [str(exc)]}, 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    sys.exit(main())
