@echo off
setlocal
REM Always run from the script's directory
cd /d "%~dp0"

set "VENV_DIR=.seoaudmach"

REM Does the venv already exist?
if exist "%VENV_DIR%\Scripts\python.exe" (
  echo ✅ Virtual environment already exists: %VENV_DIR%
) else (
  echo 🔧 Creating virtual environment in "%VENV_DIR%"...
  REM Prefer the Python launcher, fall back to python
  where py >nul 2>nul
  if %errorlevel%==0 (
    py -3 -m venv "%VENV_DIR%" || (echo ❌ Failed to create venv.& exit /b 1)
  ) else (
    where python >nul 2>nul || (echo ❌ Python not found. Install Python 3.10+ and add to PATH.& exit /b 1)
    python -m venv "%VENV_DIR%" || (echo ❌ Failed to create venv.& exit /b 1)
  )
)

echo 📦 Installing requirements with venv pip...
"%VENV_DIR%\Scripts\python.exe" -m pip install --upgrade pip wheel
"%VENV_DIR%\Scripts\python.exe" -m pip install -U -r requirements.txt || (echo ❌ pip install failed.& exit /b 1)

echo.
echo 🎉 Done.
echo 👉 To activate later in this shell: call "%VENV_DIR%\Scripts\activate"
endlocal
