import tempfile
import unittest
from pathlib import Path

from astrbot_plugin_angel_smile.tests._bootstrap import install_fake_astrbot
from PIL import Image

install_fake_astrbot()

from astrbot_plugin_angel_smile.utils import (  # noqa: E402
    detect_image_suffix,
    is_path_within_roots,
    normalize_category_name,
    safe_filename,
)


class UtilsTestCase(unittest.TestCase):
    def test_normalize_category_name(self):
        self.assertEqual(normalize_category_name(" Happy Mood "), "happy_mood")
        self.assertEqual(normalize_category_name("???"), "unsorted")

    def test_safe_filename_strips_unsafe_chars(self):
        result = safe_filename('a<>:"/\\|?*.png', ".jpg")
        self.assertTrue(result.endswith(".png"))
        self.assertNotIn("<", result)
        self.assertNotIn(">", result)

    def test_safe_filename_can_force_detected_suffix(self):
        result = safe_filename("sticker.png", ".webp", force_suffix=True)
        self.assertEqual(result, "sticker.webp")

    def test_safe_filename_keeps_legacy_force_extension_alias(self):
        result = safe_filename("sticker.png", ".webp", force_extension=True)
        self.assertEqual(result, "sticker.webp")

    def test_detect_image_suffix_uses_real_image_format(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            fake_jpg = Path(temp_dir) / "sticker.jpg"
            Image.new("RGBA", (16, 16), color=(255, 0, 0, 0)).save(
                fake_jpg,
                format="WEBP",
            )

            self.assertEqual(detect_image_suffix(fake_jpg), ".webp")

    def test_path_within_roots(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            nested = root / "sub" / "image.png"
            nested.parent.mkdir(parents=True, exist_ok=True)
            nested.write_bytes(b"ok")

            self.assertTrue(is_path_within_roots(nested, [root]))
            self.assertFalse(is_path_within_roots(Path(temp_dir).parent / "other.png", [root]))


if __name__ == "__main__":
    unittest.main()
