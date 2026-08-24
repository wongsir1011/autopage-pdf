"""Optional offline OCR and searchable-PDF support for AutoPage PDF."""

from collections import OrderedDict
from dataclasses import dataclass
from io import BytesIO
import os
import platform
import shutil
import tempfile
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import img2pdf
from PIL import Image, ImageFilter, ImageOps


try:
    import pytesseract
    from pytesseract import Output
except ImportError:  # The non-OCR PDF path must remain usable.
    pytesseract = None
    Output = None

try:
    from pypdf import PdfReader, PdfWriter
except ImportError:
    PdfReader = None
    PdfWriter = None

try:
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    from reportlab.pdfgen import canvas
except ImportError:
    pdfmetrics = None
    UnicodeCIDFont = None
    canvas = None


OCR_DEPENDENCIES = ("pytesseract", "pypdf", "reportlab")


class OCRUnavailableError(RuntimeError):
    """Raised when searchable output is selected but OCR is not ready."""


@dataclass(frozen=True)
class OCRWord:
    text: str
    left: int
    top: int
    width: int
    height: int
    confidence: float = 0.0


@dataclass(frozen=True)
class OCRPageResult:
    words: List[OCRWord]
    text: str


@dataclass(frozen=True)
class OCRStatus:
    available: bool
    executable: Optional[str]
    version: Optional[str]
    installed_languages: List[str]
    missing_languages: List[str]
    message: str


@dataclass(frozen=True)
class PDFBuildSummary:
    total_pages: int
    searchable_pages: int
    failed_pages: List[int]
    text_output_path: Optional[str]


def _missing_python_dependencies() -> List[str]:
    missing = []
    if pytesseract is None:
        missing.append("pytesseract")
    if PdfReader is None or PdfWriter is None:
        missing.append("pypdf")
    if canvas is None or pdfmetrics is None or UnicodeCIDFont is None:
        missing.append("reportlab")
    return missing


def find_tesseract_executable() -> Optional[str]:
    """Return a usable Tesseract executable from PATH or common locations."""

    found = shutil.which("tesseract")
    if found:
        return found

    candidates = []
    if platform.system() == "Windows":
        candidates.extend(
            [
                r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            ]
        )
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            candidates.append(
                os.path.join(
                    local_app_data, "Programs", "Tesseract-OCR", "tesseract.exe"
                )
            )
    elif platform.system() == "Darwin":
        candidates.extend(
            [
                "/opt/homebrew/bin/tesseract",
                "/usr/local/bin/tesseract",
                "/opt/local/bin/tesseract",
            ]
        )
    else:
        candidates.extend(["/usr/bin/tesseract", "/usr/local/bin/tesseract"])

    for candidate in candidates:
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return None


def required_language_codes(language: str) -> List[str]:
    """Split a Tesseract combined language expression into unique codes."""

    result = []
    for code in language.split("+"):
        code = code.strip()
        if code and code not in result:
            result.append(code)
    return result


def check_ocr_status(language: str = "chi_tra+eng") -> OCRStatus:
    """Check Python packages, the Tesseract executable, and language data."""

    missing_dependencies = _missing_python_dependencies()
    if missing_dependencies:
        message = "缺少 Python OCR 套件：" + ", ".join(missing_dependencies)
        return OCRStatus(False, None, None, [], [], message)

    executable = find_tesseract_executable()
    if executable is None:
        return OCRStatus(
            False,
            None,
            None,
            [],
            required_language_codes(language),
            "找不到 Tesseract OCR。一般圖片 PDF 功能仍可使用。",
        )

    assert pytesseract is not None
    pytesseract.pytesseract.tesseract_cmd = executable
    try:
        version = str(pytesseract.get_tesseract_version()).splitlines()[0]
        languages = sorted(pytesseract.get_languages(config=""))
    except Exception as error:
        return OCRStatus(
            False,
            executable,
            None,
            [],
            required_language_codes(language),
            "Tesseract 無法啟動：{0}".format(error),
        )

    missing_languages = [
        code for code in required_language_codes(language) if code not in languages
    ]
    if missing_languages:
        return OCRStatus(
            False,
            executable,
            version,
            languages,
            missing_languages,
            "缺少 OCR 語言包：{0}".format(", ".join(missing_languages)),
        )
    return OCRStatus(
        True,
        executable,
        version,
        languages,
        [],
        "Tesseract {0} 已就緒。".format(version),
    )


