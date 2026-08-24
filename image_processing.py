"""Image processing helpers for AutoPage PDF.

The functions in this module deliberately avoid GUI and desktop automation
dependencies so that page processing can be tested on every platform.
"""

from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

from PIL import Image, ImageChops, ImageStat


RESAMPLE_LANCZOS = getattr(Image, "Resampling", Image).LANCZOS


@dataclass(frozen=True)
class CropMargins:
    """Manual crop margins measured in source-image pixels."""

    left: int = 0
    top: int = 0
    right: int = 0
    bottom: int = 0

    def validated(self, width: int, height: int) -> "CropMargins":
        values = (self.left, self.top, self.right, self.bottom)
        if any(value < 0 for value in values):
            raise ValueError("裁切邊距不可為負數。")
        if self.left + self.right >= width:
            raise ValueError("左右裁切邊距超出頁面寬度。")
        if self.top + self.bottom >= height:
            raise ValueError("上下裁切邊距超出頁面高度。")
        return self


def _sample_background(image: Image.Image) -> Tuple[int, int, int]:
    """Estimate the surrounding reader colour from small corner patches."""

    rgb = image.convert("RGB")
    width, height = rgb.size
    patch = max(2, min(width, height) // 40)
    boxes = (
        (0, 0, patch, patch),
        (width - patch, 0, width, patch),
        (0, height - patch, patch, height),
        (width - patch, height - patch, width, height),
    )
    samples = []
    for box in boxes:
        mean = ImageStat.Stat(rgb.crop(box)).mean
        samples.append(tuple(int(round(channel)) for channel in mean[:3]))

    # Median by luminance avoids one corner overlay (for example a page-turn
    # button) dominating the estimate.
    samples.sort(key=lambda colour: sum(colour))
    return samples[len(samples) // 2]


def auto_crop_image(
    image: Image.Image,
    tolerance: int = 24,
    padding: int = 6,
    minimum_retained_ratio: float = 0.30,
) -> Image.Image:
    """Crop a page away from a near-uniform reader background.

    A reduced working copy is used to keep this fast for high-resolution
    screenshots.  If detection is uncertain or would retain too little of the
    source, the original image is returned unchanged.
    """

    if image.width < 8 or image.height < 8:
        return image.copy()
    if not 0 <= tolerance <= 255:
        raise ValueError("Auto-crop tolerance must be between 0 and 255.")
    if padding < 0:
        raise ValueError("Auto-crop padding cannot be negative.")

    scale = min(1.0, 900.0 / max(image.size))
    working_size = (
        max(2, int(round(image.width * scale))),
        max(2, int(round(image.height * scale))),
    )
    working = image.convert("RGB").resize(working_size, RESAMPLE_LANCZOS)
    background = _sample_background(working)
    backdrop = Image.new("RGB", working.size, background)
    difference = ImageChops.difference(working, backdrop).convert("L")
    mask = difference.point(lambda value: 255 if value > tolerance else 0)
    detected = mask.getbbox()
    if detected is None:
        return image.copy()

    left, top, right, bottom = detected
    retained = ((right - left) * (bottom - top)) / float(
        working.width * working.height
    )
    if retained < minimum_retained_ratio:
        return image.copy()

    inverse_scale = 1.0 / scale
    source_box = (
        max(0, int(left * inverse_scale) - padding),
        max(0, int(top * inverse_scale) - padding),
        min(image.width, int(round(right * inverse_scale)) + padding),
        min(image.height, int(round(bottom * inverse_scale)) + padding),
    )
    if source_box == (0, 0, image.width, image.height):
        return image.copy()
    return image.crop(source_box)


def manual_crop_image(image: Image.Image, margins: CropMargins) -> Image.Image:
    """Apply explicit pixel margins to an image."""

    margins.validated(image.width, image.height)
    return image.crop(
        (
            margins.left,
            margins.top,
            image.width - margins.right,
            image.height - margins.bottom,
        )
    )


def find_split_x(image: Image.Image, search_width: float = 0.24) -> int:
    """Find a likely book gutter near the horizontal centre.

    The score favours a visually quiet vertical seam and adds a centre-distance
    penalty so that an empty text column is not selected too readily.
    """

    if image.width < 20:
        return image.width // 2
    if not 0.05 <= search_width <= 0.45:
        raise ValueError("Split search width must be between 0.05 and 0.45.")

    scale = min(1.0, 700.0 / max(image.size))
    gray = image.convert("L").resize(
        (
            max(20, int(round(image.width * scale))),
            max(20, int(round(image.height * scale))),
        ),
        RESAMPLE_LANCZOS,
    )
    width, height = gray.size
    pixels = gray.load()
    centre = width / 2.0
    start = max(2, int(width * (0.5 - search_width)))
    end = min(width - 2, int(width * (0.5 + search_width)))
    step_y = max(1, height // 300)

    best_x = width // 2
    best_score: Optional[float] = None
    for x in range(start, end + 1):
        values = [pixels[x, y] for y in range(0, height, step_y)]
        if not values:
            continue
        mean = sum(values) / len(values)
        variance = sum((value - mean) ** 2 for value in values) / len(values)
        horizontal_edge = sum(
            abs(pixels[x - 1, y] - pixels[x + 1, y])
            for y in range(0, height, step_y)
        ) / len(values)
        centre_penalty = abs(x - centre) / width * 900.0
        score = variance + horizontal_edge * 8.0 + centre_penalty
        if best_score is None or score < best_score:
            best_score = score
            best_x = x

    return max(1, min(image.width - 1, int(round(best_x / scale))))


def split_spread(
    image: Image.Image,
    reading_order: str = "ltr",
    automatic_gutter: bool = True,
    split_x: Optional[int] = None,
) -> List[Image.Image]:
    """Split one two-page spread and return pages in PDF reading order."""

    if reading_order not in ("ltr", "rtl"):
        raise ValueError("Reading order must be 'ltr' or 'rtl'.")
    if automatic_gutter:
        seam = find_split_x(image)
    elif split_x is not None:
        seam = split_x
    else:
        seam = image.width // 2

    minimum_width = max(1, int(round(image.width * 0.25)))
    seam = max(minimum_width, min(image.width - minimum_width, seam))
    left_page = image.crop((0, 0, seam, image.height))
    right_page = image.crop((seam, 0, image.width, image.height))
    if reading_order == "rtl":
        return [right_page, left_page]
    return [left_page, right_page]


def process_page(
    image: Image.Image,
    crop_mode: str = "off",
    crop_margins: Optional[CropMargins] = None,
    auto_crop_tolerance: int = 24,
    auto_crop_padding: int = 6,
    page_mode: str = "single",
    reading_order: str = "ltr",
) -> List[Image.Image]:
    """Apply crop and optional spread splitting to one captured screen."""

    if crop_mode == "auto":
        processed = auto_crop_image(
            image,
            tolerance=auto_crop_tolerance,
            padding=auto_crop_padding,
        )
    elif crop_mode == "manual":
        processed = manual_crop_image(image, crop_margins or CropMargins())
    elif crop_mode == "off":
        processed = image.copy()
    else:
        raise ValueError("Unknown crop mode: {0}".format(crop_mode))

    if page_mode == "single":
        return [processed]
    if page_mode == "double_auto":
        return split_spread(
            processed, reading_order=reading_order, automatic_gutter=True
        )
    if page_mode == "double_centre":
        return split_spread(
            processed, reading_order=reading_order, automatic_gutter=False
        )
    raise ValueError("Unknown page mode: {0}".format(page_mode))


def image_difference_percent(
    first: Image.Image,
    second: Image.Image,
    compare_size: Sequence[int] = (320, 240),
) -> float:
    """Return an inexpensive 0..100 visual difference score."""

    size = (int(compare_size[0]), int(compare_size[1]))
    first_gray = first.convert("L").resize(size, RESAMPLE_LANCZOS)
    second_gray = second.convert("L").resize(size, RESAMPLE_LANCZOS)
    difference = ImageChops.difference(first_gray, second_gray)
    mean = ImageStat.Stat(difference).mean[0]
    return mean / 255.0 * 100.0

