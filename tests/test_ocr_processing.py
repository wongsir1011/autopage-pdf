from io import BytesIO
import os
import tempfile
import unittest

from PIL import Image, ImageDraw
from pypdf import PdfReader

from ocr_processing import (
    OCRPageResult,
    OCRWord,
    create_invisible_text_overlay,
    create_pdf_document,
    preprocess_for_ocr,
    required_language_codes,
)


class OCRUtilityTests(unittest.TestCase):
    def test_combined_language_codes_are_unique(self):
        self.assertEqual(
            required_language_codes("chi_tra+eng+chi_tra"),
            ["chi_tra", "eng"],
        )

    def test_ocr_enhancement_does_not_resize_page(self):
        image = Image.new("RGB", (180, 120), "#dddddd")
        ImageDraw.Draw(image).text((20, 30), "AutoPage", fill="black")
        for mode in ("none", "grayscale", "contrast", "binary"):
            processed = preprocess_for_ocr(image, mode)
            self.assertEqual(processed.size, image.size)

    def test_invisible_overlay_contains_searchable_english_text(self):
        overlay = create_invisible_text_overlay(
            (300.0, 200.0),
            (300, 200),
            [OCRWord("AutoPage", 20, 30, 90, 20, 95.0)],
        )
        page = PdfReader(BytesIO(overlay)).pages[0]
        self.assertIn("AutoPage", page.extract_text())

    def test_invisible_overlay_supports_traditional_and_simplified_chinese(self):
        for text, language in (
            ("繁體中文測試", "chi_tra"),
            ("简体中文测试", "chi_sim"),
        ):
            overlay = create_invisible_text_overlay(
                (400.0, 200.0),
                (400, 200),
                [OCRWord(text, 20, 30, 180, 30, 95.0)],
                language,
            )
            extracted = PdfReader(BytesIO(overlay)).pages[0].extract_text()
            self.assertIn(text, extracted)


class SearchablePDFTests(unittest.TestCase):
    def test_searchable_pdf_keeps_failed_page_and_exports_text(self):
        calls = []

        def fake_ocr(image, language, enhancement):
            calls.append((image.size, language, enhancement))
            if len(calls) == 2:
                raise RuntimeError("simulated page failure")
            return OCRPageResult(
                words=[OCRWord("Hello", 15, 15, 60, 18, 99.0)],
                text="Hello",
            )

        with tempfile.TemporaryDirectory() as directory:
            image_paths = []
            for index in range(2):
                path = os.path.join(directory, "page_{0}.png".format(index + 1))
                Image.new("RGB", (240, 160), "white").save(path)
                image_paths.append(path)
            output_path = os.path.join(directory, "searchable.pdf")
            progress = []

            summary = create_pdf_document(
                image_paths,
                output_path,
                searchable=True,
                language="eng",
                enhancement="contrast",
                write_text=True,
                progress_callback=lambda current, total, error: progress.append(
                    (current, total, error)
                ),
                ocr_function=fake_ocr,
            )

            reader = PdfReader(output_path)
            self.assertEqual(len(reader.pages), 2)
            self.assertIn("Hello", reader.pages[0].extract_text())
            self.assertEqual(summary.searchable_pages, 1)
            self.assertEqual(summary.failed_pages, [2])
            self.assertEqual(len(progress), 2)
            self.assertIsNotNone(summary.text_output_path)
            with open(summary.text_output_path, encoding="utf-8") as text_file:
                exported = text_file.read()
            self.assertIn("Hello", exported)
            self.assertIn("OCR 失敗", exported)


if __name__ == "__main__":
    unittest.main()
