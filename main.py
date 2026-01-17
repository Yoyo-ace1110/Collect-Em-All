from __future__ import annotations
from enum import Enum
from pyscreeze import Box
from PIL import Image
from typing import Any
from keyboard import is_pressed
from playwright.sync_api import sync_playwright, Playwright, Page
import pyautogui, time

class Colors(Enum):
    # 各種顏色(RGB)
    Red = (255, 0, 29)
    Green = (77, 186, 48)
    Blue = (82, 130, 246)
    Orange = (249, 140, 41)
    Purple = (150, 43, 235)
    
    @property
    def r(self): return self.value[0]
    @property
    def g(self): return self.value[1]
    @property
    def b(self): return self.value[2]
    
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
    
    def near(self, other: Point) -> bool:
        """ 檢查兩個點之間是否可以互通 """
        if abs(other.x-self.x) > 1: return False
        if abs(other.y-self.y) > 1: return False
        return True
    
    @property
    def pair(self) -> tuple[int, int]:
        ''' 取得tuple(x, y) '''
        return (self.x, self.y)

    # --- 正向運算 (Binary Operators) ---
    def __add__(self, other: Point|tuple|int|float) -> Point:
        """ 加法: self + other """
        x, y = self._unpack(other)
        return Point(self.x + x, self.y + y)

    def __sub__(self, other: Point|tuple|int|float) -> Point:
        """ 減法: self - other """
        x, y = self._unpack(other)
        return Point(self.x - x, self.y - y)

    # --- 反向運算 (Reflected Operators) ---
    def __radd__(self, other: Point|tuple|int|float) -> Point:
        return self.__add__(other)

    def __rsub__(self, other: Point|tuple|int|float) -> Point:
        x, y = self._unpack(other)
        return Point(x - self.x, y - self.y)

    # --- 就地運算 (Inplace Operators) ---
    def __iadd__(self, other: Point|tuple|int|float) -> Point:
        """ 就地加法: self += other """
        x, y = self._unpack(other)
        self.x += int(x)
        self.y += int(y)
        return self

    def __isub__(self, other: Point|tuple|int|float) -> Point:
        """ 就地減法: self -= other """
        x, y = self._unpack(other)
        self.x -= int(x)
        self.y -= int(y)
        return self

    # 輔助函數: 解析各種輸入格式
    def _unpack(self, other) -> tuple[int|float, int|float]:
        if isinstance(other, Point):
            return other.x, other.y
        elif isinstance(other, (tuple, list)) and len(other) >= 2:
            return other[0], other[1]
        elif isinstance(other, (int, float)):
            return other, other
        return 0, 0

    def __str__(self) -> str:
        return f"Point({self.x}, {self.y})"

    def __repr__(self) -> str:
        return self.__str__()

color_matrix: list[list[Colors]] = []       # 顏色矩陣
point_matrix: list[list[Point]] = []        # 座標矩陣
MIN_SIMILARITY: float = 0.83                # 圖片最低相似度
target_path: str = "./target.png"           # 球的圖片路徑
screenshot_path = "current_game_area.png"   # 暫時截圖
url: str = "https://www.crazygames.com/game/collect-em-all"
iframe_topleft: Point                       # 第一顆球的座標
dpr: float # 縮放比例

# 測試用途: 輸出矩陣
def output_matrix(matrix: list[list[Any]]) -> None:
    """ 輸出顏色矩陣(測試用) """
    for row in matrix:
        for element in row:
            print(f"{element}\t", end="")
        print()

