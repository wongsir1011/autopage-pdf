import os
import time
import pyautogui
import img2pdf

# 安全機制：若需緊急中止程式，直接將滑鼠游標迅速移到螢幕四個角落任一處即可停止
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.1

def calibrate_region():
    """引導定位截圖區域的左上角與右下角座標"""
    print("\n--- 步驟 1：定位截圖區域 ---")
    print("請將滑鼠移至閱讀器內容的【左上角】，5 秒後自動記錄座標...")
    for i in range(5, 0, -1):
        print(f"{i}...", end="", flush=True)
        time.sleep(1)
    x1, y1 = pyautogui.position()
    print(f"\n左上角座標已記錄：({x1}, {y1})")

    print("\n請將滑鼠移至閱讀器內容的【右下角】，5 秒後自動記錄座標...")
    for i in range(5, 0, -1):
        print(f"{i}...", end="", flush=True)
        time.sleep(1)
    x2, y2 = pyautogui.position()
    print(f"\n右下角座標已記錄：({x2}, {y2})")

    left = min(x1, x2)
    top = min(y1, y2)
    width = abs(x2 - x1)
    height = abs(y2 - y1)

    return (left, top, width, height)

def main():
    print("=== 電子書自動截圖與 PDF 轉換工具 ===")
    
    output_pdf = input("請輸入輸出 PDF 檔名（例如 book.pdf）: ").strip() or "output.pdf"
    if not output_pdf.lower().endswith(".pdf"):
        output_pdf += ".pdf"

    try:
        total_pages = int(input("請輸入預計截圖的總頁數: ").strip())
    except ValueError:
        print("錯誤：頁數必須為數字。")
        return

    delay_input = input("請輸入翻頁等待時間（秒，建議 0.8 ~ 1.5，預設 1.0）: ").strip()
    delay_time = float(delay_input) if delay_input else 1.0

    # 1. 取得截圖範圍
    region = calibrate_region()
    print(f"\n截圖範圍設定完成：左上角 ({region[0]}, {region[1]}), 寬度 {region[2]} px, 高度 {region[3]} px")

    # 2. 準備暫存資料夾
    temp_dir = "temp_screenshots"
    os.makedirs(temp_dir, exist_ok=True)
    image_paths = []

    print("\n--- 步驟 2：準備開始擷取 ---")
    print("請在 5 秒內將視窗切換至 Kobo 閱讀器，並翻到欲截圖的起始頁面...")
    for i in range(5, 0, -1):
        print(f"{i}...", end="", flush=True)
        time.sleep(1)
    print("\n開始自動擷取中...")

    try:
        for page in range(1, total_pages + 1):
            # 擷取指定區域
            screenshot = pyautogui.screenshot(region=region)
            img_path = os.path.join(temp_dir, f"page_{page:04d}.png")
            screenshot.save(img_path)
            image_paths.append(img_path)
            print(f"[{page}/{total_pages}] 已擷取第 {page} 頁")

            # 模擬鍵盤向右鍵翻頁（最後一頁不翻頁）
            if page < total_pages:
                pyautogui.press("right")
                time.sleep(delay_time)

    except KeyboardInterrupt:
        print("\n使用者手動中斷。將使用已擷取的頁面繼續生成 PDF...")
    except pyautogui.FailSafeException:
        print("\n觸發緊急中止。將使用已擷取的頁面繼續生成 PDF...")

    # 3. 合併為 PDF
    if not image_paths:
        print("未擷取任何頁面，程式結束。")
        return

    print("\n--- 步驟 3：合併圖片為 PDF ---")
    image_paths.sort()
    
    with open(output_pdf, "wb") as f:
        f.write(img2pdf.convert(image_paths))
    print(f"PDF 檔案生成完成：{output_pdf}")

    # 4. 清理暫存圖片（可依需求選擇是否保留）
    clean_choice = input("是否刪除暫存截圖圖片？(y/n，預設 y): ").strip().lower()
    if clean_choice in ["", "y", "yes"]:
        for p in image_paths:
            if os.path.exists(p):
                os.remove(p)
        if os.path.exists(temp_dir):
            os.rmdir(temp_dir)
        print("暫存圖片已清理完畢。")

if __name__ == "__main__":
    main()