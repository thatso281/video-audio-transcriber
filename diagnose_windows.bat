@echo off
setlocal
cd /d "%~dp0"
echo ============================================================
echo Windows Python and FFmpeg diagnostics
echo ============================================================
echo.
echo Current directory:
echo %CD%
echo.
echo PATH entries containing Python or FFmpeg commands:
echo.
where.exe python 2>&1
where.exe python3 2>&1
where.exe py 2>&1
where.exe ffmpeg 2>&1
where.exe ffprobe 2>&1
echo.
echo Direct command tests:
echo.
python --version 2>&1
python -c "import struct,sys; print(sys.executable); print(sys.version); print(struct.calcsize('P')*8)" 2>&1
py -0p 2>&1
ffmpeg -version 2>&1 | findstr /b /c:"ffmpeg version"
ffprobe -version 2>&1 | findstr /b /c:"ffprobe version"
echo.
pause
