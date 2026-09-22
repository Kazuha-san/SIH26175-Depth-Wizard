@echo off
setlocal
cd /d "%~dp0"

echo ===============================================
echo  DepthWizard launcher
echo ===============================================
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo ERROR: Python was not found on PATH.
    echo Install Python 3.10+ from python.org first ^(check "Add to PATH" during install^), then re-run this.
    pause
    exit /b 1
)

if not exist "backend\.venv" (
    echo [1/4] Creating Python virtual environment ^(first run only^)...
    python -m venv backend\.venv
)

call backend\.venv\Scripts\activate.bat

echo [2/4] Checking backend dependencies...
pip install -q -r backend\requirements.txt

if not exist "backend\checkpoints\depth_anything_v2_gamus_v4.pth" (
    echo.
    echo ERROR: Missing backend\checkpoints\depth_anything_v2_gamus_v4.pth
    echo These model checkpoints are too large for GitHub and must be added manually.
    echo See README.md for where to get them.
    echo.
    pause
    exit /b 1
)
if not exist "backend\checkpoints\landcover_seg_v6.pth" (
    echo.
    echo ERROR: Missing backend\checkpoints\landcover_seg_v6.pth
    echo These model checkpoints are too large for GitHub and must be added manually.
    echo See README.md for where to get them.
    echo.
    pause
    exit /b 1
)

if not exist "frontend\dist" (
    echo [3/4] Building frontend ^(first run only, can take a minute^)...
    where npm >nul 2>nul
    if errorlevel 1 (
        echo ERROR: Node.js/npm was not found on PATH.
        echo Install it from nodejs.org first, then re-run this.
        pause
        exit /b 1
    )
    pushd frontend
    if not exist "node_modules" (
        call npm install
    )
    call npm run build
    popd
)

echo [4/4] Starting DepthWizard...
echo ^(Keep this window open -- it shows backend logs. Close the app window or Ctrl+C here to stop.^)
echo.
cd backend
python desktop_app.py

echo.
echo DepthWizard closed.
pause
