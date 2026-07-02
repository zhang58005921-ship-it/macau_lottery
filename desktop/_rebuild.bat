@echo off
cd /d "C:\Users\PENGYI\Documents\学习codex\macau_lottery"
echo Building...
pyinstaller --onefile --windowed --name macau_lottery --add-data "macaujc_data.json;." --add-data "firecrawl_bridge.py;." --hidden-import firecrawl_bridge --hidden-import tkinter --hidden-import tkinter.ttk --clean main.py
copy /Y "dist\macau_lottery.exe" "%USERPROFILE%\Desktop\数字预测游戏.exe"
start "" "%USERPROFILE%\Desktop\数字预测游戏.exe"
echo Done