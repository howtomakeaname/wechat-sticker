#!/usr/bin/env python3
"""Remove a flat colored card background from one sticker tile, keep the subject.

Deterministic local matting for the workflow's own grid style: a near-uniform
light card background around a subject with a light outline. Only Pillow is
used. The method is border-connected background flooding on an eroded
background mask, so background-colored regions enclosed by the subject outline
are never touched unless a gap wider than the erosion kernel exists.

It cannot understand semantics: a light prop (pillow, sleeve) whose color is
close to the background and which touches the image edge is background to this
tool. Use --protect rectangles for those, and always inspect the preview.
"""

import argparse
import json
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter


class ValidationFailure(ValueError):
    """A readable input does not meet an asset requirement."""


def parse_zone(text):
    try:
        parts = [int(v) for v in text.split(",")]
    except ValueError:
        raise ValueError("--protect needs four integers: x0,y0,x1,y1")
    if len(parts) != 4:
        raise ValueError("--protect needs four integers: x0,y0,x1,y1")
    x0, y0, x1, y1 = parts
    if not (x0 < x1 and y0 < y1):
        raise ValueError("--protect rectangle is empty: {}".format(text))
    return parts


def sample_background(image):
    """Pick the bluest of the four near-corner pixels as the card color."""
    points = [(5, 5), (image.width - 6, 5), (5, image.height - 6),
              (image.width - 6, image.height - 6)]
    candidates = [image.getpixel(p)[:3] for p in points]
    return max(candidates, key=lambda c: c[2] - c[0])


def background_mask(image, blue_diff, min_blue):
    """Mask (L, 255=True) of background-colored pixels: blue cast and bright."""
    r, _, b, _ = image.convert("RGBA").split()
    # 128 + (b - r), clipped to [0, 255]
    diff = ImageChops.subtract(b, r, scale=1.0, offset=128)
    cast = diff.point(lambda v: 255 if v > 128 + blue_diff else 0)
    bright = b.point(lambda v: 255 if v > min_blue else 0)
    return ImageChops.multiply(cast, bright)


def flood_exterior(mask):
    """Fill the border-connected True region of a 0/255 L mask; return it."""
    seeded = mask.copy()
    if seeded.getpixel((0, 0)) != 255:
        raise ValidationFailure(
            "Padded corner is not background-colored; check --blue-diff/--min-blue")
    ImageDraw.floodfill(seeded, (0, 0), 128)
    return seeded.point(lambda v: 255 if v == 128 else 0)


def cutout(image, blue_diff=10, min_blue=190, erode=2, grow=None, pad=10,
           zones=(), feather=0.8):
    if erode < 1:
        raise ValueError("--erode must be >= 1 to block thin leak gaps")
    grow = erode + 1 if grow is None else grow
    if grow < erode:
        raise ValueError("--grow must be >= --erode or the rim is left behind")
    background = sample_background(image)
    padded = Image.new("RGBA", (image.width + 2 * pad, image.height + 2 * pad),
                       background + (255,))
    padded.paste(image, (pad, pad))

    weak = background_mask(padded, blue_diff, min_blue)
    # Erosion closes thin leak gaps (hairline breaks in the white outline) so
    # the flood cannot reach background-colored regions inside the subject.
    eroded = weak.filter(ImageFilter.MinFilter(2 * erode + 1))
    exterior = flood_exterior(eroded)
    grown = exterior.filter(ImageFilter.MaxFilter(2 * grow + 1))
    exterior = ImageChops.lighter(ImageChops.multiply(grown, weak), exterior)

    foreground = ImageChops.invert(exterior)
    for x0, y0, x1, y1 in zones:
        zone = Image.new("L", padded.size, 0)
        ImageDraw.Draw(zone).rectangle((x0 + pad, y0 + pad, x1 + pad - 1, y1 + pad - 1),
                                       fill=255)
        foreground = ImageChops.lighter(foreground, ImageChops.multiply(zone, weak))

    foreground = foreground.filter(ImageFilter.MinFilter(3))
    alpha = foreground.filter(ImageFilter.GaussianBlur(feather)) if feather else foreground
    result = padded.copy()
    result.putalpha(alpha)
    return result, background


