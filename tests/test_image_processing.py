import unittest

from PIL import Image, ImageDraw

from image_processing import (
    CropMargins,
    auto_crop_image,
    find_split_x,
    image_change_metrics,
    image_difference_percent,
    manual_crop_image,
    process_page,
    split_spread,
)


class CropTests(unittest.TestCase):
    def test_auto_crop_removes_reader_background(self):
        image = Image.new("RGB", (300, 220), "#303030")
        draw = ImageDraw.Draw(image)
        draw.rectangle((35, 18, 264, 201), fill="white")
        draw.rectangle((65, 55, 230, 65), fill="black")

        cropped = auto_crop_image(image, tolerance=20, padding=0)

        self.assertLess(cropped.width, image.width)
        self.assertLess(cropped.height, image.height)
        self.assertGreaterEqual(cropped.width, 228)
        self.assertGreaterEqual(cropped.height, 182)

    def test_uncertain_auto_crop_preserves_original(self):
        image = Image.new("RGB", (200, 100), "white")
        cropped = auto_crop_image(image)
        self.assertEqual(cropped.size, image.size)

    def test_manual_crop_uses_all_four_margins(self):
        image = Image.new("RGB", (200, 120), "white")
        cropped = manual_crop_image(image, CropMargins(10, 15, 20, 25))
        self.assertEqual(cropped.size, (170, 80))

    def test_manual_crop_rejects_invalid_margins(self):
        image = Image.new("RGB", (100, 80), "white")
        with self.assertRaises(ValueError):
            manual_crop_image(image, CropMargins(60, 0, 40, 0))


class SplitTests(unittest.TestCase):
    @staticmethod
    def make_spread():
        image = Image.new("RGB", (400, 240), "#333333")
        draw = ImageDraw.Draw(image)
        draw.rectangle((10, 5, 194, 234), fill="#faf7ef")
        draw.rectangle((205, 5, 389, 234), fill="#faf7ef")
        for y in range(35, 210, 22):
            draw.rectangle((35, y, 170, y + 5), fill="#444444")
            draw.rectangle((230, y, 365, y + 5), fill="#444444")
        return image

    def test_find_split_x_stays_near_central_gutter(self):
        seam = find_split_x(self.make_spread())
        self.assertGreaterEqual(seam, 190)
        self.assertLessEqual(seam, 210)

    def test_split_spread_respects_reading_order(self):
        image = Image.new("RGB", (200, 100), "red")
        ImageDraw.Draw(image).rectangle((100, 0, 199, 99), fill="blue")
        pages = split_spread(
            image, reading_order="rtl", automatic_gutter=False, split_x=100
        )
        self.assertEqual(pages[0].getpixel((25, 25)), (0, 0, 255))
        self.assertEqual(pages[1].getpixel((25, 25)), (255, 0, 0))

    def test_process_page_crops_before_splitting(self):
        image = self.make_spread()
        pages = process_page(
            image,
            crop_mode="auto",
            auto_crop_tolerance=20,
            auto_crop_padding=0,
            page_mode="double_centre",
            reading_order="ltr",
        )
        self.assertEqual(len(pages), 2)
        self.assertLess(sum(page.width for page in pages), image.width)


class DifferenceTests(unittest.TestCase):
    def test_identical_images_have_zero_difference(self):
        image = Image.new("RGB", (300, 200), "white")
        self.assertEqual(image_difference_percent(image, image.copy()), 0.0)

    def test_changed_page_has_visible_difference(self):
        first = Image.new("RGB", (300, 200), "white")
        second = first.copy()
        ImageDraw.Draw(second).rectangle((20, 20, 280, 180), fill="black")
        self.assertGreater(image_difference_percent(first, second), 10.0)

    def test_sparse_text_change_is_not_diluted_by_white_background(self):
        first = Image.new("RGB", (1200, 1600), "white")
        second = first.copy()
        first_draw = ImageDraw.Draw(first)
        second_draw = ImageDraw.Draw(second)
        for line in range(1):
            y = 150 + line * 30
            first_draw.text((140, y), "Original page line {0}".format(line), fill="#222")
            second_draw.text((140, y), "Different page row {0}".format(line), fill="#222")

        mean_difference, changed_pixels = image_change_metrics(first, second)

        self.assertLess(mean_difference, 0.35)
        self.assertGreater(changed_pixels, 0.02)


if __name__ == "__main__":
    unittest.main()