def preprocess_for_ocr(image: Image.Image, enhancement: str) -> Image.Image:
    """Prepare a recognition-only image without changing the visible PDF page."""

    if enhancement == "none":
        return image.convert("RGB")
    gray = ImageOps.grayscale(image)
    if enhancement == "grayscale":
        return gray
    contrasted = ImageOps.autocontrast(gray, cutoff=1)
    if enhancement == "contrast":
        return contrasted.filter(ImageFilter.SHARPEN)
    if enhancement == "binary":
        return contrasted.point(lambda value: 255 if value >= 180 else 0, mode="1")
    raise ValueError("Unknown OCR enhancement mode: {0}".format(enhancement))


def _lines_from_tesseract_data(data: Dict[str, Sequence[object]]) -> str:
    lines = OrderedDict()  # type: OrderedDict[Tuple[int, int, int], List[str]]
    count = len(data.get("text", []))
    for index in range(count):
        text = str(data["text"][index]).strip()
        if not text:
            continue
        key = (
            int(data.get("block_num", [0] * count)[index]),
            int(data.get("par_num", [0] * count)[index]),
            int(data.get("line_num", [0] * count)[index]),
        )
        lines.setdefault(key, []).append(text)
    return "\n".join(" ".join(words) for words in lines.values())


def ocr_image(
    image: Image.Image,
    language: str,
    enhancement: str = "contrast",
    page_segmentation_mode: int = 3,
) -> OCRPageResult:
    """Recognize one image and return positioned words plus plain text."""

    status = check_ocr_status(language)
    if not status.available:
        raise OCRUnavailableError(status.message)
    assert pytesseract is not None and Output is not None

    prepared = preprocess_for_ocr(image, enhancement)
    data = pytesseract.image_to_data(
        prepared,
        lang=language,
        config="--psm {0}".format(page_segmentation_mode),
        output_type=Output.DICT,
    )
    words = []
    for index, raw_text in enumerate(data.get("text", [])):
        text = str(raw_text).strip()
        if not text:
            continue
        try:
            confidence = float(data.get("conf", [0])[index])
        except (TypeError, ValueError, IndexError):
            confidence = 0.0
        if confidence < 0:
            continue
        words.append(
            OCRWord(
                text=text,
                left=int(data["left"][index]),
                top=int(data["top"][index]),
                width=int(data["width"][index]),
                height=int(data["height"][index]),
                confidence=confidence,
            )
        )
    return OCRPageResult(words=words, text=_lines_from_tesseract_data(data))


def _font_for_text(text: str, language: str) -> str:
    if not any(ord(character) > 255 for character in text):
        return "Helvetica"
    if "chi_sim" in language and "chi_tra" not in language:
        return "STSong-Light"
    return "MSung-Light"


def create_invisible_text_overlay(
    page_size: Tuple[float, float],
    image_size: Tuple[int, int],
    words: Sequence[OCRWord],
    language: str = "chi_tra+eng",
) -> bytes:
    """Create a one-page PDF containing positioned invisible OCR text."""

    if canvas is None or pdfmetrics is None or UnicodeCIDFont is None:
        raise OCRUnavailableError("缺少 reportlab，無法建立 PDF 文字層。")
    required_fonts = {
        _font_for_text(word.text, language)
        for word in words
        if word.text and any(ord(character) > 255 for character in word.text)
    }
    for font_name in required_fonts:
        try:
            pdfmetrics.getFont(font_name)
        except KeyError:
            pdfmetrics.registerFont(UnicodeCIDFont(font_name))

    page_width, page_height = page_size
    image_width, image_height = image_size
    scale_x = page_width / float(image_width)
    scale_y = page_height / float(image_height)
    output = BytesIO()
    pdf_canvas = canvas.Canvas(
        output,
        pagesize=(page_width, page_height),
        pageCompression=1,
    )
    text_object = pdf_canvas.beginText()
    text_object.setTextRenderMode(3)
    for word in words:
        if not word.text:
            continue
        font_size = max(4.0, word.height * scale_y * 0.92)
        x_position = max(0.0, word.left * scale_x)
        y_position = max(
            0.0,
            page_height - (word.top + word.height) * scale_y + font_size * 0.12,
        )
        text_object.setFont(_font_for_text(word.text, language), font_size)
        text_object.setTextOrigin(x_position, y_position)
        text_object.textOut(word.text)
    pdf_canvas.drawText(text_object)
    pdf_canvas.showPage()
    pdf_canvas.save()
    return output.getvalue()