def checkerboard_preview(image, square=24):
    board = Image.new("RGB", image.size)
    draw = ImageDraw.Draw(board)
    for y in range(0, image.height, square):
        for x in range(0, image.width, square):
            shade = 200 if (x // square + y // square) % 2 == 0 else 150
            draw.rectangle((x, y, x + square - 1, y + square - 1),
                           fill=(shade, shade, shade))
    board.paste(image, (0, 0), image)
    return board


def ensure_destination(source, destination, force):
    if destination.suffix.lower() != ".png":
        raise ValueError("Output must use a .png extension")
    if source.resolve() == destination.resolve() or (destination.exists() and source.samefile(destination)):
        raise ValueError("Output must not replace the input image, even with --force")
    if destination.exists() and not force:
        raise FileExistsError("Output exists; choose a new path or explicitly use --force")


def alpha_stats(image):
    histogram = image.getchannel("A").histogram()
    total = image.width * image.height
    return {
        "transparent_pixels": histogram[0],
        "partial_alpha_pixels": sum(histogram[1:255]),
        "opaque_pixels": histogram[255],
        "visible_pixels": total - histogram[0],
    }


def run(args):
    zones = [parse_zone(z) for z in args.protect]
    with Image.open(args.input) as source:
        if getattr(source, "n_frames", 1) != 1:
            raise ValidationFailure("Animated input is not supported; supply one static frame")
        image = source.convert("RGBA")
    if min(image.size) < 16:
        raise ValidationFailure("Input is too small to cut out")
    ensure_destination(args.input, args.output, args.force)
    if args.preview:
        ensure_destination(args.input, args.preview, args.force)

    result, background = cutout(image, blue_diff=args.blue_diff,
                                min_blue=args.min_blue, erode=args.erode,
                                grow=args.grow, pad=args.pad, zones=zones)
    stats = alpha_stats(result)
    errors, warnings = [], []
    if stats["transparent_pixels"] == 0:
        errors.append("No background was removed; inspect the tile and thresholds")
    if stats["visible_pixels"] < result.width * result.height * 0.05:
        warnings.append("Very little content left; the subject may have been eaten")
    if zones:
        warnings.append("Protect zones were applied; inspect them for residue")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("wb" if args.force else "xb") as stream:
        result.save(stream, format="PNG", optimize=True)
    if args.preview:
        args.preview.parent.mkdir(parents=True, exist_ok=True)
        with args.preview.open("wb" if args.force else "xb") as stream:
            checkerboard_preview(result).save(stream, format="PNG", optimize=True)
    return {
        "ok": not errors, "output": str(args.output),
        "preview": str(args.preview) if args.preview else None,
        "width": result.width, "height": result.height,
        "background_color": list(background),
        "erode": args.erode, "protect_zones": zones,
        **stats, "errors": errors, "warnings": warnings,
    }


class JsonParser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError(message)


def parser():
    root = JsonParser(description=__doc__)
    root.add_argument("input", type=Path)
    root.add_argument("output", type=Path)
    root.add_argument("--blue-diff", type=int, default=10,
                      help="background needs blue-red channel difference above this")
    root.add_argument("--min-blue", type=int, default=190,
                      help="background needs a blue channel above this")
    root.add_argument("--erode", type=int, default=2,
                      help="mask erosion iterations; raise to block wider leak gaps")
    root.add_argument("--grow", type=int, help="dilation after flooding; default erode+1")
    root.add_argument("--pad", type=int, default=10,
                      help="background-colored padding added before flooding")
    root.add_argument("--protect", action="append", default=[], metavar="X0,Y0,X1,Y1",
                      help="rectangle (input coords) whose pixels are never removed")
    root.add_argument("--preview", type=Path, help="write a checkerboard preview PNG")
    root.add_argument("--force", action="store_true")
    return root


def main(argv=None):
    try:
        result = run(parser().parse_args(argv))
        code = 0 if result["ok"] else 1
    except ValidationFailure as exc:
        result, code = {"ok": False, "errors": [str(exc)]}, 1
    except (OSError, ValueError, Image.DecompressionBombError) as exc:
        result, code = {"ok": False, "errors": [str(exc)]}, 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    sys.exit(main())
