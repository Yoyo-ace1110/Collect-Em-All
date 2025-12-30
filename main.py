from __future__ import annotations
from enum import Enum
from pyscreeze import Box
from PIL import Image
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
MIN_SIMILARITY: float = 0.83        # 圖片最低相似度
target_path: str = "./target.png"   # 球的圖片路徑
screenshot_path = "current_game_area.png"
url: str = "https://www.crazygames.com/game/collect-em-all"

def get_box_color(image: Image.Image, box: Box) -> Colors:
    """ 取得該box的顏色 """
    center_x, center_y = pyautogui.center(box)
    color = image.getpixel((int(center_x), int(center_y)))
    if not (isinstance(color, tuple) and len(color) == 3):
        raise RuntimeError(f"invalid color: {color}")
    return Colors.to_color(color[:3])

def read_matrix(image_path: str):
    """尋找球並寫入矩陣"""
    locations: list[Box] = list(
        # 螢幕上尋找球
        pyautogui.locateAll(
            target_path, 
            image_path, 
            confidence=MIN_SIMILARITY, 
            grayscale=True
        )
    )
    all_locations: list[Box] = []
    # 打開圖片並轉為 RGB
    image = Image.open(image_path).convert("RGB")
    # 去除相近座標
    for box in locations:
        # 檢查這個點是否已經在 all_locations 裡面了
        is_duplicate = False
        for u_box in all_locations:
            # 計算兩個中心點的距離
            dist = ((box.left - u_box.left)**2 + (box.top - u_box.top)**2)**0.5
            # 如果距離小於 n 像素，視為同一顆球
            if dist < 10:
                is_duplicate = True
                break
        if not is_duplicate:
            all_locations.append(box)
    print(f"DEBUG: 原始找到 {len(locations)} 個點，去重後剩餘 {len(all_locations)} 顆球")
    if len(all_locations) != 36: raise RuntimeError("找不到6*6=36顆球")
    
    # 分成一個個row並加入matrix
    all_locations.sort(key=lambda box : box.top)
    for i in range(0, 36, 6):
        # 分割成6行
        slice_ = all_locations[i:i+6]
        slice_.sort(key = lambda box : box.left)
        # 取得顏色
        row = [get_box_color(image, element) for element in slice_]
        # 加入matrix
        matrix.append(row)

def main():
    """ 主程式 """
    sync: Playwright = sync_playwright().__enter__()
    browser = sync.chromium.launch(headless=False, args=["--start-maximized"])
    context = browser.new_context(no_viewport=True)
    page = context.new_page()
    
    print("正在開啟網頁...")
    page.goto("https://www.crazygames.com/game/collect-em-all")
    page.wait_for_selector("#game-iframe")
    page.wait_for_load_state("domcontentloaded") # networkidle
    
    print("正在辨識遊戲框架...")
    game_element = page.locator("#game-iframe")
    game_element.scroll_into_view_if_needed()
    time.sleep(10)
    game_element.screenshot(path=screenshot_path)
    rect = game_element.bounding_box()
    if not rect: raise RuntimeError("找不到遊戲框架")
    game_region = (int(rect['x']), int(rect['y']), int(rect['width']), int(rect['height']))
    print(f"成功鎖定遊戲區域: {game_region}")
    
    print("正在讀取各格的顏色")
    read_matrix(screenshot_path)
    print(matrix)
    
    print("正在關閉網頁...")
    browser.close()

# 執行main
if __name__ == "__main__": main()
