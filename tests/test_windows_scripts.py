import unittest
from pathlib import Path


class WindowsScriptEncodingTests(unittest.TestCase):
    def test_batch_files_are_ascii_and_use_crlf(self):
        project_root = Path(__file__).resolve().parents[1]
        for name in ("AutoPage_Windows.bat", "build_exe_windows.bat"):
            data = (project_root / name).read_bytes()
            self.assertTrue(data.isascii(), name + " must contain ASCII only")
            self.assertIn(b"\r\n", data, name + " must use Windows CRLF")
            self.assertNotIn(
                b"\n", data.replace(b"\r\n", b""), name + " has a lone LF"
            )


if __name__ == "__main__":
    unittest.main()
