@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"

 echo ============================================================
 echo Video Audio Transcriber - Windows Installer
 echo ============================================================
 echo.

set "PYTHON_EXE="
set "PYTHON_ARGS="
set "PYTHON_SOURCE="

rem ------------------------------------------------------------
rem 1. Try commands that are normally available on PATH.
rem The validation expression deliberately avoids < and > because
rem those characters can be misparsed by cmd.exe in batch files.
rem ------------------------------------------------------------
call :try_python python "PATH command: python"
if defined PYTHON_EXE goto :python_found

call :try_python python3 "PATH command: python3"
if defined PYTHON_EXE goto :python_found

rem ------------------------------------------------------------
rem 2. Try all Python installations registered with py.exe.
rem ------------------------------------------------------------
call :try_python py -3.13 "Python Launcher: 3.13"
if defined PYTHON_EXE goto :python_found
call :try_python py -3.12 "Python Launcher: 3.12"
if defined PYTHON_EXE goto :python_found
call :try_python py -3.11 "Python Launcher: 3.11"
if defined PYTHON_EXE goto :python_found
call :try_python py -3.10 "Python Launcher: 3.10"
if defined PYTHON_EXE goto :python_found

rem ------------------------------------------------------------
rem 3. Try common per-user and system installation locations.
rem ------------------------------------------------------------
call :try_python "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" "Local Python 3.13"
if defined PYTHON_EXE goto :python_found
call :try_python "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" "Local Python 3.12"
if defined PYTHON_EXE goto :python_found
call :try_python "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" "Local Python 3.11"
if defined PYTHON_EXE goto :python_found
call :try_python "%LOCALAPPDATA%\Programs\Python\Python310\python.exe" "Local Python 3.10"
if defined PYTHON_EXE goto :python_found

call :try_python "%ProgramFiles%\Python313\python.exe" "System Python 3.13"
if defined PYTHON_EXE goto :python_found
call :try_python "%ProgramFiles%\Python312\python.exe" "System Python 3.12"
if defined PYTHON_EXE goto :python_found
call :try_python "%ProgramFiles%\Python311\python.exe" "System Python 3.11"
if defined PYTHON_EXE goto :python_found
call :try_python "%ProgramFiles%\Python310\python.exe" "System Python 3.10"
if defined PYTHON_EXE goto :python_found

rem ------------------------------------------------------------
rem 4. Try popular Python managers.
rem ------------------------------------------------------------
call :try_python "%USERPROFILE%\scoop\apps\python\current\python.exe" "Scoop Python"
if defined PYTHON_EXE goto :python_found
call :try_python "%USERPROFILE%\scoop\shims\python.exe" "Scoop Python shim"
if defined PYTHON_EXE goto :python_found
call :try_python "%USERPROFILE%\.pyenv\pyenv-win\shims\python.bat" "pyenv-win Python"
if defined PYTHON_EXE goto :python_found

rem ------------------------------------------------------------
rem 5. Inspect every python.exe returned by where.exe.
rem ------------------------------------------------------------
for /f "usebackq delims=" %%P in (`where.exe python.exe 2^>nul`) do call :try_python "%%P" "where.exe result"
if defined PYTHON_EXE goto :python_found

for /f "usebackq delims=" %%P in (`where.exe python3.exe 2^>nul`) do call :try_python "%%P" "where.exe result"
if defined PYTHON_EXE goto :python_found

goto :no_python

:python_found
echo.
echo Python interpreter selected:
echo     %PYTHON_SOURCE%
"%PYTHON_EXE%" %PYTHON_ARGS% -c "import struct,sys; print('Executable:',sys.executable); print('Version:',sys.version.split()[0]); print('Architecture:',struct.calcsize('P')*8,'bit')"
if errorlevel 1 goto :no_python

echo.
echo Checking Tkinter...
"%PYTHON_EXE%" %PYTHON_ARGS% -c "import tkinter; print('Tkinter: OK, Tcl/Tk', tkinter.TclVersion)"
if errorlevel 1 (
    echo.
    echo Tkinter is missing from this Python installation.
    echo Modify or reinstall Python and enable Tcl/Tk and IDLE.
    pause
    exit /b 1
)

echo.
echo Checking FFmpeg and ffprobe...
where.exe ffmpeg.exe >nul 2>nul
if errorlevel 1 (
    echo FFmpeg was not found in the PATH visible to this installer.
    echo.
    echo Run this installer from the same terminal where this works:
    echo     ffmpeg -version
    echo.
    echo Example:
    echo     cd /d "%~dp0"
    echo     install_windows.bat
    pause
    exit /b 1
)

where.exe ffprobe.exe >nul 2>nul
if errorlevel 1 (
    echo ffprobe was not found in the PATH visible to this installer.
    echo Run this installer from the same terminal where ffprobe works.
    pause
    exit /b 1
)

