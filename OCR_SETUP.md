# OCR 安裝指南

AutoPage PDF 的一般圖片 PDF 不需要 Tesseract。只有「可搜尋 PDF」及「可搜尋 PDF＋TXT」模式需要另行安裝本機 Tesseract OCR。

## Windows

1. 依 [Tesseract 官方安裝說明](https://tesseract-ocr.github.io/tessdoc/Installation.html)安裝 Tesseract 5。
2. 安裝時加入所需語言，或把相應的 `.traineddata` 放進 Tesseract 的 `tessdata` 資料夾：
   - `eng`：英文
   - `chi_tra`：繁體中文
   - `chi_sim`：簡體中文
3. 重新開啟 AutoPage PDF，選擇辨識語言後按「檢查 OCR」。

程式會自動尋找 `PATH`、`C:\Program Files\Tesseract-OCR`、`C:\Program Files (x86)\Tesseract-OCR` 及常見的使用者安裝位置。

## macOS

先安裝 [Homebrew](https://brew.sh/)，再於「終端機」執行：

```bash
brew install tesseract tesseract-lang
```

完成後重新開啟 AutoPage PDF，選擇辨識語言並按「檢查 OCR」。程式支援 Apple Silicon 的 `/opt/homebrew/bin` 及 Intel Mac 的 `/usr/local/bin`。

## 手動檢查語言包

在「命令提示字元」或「終端機」執行：

```bash
tesseract --version
tesseract --list-langs
```

語言清單必須包含 AutoPage PDF 內所選模式需要的全部代碼。若只看到 `eng`，仍可使用英文 OCR，或暫時改回一般圖片 PDF。

Tesseract 語言資料及檔案說明可參閱[官方文件](https://tesseract-ocr.github.io/tessdoc/Data-Files.html)。
