from random import randint
from copy import deepcopy
import pyautogui
from webbrowser import open_new
from time import sleep

pyautogui.PAUSE=0
color=((255, 0, 29), (77, 186, 48), (82, 130, 246), (249, 140, 41), (150, 43, 235))

grid=[[randint(0, 4) for _ in range(6)] for __ in range(6)]
used=[[False]*6 for _ in range(6)]

#跟螢幕上位置有關的變數
TopLeft=(724, 370) #左上方的位置
GridSize=63 #每格距離
stopImage="stop.png" #判斷遊戲結束的圖片

#以下為之前寫好的函式
def detect(r, c): #偵測圈圈顏色
    try:
        return color.index(scr.getpixel(((c)*GridSize, (r)*GridSize)))
    except:
        print("cant find color")
        sleep(0.1)
        return -1
    
def followPath(path): #滑鼠輸入寫這，path是存放連線位置的list
    print(path)

    for pos in path:
        pyautogui.moveTo(TopLeft[0]+(pos[1])*GridSize, TopLeft[1]+(pos[0])*GridSize, 0.15)
        pyautogui.mouseDown()
    pyautogui.move(1, 0, 0.15) #錄的時候需要再尾端動一下才偵測得到
    sleep(0.1)
    pyautogui.mouseUp()

    sleep(1)
    return

#新寫的程式
def findPath(row, column, color, path=None): #尋找這個點能找到的最長連線
    global used

    allDir=((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1))

    if(path is None): path=[]
    path.append((row, column))
    used[row][column]=True
    allPath=[deepcopy(path)]

    valid=lambda r, c: 0<=r<6 and 0<=c<6 and (not used[r][c]) and grid[r][c]==color


    for rd, cd in allDir:
        if not valid(row+rd, column+cd): continue
        
        allPath.append(findPath(row+rd, column+cd, color, path))
        
        used[row+rd][column+cd]=False
        path.pop()

    idx=0
    for i in range(len(allPath)):
        if(len(allPath[i])>len(allPath[idx])):
            idx=i
    
    return allPath[idx]
        
def finalLine(): #每個點的最長連線中取最長的
    best=[]
    for i in range(6):
        for j in range(6):
            if(used[i][j]): continue

            cur=findPath(i, j, grid[i][j])
            used[i][j]=False
            cur=findPath(cur[-1][0], cur[-1][1], grid[cur[-1][0]][cur[-1][1]])
            for r, c in cur: used[r][c]=True

            if(len(cur)>len(best)): best=deepcopy(cur)
    return best

def printGrid(): #輸出表格，測試用
    for i in range(6):
        for j in range(6):
            print(grid[i][j], end=" ")
        print()
    return

def scannGrid():
    for i in range(6):
            for j in range(6):
                grid[i][j]=detect(i, j)
                if(grid[i][j]==-1): return False
    return True

print("starting")
open_new("https://www.crazygames.com/game/collect-em-all")
sleep(3)
pyautogui.click(877, 605)
sleep(6)


while(True):
    try:
        pyautogui.locateOnScreen(stopImage, region=(724, 370, 63*6, 63*6))
        break
    except:
        scr=pyautogui.screenshot(region=(TopLeft[0], TopLeft[1], GridSize*7, GridSize*7))
        print("scanning")
        while(not scannGrid()):
            sleep(0.1)
            scr=pyautogui.screenshot(region=(TopLeft[0], TopLeft[1], GridSize*7, GridSize*7))
        used=[[False]*6 for _ in range(6)]
        printGrid()
        print("finding")
        followPath(finalLine())
print("end")