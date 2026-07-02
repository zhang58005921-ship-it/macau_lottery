@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo =====================================
echo   Building MacauLottery Desktop EXE
echo =========================================

pyinstaller --onefile --windowed ^
    --name "MacauLotteryV4PRO" ^
    --add-data "../shared/macaujc_data.json;shared" ^
    --add-data "../shared/engine.py;shared" \
    --add-data "../shared/macaujc_api.py;shared" \
    --hidden-import engine ^
    --hidden-import macaujc_api \
    --hidden-import tkinter \
    --hidden-import tkinter.ttk ^
    --hidden-import tkinter.messagebox \
    --hidden-import json \
    --hidden-import ssl ^
    --hidden-import threading ^
    --hidden-import collections ^
    --hidden-import urllib.request \
    --clean ^
    main.py

echo.
echo ========================================
echo   Build complete!
echo   Output: dist\MacauLotteryV4PRO.exe
echo =============================================
pause