ffmpeg -version >nul 2>nul
if errorlevel 1 (
    echo FFmpeg was found but could not be executed.
    pause
    exit /b 1
)

ffprobe -version >nul 2>nul
if errorlevel 1 (
    echo ffprobe was found but could not be executed.
    pause
    exit /b 1
)

echo FFmpeg and ffprobe: OK

rem Remove an incomplete virtual environment from a failed installation.
if exist ".venv" if not exist ".venv\Scripts\python.exe" (
    echo.
    echo Removing incomplete virtual environment...
    rmdir /s /q ".venv"
)

rem Rebuild an environment created with an unsupported Python version or bitness.
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -c "import struct,sys; ok=sys.version_info[:2] in ((3,10),(3,11),(3,12),(3,13)) and struct.calcsize('P')==8; raise SystemExit(0 if ok else 1)" >nul 2>nul
    if errorlevel 1 (
        echo.
        echo Removing incompatible virtual environment...
        rmdir /s /q ".venv"
    )
)

if not exist ".venv\Scripts\python.exe" (
    echo.
    echo Creating virtual environment...
    "%PYTHON_EXE%" %PYTHON_ARGS% -m venv ".venv"
    if errorlevel 1 (
        echo.
        echo Could not create the virtual environment.
        echo Run this command manually to display the full Python error:
        echo     "%PYTHON_EXE%" %PYTHON_ARGS% -m venv ".venv"
        pause
        exit /b 1
    )
) else (
    echo.
    echo Existing compatible virtual environment will be reused.
)

echo.
echo Updating pip, setuptools, and wheel...
".venv\Scripts\python.exe" -m pip install --upgrade pip setuptools wheel
if errorlevel 1 goto :install_error

echo.
echo Installing application dependencies...
".venv\Scripts\python.exe" -m pip install --upgrade --prefer-binary -r requirements.txt
if errorlevel 1 goto :install_error

echo.
echo Verifying the installation...
".venv\Scripts\python.exe" -c "from importlib.metadata import version; import tkinter, faster_whisper, ctranslate2; print('faster-whisper:',version('faster-whisper')); print('CTranslate2:',version('ctranslate2')); print('Installation verification: OK')"
if errorlevel 1 goto :install_error

echo.
echo Running included tests...
".venv\Scripts\python.exe" -m unittest test_text_cleanup.py
if errorlevel 1 goto :install_error

echo.
echo ============================================================
echo Installation completed successfully.
echo Double-click run_windows.bat to open the application.
echo ============================================================
pause
exit /b 0

:try_python
if defined PYTHON_EXE exit /b 0
set "CANDIDATE_LABEL=%~2"

rem The candidate command is passed as the first argument in normal cases.
rem py.exe requires a version argument, so handle those calls separately.
if /i "%~1"=="py" goto :try_py_launcher

if not exist "%~1" (
    where.exe "%~1" >nul 2>nul
    if errorlevel 1 exit /b 0
)

"%~1" -c "import struct,sys; ok=sys.version_info[:2] in ((3,10),(3,11),(3,12),(3,13)) and struct.calcsize('P')==8; raise SystemExit(0 if ok else 1)" >nul 2>nul
if errorlevel 1 exit /b 0

set "PYTHON_EXE=%~1"
set "PYTHON_ARGS="
set "PYTHON_SOURCE=%CANDIDATE_LABEL%"
exit /b 0

:try_py_launcher
set "PY_VERSION_ARG=%~2"
set "CANDIDATE_LABEL=%~3"
where.exe py.exe >nul 2>nul
if errorlevel 1 exit /b 0

py %PY_VERSION_ARG% -c "import struct,sys; ok=sys.version_info[:2] in ((3,10),(3,11),(3,12),(3,13)) and struct.calcsize('P')==8; raise SystemExit(0 if ok else 1)" >nul 2>nul
if errorlevel 1 exit /b 0

set "PYTHON_EXE=py"
set "PYTHON_ARGS=%PY_VERSION_ARG%"
set "PYTHON_SOURCE=%CANDIDATE_LABEL%"
exit /b 0

:no_python
echo.
echo No supported 64-bit Python installation was found by cmd.exe.
echo.
echo Your terminal may have a different PATH from Windows Explorer.
echo Open the terminal where this command works:
echo     python --version
echo.
echo Then run:
echo     cd /d "%~dp0"
echo     install_windows.bat
echo.
echo Supported versions: 64-bit Python 3.10, 3.11, 3.12, or 3.13.
pause
exit /b 1

:install_error
echo.
echo ============================================================
echo Installation failed while installing or verifying packages.
echo Review the complete error shown above.
echo ============================================================
echo.
echo To retry from a clean environment:
echo     rmdir /s /q ".venv"
echo     install_windows.bat
pause
exit /b 1
