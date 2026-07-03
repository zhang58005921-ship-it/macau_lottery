@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ============================================
echo   Building MacauLottery Desktop EXE
echo ============================================

pyinstaller --onefile --windowed ^
    --name "MacauLotteryV4PRO" ^
    --add-data "../shared;shared" ^
    --hidden-import shared.engine ^
    --hidden-import shared.macaujc_api ^
    --hidden-import tkinter ^
    --hidden-import tkinter.ttk ^
    --hidden-import tkinter.messagebox ^
    --hidden-import json ^
    --hidden-import ssl ^
    --hidden-import threading ^
    --hidden-import collections ^
    --hidden-import urllib.request ^
    --clean ^
    main.py

echo.
echo ============================================
echo   Build complete! Copying to desktop...
echo ============================================
copy /Y "dist\MacauLotteryV4PRO.exe" "%USERPROFILE%\Desktop\MacauLotteryV4PRO.exe"
echo Done!
pause
