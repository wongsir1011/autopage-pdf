# AutoPage PDF v1.2.0

跨平台（Windows／macOS）的本機螢幕自動翻頁截圖與無損 PDF 合併工具。

## v1.2.0 新功能

- **Auto-crop**：偵測頁面與閱讀器背景的邊界，自動去除外圍工具列及留白。
- **手動裁切**：可用像素分別設定左、上、右、下邊距。
- **雙頁自動分割**：偵測畫面中央較安靜的書脊／留白，把跨頁畫面輸出為兩個 PDF 頁面。
- **閱讀順序**：支援由左至右及由右至左。
- **處理預覽**：正式擷取前查看原圖、裁切及分頁結果和實際像素尺寸。
- **停止並輸出**：使用者可隨時停止，並用已完成的頁面生成 PDF。

## 原有功能

- 圖形化互動校準截圖範圍。
- 0.5–2.0 秒翻頁間隔。
- 向右鍵、空白鍵、Page Down 或滑鼠右側熱區翻頁。
- macOS 優先透過 AppleScript 發送按鍵。
- 連續兩次畫面重複時智慧識別最後一頁。
- PNG 無損合併為高畫質 PDF。
- 滑鼠移至螢幕任一角落即可緊急停止。

## 快速使用

### Windows

1. 安裝 Python 3.8 或以上版本，安裝時勾選 **Add Python to PATH**。
2. 雙擊 `AutoPage_Windows.bat`；首次執行會自動建立虛擬環境及安裝套件。
3. 如需單一 EXE，雙擊 `build_exe_windows.bat`，完成後到 `dist` 資料夾取用。

### macOS

1. 雙擊 `AutoPage.command`。
2. 首次執行時，在「系統設定 → 隱私權與安全性」允許終端機／Python使用「螢幕錄製」和「輔助功能」。
3. 如果系統提示缺少 Tkinter，可按所用 Python 版本安裝 `python-tk`。

### 命令列啟動

```bash
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt
python autopage_gui.py
```

## 建議工作流程

1. 開啟閱讀器並翻到起始頁。
2. 在 AutoPage PDF 選擇輸出位置、翻頁方式、裁切及單／雙頁模式。
3. 校準閱讀範圍。
4. 點選「預覽裁切／分頁」；如有誤裁，改用手動邊距或中央分割。
5. 點選「開始」，並在倒數期間點擊閱讀器取得焦點。

> Auto-crop 以截圖四角推算閱讀器背景；如果頁面填滿整個校準區域，或背景與頁面顏色非常接近，建議改用手動裁切。

## 專案結構

- `autopage_gui.py`：GUI、跨平台翻頁及擷取流程。
- `image_processing.py`：裁切、書脊偵測、分頁及末頁差異計算。
- `autopage_pdf.py`：相容舊啟動方式的入口。
- `tests/`：不需要桌面環境的影像處理測試。

## 使用守則

本工具只應用於使用者有權存取、備份或轉換的內容。請遵守相關版權法規、服務條款及機構資料保障要求；本工具不提供或繞過 DRM、付費牆或其他存取限制。
