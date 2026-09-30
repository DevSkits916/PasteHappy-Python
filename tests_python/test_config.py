import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pastehappy.config import Config


class ConfigTests(unittest.TestCase):
    def test_source_root_does_not_depend_on_working_directory(self):
        with patch.dict(os.environ, {}, clear=True):
            config = Config.from_environment()
        self.assertEqual(config.root, Path(__file__).resolve().parent.parent)

    def test_frozen_assets_and_writable_state_are_separate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(sys, "frozen", True, create=True), patch.object(sys, "_MEIPASS", str(root / "bundle"), create=True), patch.dict(os.environ, {"LOCALAPPDATA": str(root / "state")}, clear=True):
                config = Config.from_environment()
            self.assertEqual(config.root, root / "bundle")
            self.assertEqual(config.data_path, root / "state/PasteHappy/data/queue.json")
            self.assertEqual(config.profile_path, root / "state/PasteHappy/.browser-profile")
