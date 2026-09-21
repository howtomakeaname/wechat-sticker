import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("image_assets", ROOT / "scripts" / "image_assets.py")
tool = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(tool)


class ImageAssetsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def save(self, image, name="input.png", **kwargs):
        path = self.directory / name
        image.save(path, **kwargs)
        return path

    def run_tool(self, *args):
        with contextlib.redirect_stdout(io.StringIO()) as stream:
            code = tool.main([str(arg) for arg in args])
        return code, json.loads(stream.getvalue())

    def transparent_subject(self, size=(120, 120)):
        image = Image.new("RGBA", size, (0, 0, 0, 0))
        ImageDraw.Draw(image).ellipse((20, 10, 100, 110), fill=(100, 150, 245, 255))
        ImageDraw.Draw(image).ellipse((45, 40, 60, 55), fill="white")
        return image

    def test_opaque_checkerboard_and_fake_alpha_fail_cover_check(self):
        board = Image.new("RGB", (240, 240), "#999999")
        draw = ImageDraw.Draw(board)
        for row in range(0, 240, 10):
            for col in range(0, 240, 10):
                if (row + col) % 20 == 0:
                    draw.rectangle((col, row, col + 9, row + 9), fill="#cccccc")
        for mode in ("RGB", "RGBA"):
            with self.subTest(mode=mode):
                path = self.save(board.convert(mode), mode + ".png")
                code, result = self.run_tool("check", path, "--profile", "cover")
                self.assertEqual(code, 1)
                self.assertFalse(result["has_transparency"])
                self.assertEqual(result["has_alpha_channel"], mode == "RGBA")

    def test_empty_or_uniform_semitransparent_cover_fails(self):
        for alpha in (0, 128):
            with self.subTest(alpha=alpha):
                path = self.save(Image.new("RGBA", (240, 240), (12, 34, 56, alpha)))
                code, _ = self.run_tool("check", path, "--profile", "cover")
                self.assertEqual(code, 1)

    def test_palette_transparency_is_recognized(self):
        image = Image.new("P", (240, 240), 0)
        image.putpalette([0, 0, 0, 100, 150, 245] + [0] * (768 - 6))
        ImageDraw.Draw(image).rectangle((40, 30, 200, 210), fill=1)
        path = self.save(image, transparency=0)
        code, result = self.run_tool("check", path, "--profile", "cover")
        self.assertEqual(code, 0)
        self.assertTrue(result["has_alpha_channel"])
        self.assertGreater(result["transparent_pixels"], 0)

    def test_cover_export_preserves_alpha_subject_and_original(self):
        path = self.save(self.transparent_subject())
        original = path.read_bytes()
        output = self.directory / "cover.png"
        code, result = self.run_tool("export", path, output, "--profile", "cover")
        self.assertEqual(code, 0, result)
        self.assertEqual((result["width"], result["height"]), (240, 240))
        self.assertGreater(result["partial_alpha_pixels"], 0)
        self.assertGreater(result["opaque_pixels"], 0)
        self.assertGreater(result["transparent_pixels"], 0)
        self.assertEqual(result["alpha_content_bbox"][1], 3)
        self.assertEqual(result["alpha_content_bbox"][3], 237)
        with Image.open(output) as image:
            self.assertEqual(image.getpixel((0, 0))[3], 0)
            self.assertGreater(sum(1 for r, g, b, a in image.getdata()
                                   if min(r, g, b) > 250 and a == 255), 0)
        self.assertEqual(path.read_bytes(), original)

    def test_cover_rejects_opaque_source_before_creating_output(self):
        path = self.save(Image.new("RGB", (100, 100), "white"))
        output = self.directory / "cover.png"
        code, _ = self.run_tool("export", path, output, "--profile", "cover")
        self.assertEqual(code, 1)
        self.assertFalse(output.exists())

    def test_banner_contain_does_not_stretch_and_is_exact_size(self):
        path = self.save(Image.new("RGBA", (100, 100), "red"))
        output = self.directory / "banner.png"
        code, result = self.run_tool("export", path, output, "--profile", "banner", "--fit", "contain", "--background", "#001122")
        self.assertEqual(code, 0, result)
        with Image.open(output) as image:
            self.assertEqual(image.size, (750, 400))
            self.assertEqual(image.getpixel((174, 200)), (0, 17, 34, 255))
            self.assertEqual(image.getpixel((175, 200)), (255, 0, 0, 255))
            self.assertEqual(image.getpixel((574, 200)), (255, 0, 0, 255))
            self.assertEqual(image.getpixel((575, 200)), (0, 17, 34, 255))

    def test_banner_crop_uses_selected_anchor(self):
        image = Image.new("RGB", (1500, 400), "red")
        ImageDraw.Draw(image).rectangle((750, 0, 1499, 399), fill="blue")
        path = self.save(image)
        output = self.directory / "banner.png"
        code, result = self.run_tool("export", path, output, "--profile", "banner", "--anchor-x", "1")
        self.assertEqual(code, 0, result)
        with Image.open(output) as image:
            self.assertEqual(image.getpixel((375, 200)), (0, 0, 255, 255))

    def test_existing_output_and_input_are_preserved(self):
        path = self.save(self.transparent_subject())
        original = path.read_bytes()
        output = self.save(Image.new("RGBA", (20, 20), "red"), "existing.png")
        existing = output.read_bytes()
        code, _ = self.run_tool("export", path, output, "--profile", "cover")
        self.assertEqual(code, 2)
        self.assertEqual(output.read_bytes(), existing)
        code, _ = self.run_tool("export", path, path, "--profile", "cover", "--force")
        self.assertEqual(code, 2)
        self.assertEqual(path.read_bytes(), original)
        code, _ = self.run_tool("export", path, output, "--profile", "cover", "--force")
        self.assertEqual(code, 0)

    def test_grid_split_covers_every_pixel_for_non_divisible_dimensions(self):
        source = Image.new("RGBA", (10, 11))
        source.putdata([(x * 20, y * 20, 100, 255) for y in range(11) for x in range(10)])
        path = self.save(source)
        output = self.directory / "tiles"
        code, result = self.run_tool("split-grid", path, output)
        self.assertEqual(code, 0)
        self.assertEqual(len(result["files"]), 9)
        rebuilt = Image.new("RGBA", source.size)
        for filename, box in zip(result["files"], result["boxes"]):
            with Image.open(filename) as tile:
                rebuilt.paste(tile, (box[0], box[1]))
        self.assertEqual(rebuilt.tobytes(), source.tobytes())

    def test_split_checks_all_destinations_before_writing(self):
        path = self.save(Image.new("RGB", (30, 30), "red"))
        output = self.directory / "tiles"
        output.mkdir()
        existing = output / "sticker-09.png"
        Image.new("RGB", (1, 1), "blue").save(existing)
        code, _ = self.run_tool("split-grid", path, output)
        self.assertEqual(code, 2)
        self.assertEqual(list(output.iterdir()), [existing])

    def test_explicit_grid_boxes_can_skip_gutters(self):
        path = self.save(Image.new("RGBA", (34, 34), (10, 20, 30, 128)))
        boxes = [[c * 12, r * 12, c * 12 + 10, r * 12 + 10]
                 for r in range(3) for c in range(3)]
        boxes_file = self.directory / "boxes.json"
        boxes_file.write_text(json.dumps(boxes), encoding="utf-8")
        code, result = self.run_tool("split-grid", path, self.directory / "tiles", "--boxes", boxes_file)
        self.assertEqual(code, 0)
        with Image.open(result["files"][0]) as tile:
            self.assertEqual(tile.size, (10, 10))
            self.assertEqual(tile.getpixel((0, 0))[3], 128)

    def test_invalid_boxes_do_not_create_tiles(self):
        path = self.save(Image.new("RGB", (30, 30), "red"))
        output = self.directory / "tiles"
        for boxes in ([[0, 0, 2, 2]] * 9, [[0, 0, 31, 10]] * 9, []):
            boxes_file = self.directory / "boxes.json"
            boxes_file.write_text(json.dumps(boxes), encoding="utf-8")
            code, _ = self.run_tool("split-grid", path, output, "--boxes", boxes_file)
            self.assertEqual(code, 2)
            self.assertFalse(output.exists())

    def test_size_limit_is_warning_and_dimensions_can_be_overridden(self):
        path = self.save(self.transparent_subject((300, 300)))
        code, result = self.run_tool("check", path, "--profile", "cover", "--width", "300", "--height", "300", "--max-kb", "1")
        self.assertEqual(code, 0)
        self.assertTrue(any("Exceeds" in warning for warning in result["warnings"]))

    def test_grid_profile_rejects_non_square_image(self):
        path = self.save(Image.new("RGB", (30, 40), "red"))
        code, result = self.run_tool("check", path, "--profile", "grid")
        self.assertEqual(code, 1)
        self.assertTrue(result["errors"])

    def test_wrong_format_dimensions_and_arguments(self):
        path = self.save(Image.new("RGB", (100, 100), "red"), "input.jpg")
        code, result = self.run_tool("check", path, "--profile", "banner")
        self.assertEqual(code, 1)
        self.assertEqual(len(result["errors"]), 2)
        for options in (("--width", "240"), ("--max-kb", "-1"), ("--profile", "unknown")):
            code, _ = self.run_tool("check", path, *options)
            self.assertEqual(code, 2)

    def test_animated_input_is_not_silently_flattened(self):
        path = self.directory / "animated.png"
        Image.new("RGBA", (20, 20), "red").save(path, save_all=True,
            append_images=[Image.new("RGBA", (20, 20), "blue")], duration=100, loop=0)
        code, _ = self.run_tool("check", path)
        self.assertEqual(code, 1)
        output = self.directory / "banner.png"
        code, _ = self.run_tool("export", path, output, "--profile", "banner")
        self.assertEqual(code, 1)
        self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
