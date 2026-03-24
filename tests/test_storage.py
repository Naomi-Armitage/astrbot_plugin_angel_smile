import json
import os
import tempfile
import unittest
from pathlib import Path

from astrbot_plugin_angel_smile.tests._bootstrap import install_fake_astrbot
from PIL import Image

install_fake_astrbot()

from astrbot_plugin_angel_smile.models import PluginPaths  # noqa: E402
from astrbot_plugin_angel_smile.services.storage import MemeStorage  # noqa: E402


class StorageTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        os.environ["ASTRBOT_TEST_DATA_PATH"] = self.temp_dir.name

        root = Path(self.temp_dir.name)
        self.paths = PluginPaths(
            plugin_dir=root / "plugin",
            data_dir=root / "data",
            stickers_dir=root / "data" / "memes",
            stickers_data_file=root / "data" / "memes_data.json",
            default_dir=root / "plugin" / "default",
        )
        self.paths.default_dir.mkdir(parents=True, exist_ok=True)
        self.storage = MemeStorage(self.paths)

    def test_normalize_stickers_data_requires_dict(self):
        with self.assertRaises(TypeError):
            self.storage._normalize_stickers_data(["not", "dict"])

    def test_load_stickers_data_falls_back_on_invalid_json_shape(self):
        self.paths.data_dir.mkdir(parents=True, exist_ok=True)
        self.paths.stickers_data_file.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
        result = self.storage.load_stickers_data()
        self.assertEqual(result, {})

    def test_available_stickers_only_counts_categories_with_assets(self):
        self.storage.stickers_data = {"happy": "desc", "sad": "desc2"}
        happy_dir = self.paths.stickers_dir / "happy"
        sad_dir = self.paths.stickers_dir / "sad"
        happy_dir.mkdir(parents=True, exist_ok=True)
        sad_dir.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (16, 16), color="red").save(happy_dir / "a.png")

        available = self.storage.get_available_stickers_data()
        self.assertEqual(available, {"happy": "desc"})

    def test_save_meme_preserves_detected_webp_suffix(self):
        source_file = self.paths.plugin_dir / "downloaded.jpg"
        source_file.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGBA", (32, 32), color=(255, 0, 0, 0)).save(
            source_file,
            format="WEBP",
        )

        result = self.storage.save_meme(
            source_file=source_file,
            category="happy",
            description="desc",
            reason="test",
            save_name="sticker.jpg",
        )

        self.assertEqual(result.saved_file.suffix.lower(), ".webp")
        self.assertTrue(result.saved_file.exists())


if __name__ == "__main__":
    unittest.main()