def _one_page_image_pdf(image_path: str):
    if PdfReader is None:
        raise OCRUnavailableError("缺少 pypdf，無法建立可搜尋 PDF。")
    pdf_bytes = img2pdf.convert([image_path])
    return PdfReader(BytesIO(pdf_bytes)).pages[0]


def _text_output_path(output_path: str) -> str:
    return os.path.splitext(output_path)[0] + ".txt"


def _write_atomic_pdf(output_path: str, pdf_bytes: bytes) -> None:
    output_directory = os.path.dirname(os.path.abspath(output_path))
    temporary = tempfile.NamedTemporaryFile(
        mode="wb",
        prefix=".autopage_pdf_",
        suffix=".pdf.part",
        dir=output_directory,
        delete=False,
    )
    temporary_path = temporary.name
    try:
        with temporary:
            temporary.write(pdf_bytes)
        os.replace(temporary_path, output_path)
    except Exception:
        if os.path.exists(temporary_path):
            os.remove(temporary_path)
        raise


def create_pdf_document(
    image_paths: Sequence[str],
    output_path: str,
    searchable: bool = False,
    language: str = "chi_tra+eng",
    enhancement: str = "contrast",
    write_text: bool = False,
    progress_callback: Optional[Callable[[int, int, Optional[str]], None]] = None,
    ocr_function: Callable[[Image.Image, str, str], OCRPageResult] = ocr_image,
) -> PDFBuildSummary:
    """Create a normal or searchable PDF while preserving the visible pages."""

    if not image_paths:
        raise ValueError("沒有可輸出的頁面。")
    if not searchable:
        _write_atomic_pdf(output_path, img2pdf.convert(list(image_paths)))
        return PDFBuildSummary(len(image_paths), 0, [], None)

    status = check_ocr_status(language)
    if not status.available and ocr_function is ocr_image:
        raise OCRUnavailableError(status.message)
    if PdfReader is None or PdfWriter is None:
        raise OCRUnavailableError("缺少 pypdf，無法建立可搜尋 PDF。")

    writer = PdfWriter()
    failed_pages = []
    searchable_pages = 0
    page_texts = []
    total = len(image_paths)
    for index, image_path in enumerate(image_paths, 1):
        writer.add_page(_one_page_image_pdf(image_path))
        page = writer.pages[-1]
        page_error = None
        try:
            with Image.open(image_path) as opened:
                image = opened.convert("RGB")
            result = ocr_function(image, language, enhancement)
            overlay_bytes = create_invisible_text_overlay(
                (float(page.mediabox.width), float(page.mediabox.height)),
                image.size,
                result.words,
                language,
            )
            overlay_page = PdfReader(BytesIO(overlay_bytes)).pages[0]
            page.merge_page(overlay_page)
            searchable_pages += 1
            page_texts.append(result.text)
        except Exception as error:
            failed_pages.append(index)
            page_error = str(error)
            page_texts.append("[OCR 失敗：{0}]".format(page_error))
        if progress_callback:
            progress_callback(index, total, page_error)

    output_directory = os.path.dirname(os.path.abspath(output_path))
    temporary = tempfile.NamedTemporaryFile(
        mode="wb",
        prefix=".autopage_ocr_",
        suffix=".pdf.part",
        dir=output_directory,
        delete=False,
    )
    temporary_path = temporary.name
    try:
        with temporary:
            writer.write(temporary)
        os.replace(temporary_path, output_path)
    except Exception:
        if os.path.exists(temporary_path):
            os.remove(temporary_path)
        raise

    text_path = None
    if write_text:
        text_path = _text_output_path(output_path)
        with open(text_path, "w", encoding="utf-8", newline="\n") as text_file:
            for page_number, page_text in enumerate(page_texts, 1):
                if page_number > 1:
                    text_file.write("\n\n")
                text_file.write("===== 第 {0} 頁 =====\n".format(page_number))
                text_file.write(page_text.strip())
                text_file.write("\n")

    return PDFBuildSummary(total, searchable_pages, failed_pages, text_path)
