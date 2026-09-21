import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("sticker_cutout", ROOT / "scripts" / "sticker_cutout.py")
tool = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(tool)

BACKGROUND = (214, 230, 254)  # the light blue card background of the real grids


class StickerCutoutTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def save(self, image, name="input.png"):
        path = self.directory / name
        image.save(path)
        return path

    def run_tool(self, *args):
        with contextlib.redirect_stdout(io.StringIO()) as stream:
            code = tool.main([str(arg) for arg in args])
        return code, json.loads(stream.getvalue())

    def test_background_removed_and_white_subject_kept(self):
        image = Image.new("RGB", (120, 120), BACKGROUND)
        ImageDraw.Draw(image).ellipse((30, 30, 90, 90), fill=(253, 253, 254))
        path = self.save(image)
        output = self.directory / "out.png"
        code, result = self.run_tool(path, output)
        self.assertEqual(code, 0, result)
        self.assertGreater(result["transparent_pixels"], 0)
        pad = 10
        with Image.open(output) as cut:
            self.assertEqual(cut.getpixel((5, 5))[3], 0)            # padding exterior
            self.assertEqual(cut.getpixel((pad + 60, pad + 60))[3], 255)  # white subject stays
            self.assertEqual(cut.getpixel((pad + 60, pad + 10))[3], 0)    # background above subject

    def ring_tile(self, gap=0):
        """White ring enclosing a background-colored patch, like hair highlights
        inside a sticker outline."""
        image = Image.new("RGB", (140, 140), BACKGROUND)
        draw = ImageDraw.Draw(image)
        draw.rectangle((30, 30, 109, 109), fill=(253, 253, 254))
        draw.rectangle((42, 42, 97, 97), fill=BACKGROUND)  # enclosed patch
        if gap:
            # breach the ring so the exterior connects to the enclosed patch
            draw.rectangle((60, 28, 60 + gap, 44), fill=BACKGROUND)
        return image

    def test_enclosed_background_colored_region_survives(self):
        path = self.save(self.ring_tile(gap=0))
        output = self.directory / "out.png"
        code, result = self.run_tool(path, output)
        self.assertEqual(code, 0, result)
        with Image.open(output) as cut:
            self.assertEqual(cut.getpixel((10 + 60, 10 + 60))[3], 255)  # patch kept

    def test_wide_gap_lets_the_flood_in(self):
        path = self.save(self.ring_tile(gap=10))
        output = self.directory / "out.png"
        code, result = self.run_tool(path, output)
        self.assertEqual(code, 0, result)
        with Image.open(output) as cut:
            self.assertEqual(cut.getpixel((10 + 60, 10 + 60))[3], 0)  # flooded through the gap

    def test_thin_gap_is_blocked_by_erosion(self):
        image = Image.new("RGB", (140, 140), BACKGROUND)
        draw = ImageDraw.Draw(image)
        draw.rectangle((30, 30, 109, 109), fill=(253, 253, 254))
        draw.rectangle((42, 42, 97, 97), fill=BACKGROUND)
        draw.rectangle((60, 28, 62, 44), fill=BACKGROUND)  # 3px breach
        path = self.save(image)
        output = self.directory / "out.png"
        code, result = self.run_tool(path, output)
        self.assertEqual(code, 0, result)
        with Image.open(output) as cut:
            self.assertEqual(cut.getpixel((10 + 60, 10 + 60))[3], 255)  # leak blocked

    def prop_tile(self):
        """A background-colored prop touching the image edge, like a light
        pillow overflowing the card."""
        image = Image.new("RGB", (140, 140), BACKGROUND)
        draw = ImageDraw.Draw(image)
        draw.ellipse((60, 30, 130, 100), fill=(253, 253, 254))  # subject
        draw.rectangle((0, 60, 59, 139), fill=BACKGROUND)       # prop flush to the edge
        draw.line((0, 60, 59, 139), fill=(120, 160, 240), width=3)
        return image

    def test_edge_touching_prop_needs_protect_zone(self):
        path = self.save(self.prop_tile())
        eaten = self.directory / "eaten.png"
        code, _ = self.run_tool(path, eaten)
        self.assertEqual(code, 0)
        with Image.open(eaten) as cut:
            self.assertEqual(cut.getpixel((10 + 20, 10 + 100))[3], 0)  # prop treated as background
        kept = self.directory / "kept.png"
        code, result = self.run_tool(path, kept, "--protect", "0,50,60,140")
        self.assertEqual(code, 0, result)
        self.assertTrue(any("Protect" in w for w in result["warnings"]))
        with Image.open(kept) as cut:
            self.assertEqual(cut.getpixel((10 + 20, 10 + 100))[3], 255)  # prop restored

    def test_nothing_removable_is_a_failure_not_a_fake(self):
        path = self.save(Image.new("RGB", (60, 60), (200, 40, 40)))
        output = self.directory / "out.png"
        code, result = self.run_tool(path, output)
        self.assertEqual(code, 1)
        self.assertFalse(output.exists())

    def test_preview_is_checkerboard_composite(self):
        image = Image.new("RGB", (80, 80), BACKGROUND)
        ImageDraw.Draw(image).ellipse((20, 20, 60, 60), fill=(253, 253, 254))
        path = self.save(image)
        output = self.directory / "out.png"
        preview = self.directory / "preview.png"
        code, result = self.run_tool(path, output, "--preview", preview)
        self.assertEqual(code, 0, result)
        with Image.open(preview) as board, Image.open(output) as cut:
            self.assertEqual(board.mode, "RGB")
            self.assertEqual(board.size, cut.size)
            self.assertIn(board.getpixel((3, 3)), [(200, 200, 200), (150, 150, 150)])

    def test_existing_output_and_input_are_preserved(self):
        image = Image.new("RGB", (80, 80), BACKGROUND)
        ImageDraw.Draw(image).ellipse((20, 20, 60, 60), fill=(253, 253, 254))
        path = self.save(image)
        original = path.read_bytes()
        output = self.save(Image.new("RGB", (10, 10), "red"), "existing.png")
        existing = output.read_bytes()
        code, _ = self.run_tool(path, output)
        self.assertEqual(code, 2)
        self.assertEqual(output.read_bytes(), existing)
        code, _ = self.run_tool(path, path, "--force")
        self.assertEqual(code, 2)
        self.assertEqual(path.read_bytes(), original)
        code, _ = self.run_tool(path, output, "--force")
        self.assertEqual(code, 0)

    def test_animated_input_is_rejected(self):
        path = self.directory / "animated.png"
        Image.new("RGB", (40, 40), BACKGROUND).save(path, save_all=True,
            append_images=[Image.new("RGB", (40, 40), "blue")], duration=100, loop=0)
        output = self.directory / "out.png"
        code, _ = self.run_tool(path, output)
        self.assertEqual(code, 1)
        self.assertFalse(output.exists())

    def test_invalid_protect_zone_is_an_argument_error(self):
        path = self.save(Image.new("RGB", (60, 60), BACKGROUND))
        code, _ = self.run_tool(path, self.directory / "out.png", "--protect", "10,10,5")
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
