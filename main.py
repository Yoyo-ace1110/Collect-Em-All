from __future__ import annotations
from enum import Enum
from pyscreeze import Box
from playwright.sync_api import sync_playwright, Playwright
import pyautogui, time

class Colors(Enum):
    # 各種顏色(RGB)
    Red = (255, 0, 29)
    Green = (77, 186, 48)
    Blue = (82, 130, 246)
    Orange = (249, 140, 41)
    Purple = (150, 43, 235)
    
    # 成員變數
    @property
    def r(self): return self.value[0]
    @property
    def g(self): return self.value[1]
    @property
    def b(self): return self.value[2]

    # 函數
    @classmethod
    def to_color(cls, rgb: tuple[int, int, int]):
        """ 將tuple的顏色轉為Colors的成員 """
        for color in Colors:
            if color.value == rgb: return color
        raise RuntimeError(f"未找到相對應的color: {rgb}")

class Rect:
    def __init__(self, x: int, y: int, width: int, height: int):
        """ 初始化矩形 """
        self.x, self.y = x, y
        self.width, self.height = width, height
    
    def get_pos(self):
        return (self.x, self.y)
    
    def get_size(self):
        return (self.width, self.height)
    
    def get_tuple(self):
        return (self.x, self.y, self.width, self.height)

matrix: list[list[Colors]] = []     # 主要的矩陣
MIN_SIMILARITY: float = 0.75        # 圖片最低相似度
target_path: str = "./target.png"   # 球的圖片路徑
url: str = "https://www.crazygames.com/game/collect-em-all"

def get_box_color(box: Box) -> Colors:
    """ 取得該box的顏色 """
    color = pyautogui.pixel(*pyautogui.center(box))
    return Colors.to_color(color)

def read_matrix():
    """尋找球並寫入矩陣"""
    all_locations: list[Box] = list(
        # 螢幕上尋找球
        pyautogui.locateAllOnScreen(target_path, confidence=MIN_SIMILARITY, grayscale=True)
    )
    if len(all_locations) != 36: raise RuntimeError("找不到6*6=36顆球")
    
    # 分成一個個row並加入matrix
    all_locations.sort(key=lambda box : box.top)
    for i in range(0, 36, 6):
        # 分割成6行
        slice_ = all_locations[i:i+6]
        slice_.sort(key = lambda box : box.left)
        # 取得顏色
        row = [get_box_color(element) for element in slice_]
        # 加入matrix
        matrix.append(row)

def main():
    """ 主程式 """
    sync: Playwright = sync_playwright().__enter__()
    browser = sync.chromium.launch(headless=False)
    
    print("正在開啟網頁...")
    page = browser.new_page()
    page.goto("https://www.crazygames.com/game/collect-em-all")
    page.wait_for_load_state("domcontentloaded")
    
    """
    print("正在點擊 play_now 按鈕...")
    # play_button = page.get_by_text("Play now")
    # play_button.click()
    try:
        # 策略 A: 直接尋找最深層的文字並點擊
        # 使用 force=True 強制點擊，避開元素被遮擋的檢查
        page.get_by_text("Play now").first.click(timeout=5000, force=True)
    except:
        print("主頁面點擊失敗，嘗試穿透 iframe...")
        try:
            # 策略 B: 遍歷所有 iframe 尋找按鈕
            # 這是處理嵌入式遊戲最暴力但也最有效的方法
            for frame in page.frames:
                btn = frame.get_by_text("Play now")
                if btn.count() > 0:
                    btn.first.click(timeout=5000)
                    print("在 iframe 中成功點擊！")
                    break
        except Exception as e:
            print(f"所有點擊嘗試均失敗: {e}")
    page.wait_for_load_state("domcontentloaded")
    """
    
    print("正在讀取各格的顏色")
    time.sleep(10)
    read_matrix()
    print(matrix)
    
    print("正在關閉網頁...")
    # browser.close()

# 執行main
if __name__ == "__main__": main()
