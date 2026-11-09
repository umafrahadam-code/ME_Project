@echo off
REM ======================================================================
REM  Plant Disease Detection - one command setup and start.
REM   1. Finds Python 3.10-3.12; if missing, installs Python 3.12 with winget
REM   2. Creates a virtual environment in %USERPROFILE%\.plantapp_venv (a short
REM      path, so PyTorch's long file names fit) and installs the packages
REM   3. Starts the web app and opens http://127.0.0.1:5000
REM  First run needs internet (about 250 MB). Later runs start at once.
REM ======================================================================
setlocal
cd /d "%~dp0"
set "VENV=%USERPROFILE%\.plantapp_venv"
title Plant Disease Detection

if exist "%VENV%\Scripts\python.exe" goto :start

echo [1/3] Looking for Python 3.10 - 3.12 ...
set "PY="
call :try python
if not defined PY call :try py -3.12
if not defined PY call :try py -3.11
if not defined PY call :try py -3.10
if not defined PY call :try "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if defined PY goto :venv

echo       Python not found. Installing Python 3.12 with winget ...
where winget >nul 2>nul || goto :nopython
winget install -e --id Python.Python.3.12 --scope user --accept-package-agreements --accept-source-agreements
call :try "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if not defined PY goto :nopython

:venv
echo       Using %PY%
echo [2/3] Creating virtual environment and installing packages (first time: 5-10 min) ...
%PY% -m venv "%VENV%" || goto :fail
"%VENV%\Scripts\python.exe" -m pip install --upgrade pip
"%VENV%\Scripts\python.exe" -m pip install -r requirements.txt || goto :fail

:start
echo [3/3] Starting the app ...
echo.
echo   Open http://127.0.0.1:5000 in your browser.
echo   Press Ctrl+C in this window to stop the app.
echo.
if not defined NO_BROWSER start "" /b cmd /c "timeout /t 10 >nul & start "" http://127.0.0.1:5000"
"%VENV%\Scripts\python.exe" app.py
pause
exit /b 0

REM ---- sets PY if the given command is Python 3.10 - 3.12 (64-bit) -------
:try
%* -c "import sys,struct;sys.exit(0 if (3,10)<=sys.version_info[:2]<=(3,12) and struct.calcsize('P')==8 else 1)" >nul 2>nul
if not errorlevel 1 set PY=%*
exit /b 0

:nopython
echo.
echo Python could not be installed automatically.
echo Install 64-bit Python 3.12 from https://www.python.org/downloads/
echo (tick "Add python.exe to PATH"), then run this file again.
pause
exit /b 1

:fail
echo.
echo Setup failed. Check the internet connection, and run this file again.
if exist "%VENV%" rmdir /s /q "%VENV%"
pause
exit /b 1
