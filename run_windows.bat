@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Virtual environment not found.
    echo Run install_windows.bat first.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" app.py

if errorlevel 1 (
    echo.
    echo The application stopped with an error.
    pause
)
