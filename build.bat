@echo off
setlocal enabledelayedexpansion

:: =============================================================
:: Zoltek NozzleScanner — Automated Build Script
:: =============================================================

set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"

set "BACKEND=%ROOT%\PythonBackend"
set "FRONTEND=%ROOT%\Angular"
set "ELECTRON=%ROOT%\Electron_Config"
set "RELEASE=%ELECTRON%\release"

echo.
echo ============================================================
echo  Verifying Paths...
echo ============================================================
if not exist "%ELECTRON%\package.json" (
    echo ERROR: Could not find package.json in %ELECTRON%
    pause & exit /b 1
)
echo  Electron Folder: OK
echo ============================================================
echo.

set "INSTALL_DEPS=N"
set /p "INSTALL_DEPS=Install/update dependencies? (pip, npm) [y/N]: "
if /i "!INSTALL_DEPS!"=="" set "INSTALL_DEPS=N"

:: --- Step 1: Python ---
echo [1/5] Building Python backend ...
pushd "%BACKEND%"
if /i "!INSTALL_DEPS!"=="y" ( pip install pyinstaller -r requirements.txt )
python -m PyInstaller GUI_backend.py --noconsole --hidden-import pyodbc --hidden-import tkinter --hidden-import matplotlib --add-data "error_messages.json;."
if !errorlevel! neq 0 ( popd & exit /b 1 )
popd

:: --- Step 2: Angular ---
echo [2/5] Building Angular frontend ...
pushd "%FRONTEND%"
if /i "!INSTALL_DEPS!"=="y" ( call npm install )
call npx ng build --configuration production
if !errorlevel! neq 0 ( popd & exit /b 1 )
popd

:: --- Step 3: Copy Frontend ---
echo [3/5] Copying frontend to Electron ...
if exist "%ELECTRON%\app" rmdir /s /q "%ELECTRON%\app"
mkdir "%ELECTRON%\app"
xcopy "%FRONTEND%\dist\zoltek\browser\*" "%ELECTRON%\app\" /s /e /q /y

:: --- Step 4: Build Electron (With Safety Check) ---
echo [4/5] Building Electron application ...
pushd "%ELECTRON%"

:: Logic from Source: Auto-install if node_modules is missing
if /i "!INSTALL_DEPS!"=="y" (
    call npm install
) else if not exist "node_modules" (
    echo node_modules missing in Electron_Config - running npm install...
    call npm install
)

if exist "%RELEASE%" rmdir /s /q "%RELEASE%"
call npx electron-builder --win
if !errorlevel! neq 0 ( popd & exit /b 1 )
popd

:: --- Step 5: Final Packaging ---
echo [5/5] Finalizing package resources ...
set "RES_DIR=%RELEASE%\win-unpacked\resources"
xcopy "%BACKEND%\dist\GUI_backend\*" "%RES_DIR%\" /s /e /q /y
if exist "%BACKEND%\Templates" (
    mkdir "%RES_DIR%\_internal" 2>nul
    xcopy "%BACKEND%\Templates\*" "%RES_DIR%\_internal\Templates\" /s /e /q /y [cite: 22]
)
if exist "%BACKEND%\settings.json" (
    copy /y "%BACKEND%\settings.json" "%RES_DIR%\settings.json" >nul [cite: 22]
)

echo ============================================================
echo  BUILD COMPLETE
echo ============================================================
pause