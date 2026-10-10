@echo off
setlocal
python -m pip install -r requirements.txt
if errorlevel 1 exit /b %errorlevel%
if not exist .env copy .env.example .env
python -m PyInstaller --noconfirm --clean --onedir --windowed --name JobFinder ^
  --collect-submodules uvicorn --collect-submodules ddgs ^
  --hidden-import pydantic_settings --add-data ".env.example;." run.py
if errorlevel 1 exit /b %errorlevel%
endlocal
