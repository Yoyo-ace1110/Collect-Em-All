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

    def __str__(self) -> str:
        return f"Colors.{self.name}"

    def __repr__(self) -> str:
        return self.__str__()

class Point:
    def __init__(self, x: int|float, y: int|float) -> None:
        ''' 初始化座標 '''
        self.x: int = int(x)
        self.y: int = int(y)
    
    def get_pair(self) -> tuple[int, int]:
        ''' 取得tuple(x, y) '''
        return (self.x, self.y)

    def __str__(self) -> str:
        return f"Point({self.x}, {self.y})"

    def __repr__(self) -> str:
        return self.__str__()

matrix: list[list[Colors]] = []             # 主要的矩陣
MIN_SIMILARITY: float = 0.83                # 圖片最低相似度
target_path: str = "./target.png"           # 球的圖片路徑
screenshot_path = "current_game_area.png"   # 暫時截圖
url: str = "https://www.crazygames.com/game/collect-em-all"
start_point: Point                          # 第一顆球的座標
grid_spacing: Point                         # (0, 0)跟(1, 1)的間距

# 測試用途: 輸出矩陣
def output_matrix(matrix: list[list[Colors]]) -> None:
    """ 輸出顏色矩陣(測試用) """
    for row in matrix:
        for color in row:
            print(f"{color}\t", end="")
        print()

# 讀取指定一顆球的顏色
def get_box_color(image: Image.Image, box: Box) -> Colors:
    """ 取得該box的顏色 """
    center_x, center_y = pyautogui.center(box)
    color = image.getpixel((int(center_x), int(center_y)))
    if not (isinstance(color, tuple) and len(color) == 3):
        raise RuntimeError(f"invalid color: {color}")
    return Colors.to_color(color[:3])

# 從螢幕讀取矩陣
def read_matrix(image_path: str = screenshot_path) -> None:
    """尋找球並寫入矩陣"""
    global start_point, grid_spacing
    matrix.clear()
    all_locations: list[Box] = []
    locations: list[Box] = list(
        # 螢幕上尋找球
        pyautogui.locateAll(
            target_path, 
            image_path, 
            confidence=MIN_SIMILARITY, 
            grayscale=True
        )
    )
    
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
    
    # 記錄 start_point, grid_spacing
    all_locations.sort(key=lambda box : box.top)
    box00, box11 = all_locations[0], all_locations[7] # 在(0, 0)和(1, 1)的box
    start_point = Point(box00.left+box00.width/2, box00.top+box00.height/2)
    grid_spacing = Point(box11.left-box00.left, box11.top-box00.top)
    
    # 分成一個個row並加入matrix
    for i in range(0, 36, 6):
        # 分割成6行
        slice_ = all_locations[i:i+6]
        slice_.sort(key = lambda box : box.left)
        # 取得顏色
        row = [get_box_color(image, element) for element in slice_]
        # 加入matrix
        matrix.append(row)
        
# 座標轉換
def pixel_pos(grid: Point, topleft: Point, offset: Point) -> Point:
    """將矩陣的座標轉為像素座標"""
    rel_x = grid.x * offset.x
    rel_y = grid.y * offset.y
    abs_x = topleft.x + rel_x
    abs_y = topleft.y + rel_y
    return Point(abs_x, abs_y)

# 主程式函數
def main():
    """ 主程式 """
    global start_point, grid_spacing
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
    time.sleep(8)
    game_element.screenshot(path=screenshot_path)
    rect = game_element.bounding_box()
    if not rect: raise RuntimeError("找不到遊戲框架")
    print(f"成功鎖定遊戲區域")
    
    print("正在讀取各格的顏色")
    read_matrix(screenshot_path)
    output_matrix(matrix)
    
    pixel00 = pixel_pos(Point(0, 0), start_point, grid_spacing)
    pixel11 = pixel_pos(Point(1, 1), start_point, grid_spacing)
    print(f"矩陣 (0, 0) 的像素位置: {pixel00}")
    print(f"矩陣 (1, 1) 的像素位置: {pixel11}")
    
    print("正在關閉網頁...")
    browser.close()

# 執行main
if __name__ == "__main__": main()