# 取得中心座標
def get_box_center(box: Box) -> Point:
    """ 取得box的中心座標 """
    return Point(box.left+box.width/2, box.top+box.height/2)

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
    color_matrix.clear()
    point_matrix.clear()
    all_locations: list[Box] = []
    
    # 螢幕上尋找球
    locations: list[Box] = list(
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
            # 如果距離小於 n 像素 視為同一顆球
            if dist < 10:
                is_duplicate = True
                break
        if not is_duplicate:
            all_locations.append(box)
    print(f"DEBUG: 原始找到 {len(locations)} 個點 去重後剩餘 {len(all_locations)} 顆球")
    if len(all_locations) != 36: raise RuntimeError("找不到6*6=36顆球")
    
    # 分成一個個 row 並加入 color_matrix && point_matrix
    all_locations.sort(key=lambda box : box.top)
    for i in range(0, 36, 6):
        slice_ = all_locations[i:i+6]                             # 分割成6行
        slice_.sort(key=lambda box: box.left)                     # 橫向排序
        color_row = [get_box_color(image, box) for box in slice_] # 取得顏色
        point_row = [get_box_center(box) for box in slice_]       # 取得座標
        color_matrix.append(color_row)                            # 加入color_matrix
        point_matrix.append(point_row)                            # 加入point_matrix
    
# 座標轉換
def pixel_pos(grid: Point) -> Point:
    """將矩陣的座標轉為像素座標"""
    pos = point_matrix[grid.y][grid.x]
    return iframe_topleft + Point(pos.x/dpr, pos.y/dpr)

# 拖曳連線
def drag_path(page: Page, points: list[Point]):
    """ 在points中一個個拖曳並連線 """
    last_point = pixel_pos(points[-1])
    # 找到第一個點並按下
    first_point = pixel_pos(points[0])
    page.mouse.move(*first_point.pair)
    page.mouse.down()
    # print(f"DEBUG: 在 {first_point} 按下滑鼠")
    # 迴圈拖曳(跳過第一個)
    for point in points[1:]:
        # 拖曳 (step是移動平滑度 可以調整)
        pixel = pixel_pos(point)
        page.mouse.move(*pixel.pair, steps=4)
        # print(f"DEBUG: 移動滑鼠至 {pixel}")
        time.sleep(0.2)
    # 鬆開滑鼠
    page.mouse.up()
    # print(f"DEBUG: 在 {last_point} 鬆開滑鼠")

# 尋找周圍同色鄰居
def get_neighbors(point: Point, color_matrix: list[list[Colors]]) -> list[Point]:
    """ 取得周圍同色球的座標 """
    neighbors: list[Point] = []
    point_color = color_matrix[point.y][point.x]
    # 八方位找
    for offset_x in [-1, 0, 1]:
        for offset_y in [-1, 0, 1]:
            # 記錄座標
            detect_point = point+Point(offset_x, offset_y)
            x, y = detect_point.x, detect_point.y
            # 跳過自己 && 邊界檢查
            if (offset_x == 0 and offset_y == 0): continue
            if (x < 0 or y < 0 or x > 5 or y > 5): continue
            # 比較顏色
            if color_matrix[y][x] == point_color:
                neighbors.append(detect_point)
    return neighbors

# 初判最長長度
def len_all_neighbors(point: Point) -> int:
    """ 使用 BFS 算出該區域總球數上限 """
    visited = [[False for _ in range(6)] for _ in range(6)]
    queue = [point]
    visited[point.y][point.x] = True
    count = 0
    
    while queue:
        curr = queue.pop(0)
        count += 1
        for n in get_neighbors(curr, color_matrix):
            if not visited[n.y][n.x]:
                visited[n.y][n.x] = True # 加入隊列前就標記，避免重複排隊
                queue.append(n)
    return count

# 尋找最長連線
def find_longest_move(color_matrix: list[list[Colors]]) -> list[Point]:
    """ 由左上開始DFS 尋找過的點就消除 分岔就兩個都跑一遍 """
    visited: list[list[bool]] = [[False for _ in range(6)] for __ in range(6)]
    best_path: list[Point] = []
    best_len = 0
    row, column = 0, 0
    # 開始訪問
    while (row <= 5 and column <= 5):
        # 剪枝: 去除周圍加總根本不會超過的問題
        max_len = len_all_neighbors(Point(column, row))
        skip = max_len <= best_len
        # 略過已訪問的點
        skip = skip or visited[row][column]
        # 下一個點
        if skip: 
            row += (column+1)//6
            column = (column+1)%6
            continue
        # DFS 並更新最佳路線
        visits = DFS(Point(column, row), color_matrix, max_len=max_len)
        visit_len = len(visits)
        if visit_len >= 3 and visit_len > best_len:
            best_path = visits
            best_len = visit_len
        # 標記尋訪過的點
        for visit in visits: visited[visit.y][visit.x] = True
        # 下一個點
        row += (column+1)//6
        column = (column+1)%6
    return best_path

# 核心演算法: DFS
def DFS(point: Point, color_matrix: list[list[Colors]], 
        current_path: list[Point]|None = None, max_len: int = 36) -> list[Point]:
    """ 
    深度優先搜尋：利用回溯尋找該區域內最長的路徑。
    current_path 用於記錄目前已經走過的點，避免循環連線。
    """
    if current_path is None: current_path = [point]
    if len(current_path) == max_len: return list(current_path)
    best_sub_path = list(current_path)
    neighbors = get_neighbors(point, color_matrix) # 取得周圍同色鄰居

    for neighbor in neighbors:
        # 檢查這個鄰居是否已經在目前的路徑中
        if any(p.x == neighbor.x and p.y == neighbor.y for p in current_path):
            continue 
        # 前進: 加入路徑並繼續向下探索
        current_path.append(neighbor)
        res_path = DFS(neighbor, color_matrix, current_path, max_len)
        # 比較: 如果這條分岔走出來的路比較長，就更新它
        if len(res_path) > len(best_sub_path):
            best_sub_path = list(res_path)
        # 回溯: 將點移除，讓下一個鄰居的分岔可以重新嘗試走這條路
        current_path.pop()
    return best_sub_path

# 主程式函數
def main():
    """ 主程式 """
    global iframe_topleft, dpr
    sync: Playwright = sync_playwright().__enter__()
    browser = sync.chromium.launch(headless=False, args=["--start-maximized"])
    context = browser.new_context(no_viewport=True)
    page = context.new_page()
    
    print("正在開啟網頁...")
    page.goto("https://www.crazygames.com/game/collect-em-all")
    page.wait_for_selector("#game-iframe")
    page.wait_for_load_state("domcontentloaded")
    
    print("正在辨識遊戲框架...")
    game_element = page.locator("#game-iframe")
    game_element.scroll_into_view_if_needed()
    time.sleep(4)           # 等遊戲載入 可調
    game_element.click()    # 聚焦
    rect = game_element.bounding_box()
    if not rect: raise RuntimeError("找不到遊戲框架")
    iframe_topleft = Point(rect['x'], rect['y'])
    print(f"成功鎖定遊戲區域")
    
    dpr = page.evaluate("window.devicePixelRatio")
    print(f"DEBUG: 偵測到螢幕縮放倍率為: {dpr}")
    
    print("正在遊玩...")
    while True:
        # Esc 可以退出
        if is_pressed("esc"): break
        
        print("\t正在讀取各格的顏色...")
        game_element.screenshot(path=screenshot_path)
        read_matrix(screenshot_path)
        # output_matrix(color_matrix)
        
        print("\t連線中...")
        longest_move = find_longest_move(color_matrix)
        drag_path(page=page, points=longest_move)
        
        print("等待球被消除")
        move_len = len(longest_move)
        # 依據連線步長決定等待時間
        if move_len <= 6: time.sleep(2.5)
        elif move_len <= 9: time.sleep(4)
        else: time.sleep(8)
    
    # print(f"iframe_topleft: {iframe_topleft}")
    # print(f"pixel_pos(Point(0, 0)): {pixel_pos(Point(0, 0))}")
    
    print("正在關閉網頁...")
    browser.close()
    print("程式執行完畢")

# 執行 main()
if __name__ == "__main__": main()
