"""AutoPage PDF v1.2.0 graphical application."""

import os
import platform
import shutil
import subprocess
import tempfile
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Dict, List, Optional, Tuple

import img2pdf
import pyautogui
from PIL import Image, ImageTk

from image_processing import (
    CropMargins,
    image_difference_percent,
    process_page,
)


__version__ = "1.2.0"

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.1


CROP_MODE_LABELS = {
    "不裁切（保留原圖）": "off",
    "自動偵測頁面邊界": "auto",
    "手動設定四邊邊距": "manual",
}

PAGE_MODE_LABELS = {
    "單頁模式": "single",
    "雙頁模式－自動偵測書脊": "double_auto",
    "雙頁模式－從正中央分割": "double_centre",
}

READING_ORDER_LABELS = {
    "由左至右": "ltr",
    "由右至左（日／直排書）": "rtl",
}


def is_image_duplicate(
    first: Optional[Image.Image],
    second: Optional[Image.Image],
    threshold_percent: float = 0.35,
) -> bool:
    """Return whether two captures are visually close enough to be the same page."""

    if first is None or second is None or first.size != second.size:
        return False
    return image_difference_percent(first, second) <= threshold_percent


def trigger_turn_page(action: str, click_x: int = 0, click_y: int = 0) -> None:
    """Send the selected page-turn action on Windows or macOS."""

    is_mac = platform.system() == "Darwin"
    if "Mouse" in action or "滑鼠" in action or "點擊" in action:
        pyautogui.click(click_x, click_y)
        return

    key_name = "right"
    mac_key_code = 124
    if "Space" in action or "空白" in action:
        key_name = "space"
        mac_key_code = 49
    elif "Page Down" in action or "PageDown" in action:
        key_name = "pagedown"
        mac_key_code = 121

    if is_mac:
        try:
            command = 'tell application "System Events" to key code {0}'.format(
                mac_key_code
            )
            result = subprocess.run(
                ["osascript", "-e", command],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                timeout=5,
            )
            if result.returncode == 0:
                return
        except (OSError, subprocess.SubprocessError):
            pass
    pyautogui.press(key_name)


class AutoPageApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("AutoPage PDF v{0}".format(__version__))
        self.root.geometry("690x790")
        self.root.minsize(690, 790)
        self.region: Optional[Tuple[int, int, int, int]] = None
        self.stop_event = threading.Event()
        self.capture_running = False
        self.margin_entries: List[ttk.Entry] = []
        self._create_widgets()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _create_widgets(self) -> None:
        container = ttk.Frame(self.root, padding=14)
        container.pack(fill=tk.BOTH, expand=True)
        container.columnconfigure(0, weight=1)

        title = ttk.Label(
            container,
            text="AutoPage PDF",
            font=("Arial", 18, "bold"),
        )
        title.grid(row=0, column=0, sticky=tk.W)
        ttk.Label(
            container,
            text="自動翻頁截圖、頁面裁切與雙頁分割",
            foreground="#555555",
        ).grid(row=1, column=0, sticky=tk.W, pady=(0, 10))

        basic = ttk.LabelFrame(container, text="基本設定", padding=10)
        basic.grid(row=2, column=0, sticky=tk.EW)
        basic.columnconfigure(1, weight=1)

        ttk.Label(basic, text="輸出 PDF：").grid(row=0, column=0, sticky=tk.W, pady=4)
        self.entry_pdf = ttk.Entry(basic)
        self.entry_pdf.insert(0, "book.pdf")
        self.entry_pdf.grid(row=0, column=1, sticky=tk.EW, pady=4)
        ttk.Button(basic, text="選擇…", command=self._choose_output).grid(
            row=0, column=2, padx=(6, 0), pady=4
        )

        ttk.Label(basic, text="最大畫面數：").grid(row=1, column=0, sticky=tk.W, pady=4)
        self.entry_pages = ttk.Entry(basic, width=14)
        self.entry_pages.insert(0, "500")
        self.entry_pages.grid(row=1, column=1, sticky=tk.W, pady=4)

        ttk.Label(basic, text="翻頁間隔：").grid(row=2, column=0, sticky=tk.W, pady=4)
        self.combo_delay = ttk.Combobox(
            basic,
            values=[
                "0.5",
                "0.6",
                "0.7",
                "0.8",
                "0.9",
                "1.0",
                "1.1",
                "1.2",
                "1.3",
                "1.4",
                "1.5",
                "1.6",
                "1.7",
                "1.8",
                "1.9",
                "2.0",
            ],
            width=12,
            state="readonly",
        )
        self.combo_delay.set("1.0")
        self.combo_delay.grid(row=2, column=1, sticky=tk.W, pady=4)
        ttk.Label(basic, text="秒").grid(row=2, column=1, padx=(100, 0), sticky=tk.W)

        ttk.Label(basic, text="翻頁方式：").grid(row=3, column=0, sticky=tk.W, pady=4)
        self.combo_action = ttk.Combobox(
            basic,
            values=[
                "向右鍵 (AppleScript / Right Arrow)",
                "空白鍵 (Space)",
                "Page Down (向下換頁)",
                "點擊頁面右側 (Mouse Click)",
            ],
            state="readonly",
        )
        self.combo_action.set("向右鍵 (AppleScript / Right Arrow)")
        self.combo_action.grid(row=3, column=1, columnspan=2, sticky=tk.EW, pady=4)

        self.var_autostop = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            basic,
            text="智慧末頁停止（連續兩次畫面不再變動）",
            variable=self.var_autostop,
        ).grid(row=4, column=0, columnspan=3, sticky=tk.W, pady=(5, 2))

        processing = ttk.LabelFrame(container, text="v1.2 頁面處理", padding=10)
        processing.grid(row=3, column=0, sticky=tk.EW, pady=(10, 0))
        processing.columnconfigure(1, weight=1)

        ttk.Label(processing, text="頁面邊界：").grid(
            row=0, column=0, sticky=tk.W, pady=4
        )
        self.combo_crop = ttk.Combobox(
            processing,
            values=list(CROP_MODE_LABELS.keys()),
            state="readonly",
        )
        # Keep v1.1.0 output unchanged until the user explicitly enables crop.
        self.combo_crop.set("不裁切（保留原圖）")
        self.combo_crop.grid(row=0, column=1, columnspan=3, sticky=tk.EW, pady=4)
        self.combo_crop.bind("<<ComboboxSelected>>", self._on_crop_mode_change)

        ttk.Label(processing, text="自動裁切：").grid(
            row=1, column=0, sticky=tk.W, pady=4
        )
        auto_frame = ttk.Frame(processing)
        auto_frame.grid(row=1, column=1, columnspan=3, sticky=tk.W)
        ttk.Label(auto_frame, text="敏感度").grid(row=0, column=0)
        self.spin_tolerance = ttk.Spinbox(auto_frame, from_=5, to=80, width=6)
        self.spin_tolerance.set("24")
        self.spin_tolerance.grid(row=0, column=1, padx=(5, 16))
        ttk.Label(auto_frame, text="保留邊距").grid(row=0, column=2)
        self.spin_padding = ttk.Spinbox(auto_frame, from_=0, to=100, width=6)
        self.spin_padding.set("6")
        self.spin_padding.grid(row=0, column=3, padx=(5, 0))

        ttk.Label(processing, text="手動邊距：").grid(
            row=2, column=0, sticky=tk.W, pady=4
        )
        margin_frame = ttk.Frame(processing)
        margin_frame.grid(row=2, column=1, columnspan=3, sticky=tk.W)
        self.margin_entries = []
        for column, label in enumerate(("左", "上", "右", "下")):
            ttk.Label(margin_frame, text=label).grid(row=0, column=column * 2)
            entry = ttk.Entry(margin_frame, width=5)
            entry.insert(0, "0")
            entry.grid(row=0, column=column * 2 + 1, padx=(3, 10))
            self.margin_entries.append(entry)

        ttk.Label(processing, text="頁面模式：").grid(
            row=3, column=0, sticky=tk.W, pady=4
        )
        self.combo_page_mode = ttk.Combobox(
            processing,
            values=list(PAGE_MODE_LABELS.keys()),
            state="readonly",
        )
        self.combo_page_mode.set("單頁模式")
        self.combo_page_mode.grid(row=3, column=1, columnspan=3, sticky=tk.EW, pady=4)
        self.combo_page_mode.bind("<<ComboboxSelected>>", self._on_page_mode_change)

        ttk.Label(processing, text="閱讀順序：").grid(
            row=4, column=0, sticky=tk.W, pady=4
        )
        self.combo_reading_order = ttk.Combobox(
            processing,
            values=list(READING_ORDER_LABELS.keys()),
            state="disabled",
        )
        self.combo_reading_order.set("由左至右")
        self.combo_reading_order.grid(
            row=4, column=1, columnspan=3, sticky=tk.EW, pady=4
        )

        controls = ttk.Frame(container)
        controls.grid(row=4, column=0, sticky=tk.EW, pady=(10, 0))
        for index in range(3):
            controls.columnconfigure(index, weight=1)

        self.btn_test_turn = ttk.Button(
            controls, text="測試翻頁", command=self.test_turn_page
        )
        self.btn_test_turn.grid(row=0, column=0, sticky=tk.EW, padx=(0, 4))
        self.btn_calibrate = ttk.Button(
            controls, text="1. 校準截圖區域", command=self.start_calibration
        )
        self.btn_calibrate.grid(row=0, column=1, sticky=tk.EW, padx=4)
        self.btn_preview = ttk.Button(
            controls,
            text="預覽裁切／分頁",
            command=self.preview_processing,
            state=tk.DISABLED,
        )
        self.btn_preview.grid(row=0, column=2, sticky=tk.EW, padx=(4, 0))

        self.lbl_region = ttk.Label(
            container, text="截圖範圍：尚未校準", foreground="gray"
        )
        self.lbl_region.grid(row=5, column=0, pady=(8, 2))

        action_frame = ttk.Frame(container)
        action_frame.grid(row=6, column=0, sticky=tk.EW, pady=(8, 0))
        action_frame.columnconfigure(0, weight=3)
        action_frame.columnconfigure(1, weight=1)
        self.btn_start = ttk.Button(
            action_frame,
            text="2. 開始自動截圖並生成 PDF",
            command=self.start_capture_thread,
            state=tk.DISABLED,
        )
        self.btn_start.grid(row=0, column=0, sticky=tk.EW, padx=(0, 4))
        self.btn_stop = ttk.Button(
            action_frame,
            text="停止並輸出",
            command=self.request_stop,
            state=tk.DISABLED,
        )
        self.btn_stop.grid(row=0, column=1, sticky=tk.EW, padx=(4, 0))

        self.lbl_status = ttk.Label(container, text="狀態：準備就緒")
        self.lbl_status.grid(row=7, column=0, sticky=tk.W, pady=(10, 2))
        self.progress = ttk.Progressbar(
            container, orient=tk.HORIZONTAL, mode="determinate"
        )
        self.progress.grid(row=8, column=0, sticky=tk.EW, pady=4)

        ttk.Label(
            container,
            text=(
                "開始後請在 5 秒內點擊閱讀器視窗取得焦點。\n"
                "緊急中止：將滑鼠移至螢幕任一角落；程式會用已擷取頁面輸出 PDF。"
            ),
            foreground="#b00020",
            justify=tk.LEFT,
        ).grid(row=9, column=0, sticky=tk.W, pady=(4, 0))

        self._on_crop_mode_change()

    def _choose_output(self) -> None:
        selected = filedialog.asksaveasfilename(
            title="選擇輸出 PDF",
            defaultextension=".pdf",
            filetypes=[("PDF 文件", "*.pdf")],
            initialfile=os.path.basename(self.entry_pdf.get() or "book.pdf"),
        )
        if selected:
            self.entry_pdf.delete(0, tk.END)
            self.entry_pdf.insert(0, selected)

    def _on_crop_mode_change(self, _event: object = None) -> None:
        manual = CROP_MODE_LABELS.get(self.combo_crop.get()) == "manual"
        automatic = CROP_MODE_LABELS.get(self.combo_crop.get()) == "auto"
        for entry in self.margin_entries:
            entry.configure(state="normal" if manual else "disabled")
        self.spin_tolerance.configure(state="normal" if automatic else "disabled")
        self.spin_padding.configure(state="normal" if automatic else "disabled")

    def _on_page_mode_change(self, _event: object = None) -> None:
        single = PAGE_MODE_LABELS.get(self.combo_page_mode.get()) == "single"
        self.combo_reading_order.configure(
            state="disabled" if single else "readonly"
        )

    def log(self, text: str) -> None:
        self.root.after(0, lambda: self.lbl_status.configure(text="狀態：" + text))

    def _set_progress(self, value: int, maximum: Optional[int] = None) -> None:
        def update() -> None:
            if maximum is not None:
                self.progress["maximum"] = maximum
            self.progress["value"] = value

        self.root.after(0, update)

    def test_turn_page(self) -> None:
        self.btn_test_turn.configure(state=tk.DISABLED)
        self._test_countdown(3)

    def _test_countdown(self, remaining: int) -> None:
        if remaining > 0:
            self.lbl_status.configure(
                text="狀態：請切換並點擊閱讀器視窗… {0}".format(remaining)
            )
            self.root.after(1000, self._test_countdown, remaining - 1)
            return

        action = self.combo_action.get()
        click_x, click_y = self._click_position()

        def worker() -> None:
            try:
                trigger_turn_page(action, click_x, click_y)
                self.log("翻頁指令已發送，請確認閱讀器有換頁。")
            except Exception as error:
                self.log("翻頁測試失敗：{0}".format(error))
            finally:
                self.root.after(
                    0, lambda: self.btn_test_turn.configure(state=tk.NORMAL)
                )

        threading.Thread(target=worker, daemon=True).start()

    def start_calibration(self) -> None:
        self.btn_calibrate.configure(state=tk.DISABLED)
        messagebox.showinfo(
            "校準提示",
            "按下確定後有 4 秒，請將滑鼠移至閱讀頁面的左上角。",
        )
        self._calibration_countdown("left", 4, None)

    def _calibration_countdown(
        self,
        target: str,
        remaining: int,
        first_point: Optional[Tuple[int, int]],
    ) -> None:
        label = "左上角" if target == "left" else "右下角"
        if remaining > 0:
            self.lbl_status.configure(
                text="狀態：請移至{0}… {1} 秒".format(label, remaining)
            )
            self.root.after(
                1000,
                self._calibration_countdown,
                target,
                remaining - 1,
                first_point,
            )
            return

        point = tuple(int(value) for value in pyautogui.position())
        if target == "left":
            messagebox.showinfo(
                "校準提示",
                "已記錄左上角。按下確定後有 4 秒，請將滑鼠移至右下角。",
            )
            self._calibration_countdown("right", 4, point)
            return

        if first_point is None:
            self._calibration_failed("未能取得左上角座標。")
            return
        x1, y1 = first_point
        x2, y2 = point
        left, top = min(x1, x2), min(y1, y2)
        width, height = abs(x2 - x1), abs(y2 - y1)
        if width < 20 or height < 20:
            self._calibration_failed("截圖範圍太小，請重新校準。")
            return

        self.region = (left, top, width, height)
        self.lbl_region.configure(
            text="截圖範圍：({0}, {1})　{2} × {3} px".format(
                left, top, width, height
            ),
            foreground="green",
        )
        self.lbl_status.configure(text="狀態：校準完成，可先預覽頁面處理。")
        self.btn_calibrate.configure(state=tk.NORMAL)
        self.btn_start.configure(state=tk.NORMAL)
        self.btn_preview.configure(state=tk.NORMAL)

    def _calibration_failed(self, message: str) -> None:
        self.btn_calibrate.configure(state=tk.NORMAL)
        self.lbl_status.configure(text="狀態：" + message)
        messagebox.showerror("校準失敗", message)

    def _click_position(self) -> Tuple[int, int]:
        if not self.region:
            return (0, 0)
        return (
            self.region[0] + int(self.region[2] * 0.9),
            self.region[1] + int(self.region[3] * 0.5),
        )

    def _processing_settings(self) -> Dict[str, object]:
        crop_mode = CROP_MODE_LABELS[self.combo_crop.get()]
        page_mode = PAGE_MODE_LABELS[self.combo_page_mode.get()]
        reading_order = READING_ORDER_LABELS[self.combo_reading_order.get()]
        try:
            margins = CropMargins(
                left=int(self.margin_entries[0].get() or "0"),
                top=int(self.margin_entries[1].get() or "0"),
                right=int(self.margin_entries[2].get() or "0"),
                bottom=int(self.margin_entries[3].get() or "0"),
            )
            tolerance = int(self.spin_tolerance.get() or "24")
            padding = int(self.spin_padding.get() or "6")
        except ValueError:
            raise ValueError("裁切設定必須是整數。")
        if any(value < 0 for value in (
            margins.left, margins.top, margins.right, margins.bottom, padding
        )):
            raise ValueError("裁切設定不可為負數。")
        if not 5 <= tolerance <= 80:
            raise ValueError("自動裁切敏感度必須介乎 5 至 80。")
        if crop_mode == "manual" and self.region:
            margins.validated(self.region[2], self.region[3])
        return {
            "crop_mode": crop_mode,
            "crop_margins": margins,
            "auto_crop_tolerance": tolerance,
            "auto_crop_padding": padding,
            "page_mode": page_mode,
            "reading_order": reading_order,
        }

    def preview_processing(self) -> None:
        if not self.region:
            messagebox.showwarning("未校準", "請先校準截圖區域。")
            return
        try:
            settings = self._processing_settings()
        except ValueError as error:
            messagebox.showerror("設定錯誤", str(error))
            return
        self.btn_preview.configure(state=tk.DISABLED)
        self.lbl_status.configure(text="狀態：正在擷取預覽…")

        def worker() -> None:
            try:
                original = pyautogui.screenshot(region=self.region)
                outputs = process_page(original, **settings)
                self.root.after(0, self._show_preview, original, outputs)
            except Exception as error:
                error_text = str(error)
                self.root.after(
                    0,
                    lambda message=error_text: messagebox.showerror(
                        "預覽失敗", "未能產生預覽：{0}".format(message)
                    ),
                )
            finally:
                self.root.after(
                    0, lambda: self.btn_preview.configure(state=tk.NORMAL)
                )

        threading.Thread(target=worker, daemon=True).start()

    def _show_preview(
        self, original: Image.Image, outputs: List[Image.Image]
    ) -> None:
        window = tk.Toplevel(self.root)
        window.title("頁面處理預覽")
        window.transient(self.root)
        wrapper = ttk.Frame(window, padding=12)
        wrapper.pack(fill=tk.BOTH, expand=True)
        images = [("原始擷取", original)] + [
            ("輸出第 {0} 頁".format(index), image)
            for index, image in enumerate(outputs, 1)
        ]
        photo_refs = []
        for column, (label, image) in enumerate(images):
            ttk.Label(wrapper, text=label, font=("Arial", 10, "bold")).grid(
                row=0, column=column, padx=6, pady=(0, 6)
            )
            preview = image.copy()
            preview.thumbnail((380, 520))
            photo = ImageTk.PhotoImage(preview)
            photo_refs.append(photo)
            ttk.Label(wrapper, image=photo).grid(row=1, column=column, padx=6)
            ttk.Label(
                wrapper,
                text="{0} × {1} px".format(image.width, image.height),
                foreground="#666666",
            ).grid(row=2, column=column, pady=(5, 0))
        window._photo_refs = photo_refs  # type: ignore[attr-defined]
        self.lbl_status.configure(text="狀態：預覽完成；可調整後再次預覽。")

    def _capture_settings(self) -> Dict[str, object]:
        if not self.region:
            raise ValueError("請先完成截圖區域校準。")
        try:
            pages = int(self.entry_pages.get().strip())
            delay = float(self.combo_delay.get().strip())
        except ValueError:
            raise ValueError("最大畫面數及翻頁間隔必須是數字。")
        if pages < 1:
            raise ValueError("最大畫面數必須最少為 1。")
        if not 0.5 <= delay <= 2.0:
            raise ValueError("翻頁間隔必須介乎 0.5 至 2.0 秒。")

        pdf_name = self.entry_pdf.get().strip() or "book.pdf"
        if not pdf_name.lower().endswith(".pdf"):
            pdf_name += ".pdf"
        output_path = os.path.abspath(os.path.expanduser(pdf_name))
        parent = os.path.dirname(output_path)
        if parent and not os.path.isdir(parent):
            raise ValueError("輸出資料夾不存在：{0}".format(parent))

        settings = self._processing_settings()
        settings.update(
            {
                "pages": pages,
                "delay": delay,
                "action": self.combo_action.get(),
                "autostop": self.var_autostop.get(),
                "output_path": output_path,
            }
        )
        return settings

    def start_capture_thread(self) -> None:
        try:
            settings = self._capture_settings()
        except ValueError as error:
            messagebox.showerror("設定錯誤", str(error))
            return

        self.stop_event.clear()
        self.capture_running = True
        self.btn_start.configure(state=tk.DISABLED)
        self.btn_calibrate.configure(state=tk.DISABLED)
        self.btn_preview.configure(state=tk.DISABLED)
        self.btn_stop.configure(state=tk.NORMAL)
        self._set_progress(0, int(settings["pages"]))
        threading.Thread(
            target=self._capture_process,
            args=(settings,),
            daemon=True,
        ).start()

    def request_stop(self) -> None:
        if self.capture_running:
            self.stop_event.set()
            self.btn_stop.configure(state=tk.DISABLED)
            self.lbl_status.configure(text="狀態：正在停止並輸出已擷取頁面…")

    def _capture_process(self, settings: Dict[str, object]) -> None:
        temp_dir = tempfile.mkdtemp(prefix="autopage_pdf_")
        image_paths: List[str] = []
        last_image: Optional[Image.Image] = None
        duplicate_count = 0
        output_page = 0
        completion_note = ""
        error_message: Optional[str] = None

        try:
            for remaining in range(5, 0, -1):
                if self.stop_event.is_set():
                    completion_note = "使用者在開始前停止。"
                    break
                self.log("請點擊閱讀器視窗取得焦點… {0} 秒後開始".format(remaining))
                time.sleep(1)

            click_x, click_y = self._click_position()
            pages = int(settings["pages"])
            for capture_number in range(1, pages + 1):
                if self.stop_event.is_set():
                    completion_note = "已按要求停止。"
                    break

                screenshot = pyautogui.screenshot(region=self.region)
                duplicate = bool(settings["autostop"]) and is_image_duplicate(
                    screenshot, last_image
                )
                if duplicate:
                    duplicate_count += 1
                    self.log(
                        "畫面重複確認 {0}/2；正在檢查是否已到末頁…".format(
                            duplicate_count
                        )
                    )
                    if duplicate_count >= 2:
                        completion_note = "已智慧識別最後一頁。"
                        break
                else:
                    duplicate_count = 0
                    processed_pages = process_page(
                        screenshot,
                        crop_mode=str(settings["crop_mode"]),
                        crop_margins=settings["crop_margins"],
                        auto_crop_tolerance=int(settings["auto_crop_tolerance"]),
                        auto_crop_padding=int(settings["auto_crop_padding"]),
                        page_mode=str(settings["page_mode"]),
                        reading_order=str(settings["reading_order"]),
                    )
                    for processed in processed_pages:
                        output_page += 1
                        path = os.path.join(
                            temp_dir, "page_{0:05d}.png".format(output_page)
                        )
                        processed.save(path, format="PNG", optimize=False)
                        image_paths.append(path)
                    last_image = screenshot.copy()
                    self.log(
                        "已擷取第 {0} 個畫面；PDF 頁數：{1}".format(
                            capture_number, output_page
                        )
                    )
                    self._set_progress(capture_number)

                if capture_number < pages:
                    trigger_turn_page(str(settings["action"]), click_x, click_y)
                    time.sleep(float(settings["delay"]))

        except pyautogui.FailSafeException:
            completion_note = "已觸發滑鼠角落安全停止。"
        except Exception as error:
            error_message = str(error)

        output_path = str(settings["output_path"])
        if image_paths:
            try:
                self.log("正在無損合併 {0} 頁 PDF…".format(len(image_paths)))
                with open(output_path, "wb") as output_file:
                    output_file.write(img2pdf.convert(image_paths))
            except Exception as error:
                error_message = "PDF 合併失敗：{0}".format(error)

        if error_message:
            self.root.after(
                0,
                self._finish_capture,
                False,
                error_message,
                output_path,
                len(image_paths),
                temp_dir,
            )
            return

        shutil.rmtree(temp_dir, ignore_errors=True)
        if image_paths:
            detail = completion_note or "已達設定的最大畫面數。"
            self.root.after(
                0,
                self._finish_capture,
                True,
                detail,
                output_path,
                len(image_paths),
                None,
            )
        else:
            self.root.after(
                0,
                self._finish_capture,
                False,
                completion_note or "未擷取任何頁面。",
                output_path,
                0,
                None,
            )

    def _finish_capture(
        self,
        success: bool,
        detail: str,
        output_path: str,
        page_count: int,
        retained_temp_dir: Optional[str],
    ) -> None:
        self.capture_running = False
        self.btn_start.configure(state=tk.NORMAL if self.region else tk.DISABLED)
        self.btn_calibrate.configure(state=tk.NORMAL)
        self.btn_preview.configure(state=tk.NORMAL if self.region else tk.DISABLED)
        self.btn_stop.configure(state=tk.DISABLED)
        if success:
            self.lbl_status.configure(
                text="狀態：完成，共輸出 {0} 頁。".format(page_count)
            )
            messagebox.showinfo(
                "完成",
                "PDF 生成成功！\n\n頁數：{0}\n檔案：{1}\n\n{2}".format(
                    page_count, output_path, detail
                ),
            )
            return

        message = detail
        if retained_temp_dir:
            message += "\n\n暫存圖片已保留於：\n" + retained_temp_dir
        self.lbl_status.configure(text="狀態：未能完成－" + detail)
        messagebox.showerror("未能完成", message)

    def _on_close(self) -> None:
        if self.capture_running:
            close = messagebox.askyesno(
                "正在擷取",
                "擷取仍在進行。確定要停止並關閉程式嗎？",
            )
            if not close:
                return
            self.stop_event.set()
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    root.lift()
    try:
        root.attributes("-topmost", True)
        root.after_idle(root.attributes, "-topmost", False)
    except tk.TclError:
        pass
    app = AutoPageApp(root)
    root._autopage_app = app  # type: ignore[attr-defined]
    root.mainloop()


if __name__ == "__main__":
    main()
