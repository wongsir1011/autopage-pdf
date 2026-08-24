import os
import sys
import tempfile
import threading
import types
import unittest

from PIL import Image
from pypdf import PdfReader


class FakeFailSafeException(Exception):
    pass


class FakePyAutoGUI(types.ModuleType):
    def __init__(self):
        super().__init__("pyautogui")
        self.FAILSAFE = True
        self.PAUSE = 0.1
        self.FailSafeException = FakeFailSafeException
        self.screenshots = []
        self.turns = []

    def screenshot(self, region=None):
        del region
        return self.screenshots.pop(0).copy()

    def press(self, key):
        self.turns.append(("press", key))

    def click(self, x, y):
        self.turns.append(("click", x, y))


fake_pyautogui = FakePyAutoGUI()
sys.modules["pyautogui"] = fake_pyautogui

import autopage_gui  # noqa: E402  (desktop dependencies are stubbed above)


class ImmediateRoot:
    def after(self, _delay, callback, *args):
        callback(*args)


class CaptureWorkflowTests(unittest.TestCase):
    def setUp(self):
        fake_pyautogui.turns = []
        first = Image.new("RGB", (120, 80), "white")
        second = Image.new("RGB", (120, 80), "white")
        for x in range(20, 100):
            for y in range(20, 60):
                second.putpixel((x, y), (0, 0, 0))
        fake_pyautogui.screenshots = [first, second, second, second]

    def test_duplicate_end_page_is_not_added_to_pdf(self):
        app = autopage_gui.AutoPageApp.__new__(autopage_gui.AutoPageApp)
        app.root = ImmediateRoot()
        app.region = (0, 0, 120, 80)
        app.stop_event = threading.Event()
        app.log = lambda _text: None
        app._set_progress = lambda _value, maximum=None: None
        result = {}

        def finish(success, detail, output_path, page_count, retained_temp_dir):
            result.update(
                success=success,
                detail=detail,
                output_path=output_path,
                page_count=page_count,
                retained_temp_dir=retained_temp_dir,
            )

        app._finish_capture = finish
        with tempfile.TemporaryDirectory() as directory:
            output_path = os.path.join(directory, "book.pdf")
            settings = {
                "pages": 10,
                "delay": 0.0,
                "action": "Right Arrow",
                "autostop": True,
                "output_path": output_path,
                "crop_mode": "off",
                "crop_margins": autopage_gui.CropMargins(),
                "auto_crop_tolerance": 24,
                "auto_crop_padding": 6,
                "page_mode": "single",
                "reading_order": "ltr",
            }

            original_sleep = autopage_gui.time.sleep
            autopage_gui.time.sleep = lambda _seconds: None
            try:
                app._capture_process(settings)
            finally:
                autopage_gui.time.sleep = original_sleep

            self.assertTrue(os.path.exists(output_path))
            self.assertEqual(len(PdfReader(output_path).pages), 2)

        self.assertTrue(result["success"])
        self.assertEqual(result["page_count"], 2)
        self.assertIn("最後一頁", result["detail"])
        self.assertEqual(len(fake_pyautogui.turns), 3)


if __name__ == "__main__":
    unittest.main()
