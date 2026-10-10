# JobFinder

JobFinder is a Windows desktop application for structured public-web job search. It uses a PySide6 interface and starts its local FastAPI search service automatically when the desktop application launches.

## Requirements

- Windows
- Python 3.13 or newer
- Internet access for live job searches

No API key, database, separate backend process, or LLM service is required.

## Create the `.venv`

Open PowerShell in the repository root (`JobFinder`) and run:

```powershell
py -3.13 -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If the Python Launcher is not installed, use `python -m venv .venv` instead of `py -3.13 -m venv .venv`.

For Command Prompt, activate the same environment with:

```cmd
.venv\Scripts\activate.bat
```

After activation, the terminal prompt normally starts with `(.venv)`. Keep the environment activated for the commands below. To leave it, run `deactivate`.

## Configure

The application works without a configuration file. To customize defaults, copy the example file:

```powershell
Copy-Item .env.example .env
```

Available settings in `.env` are:

```text
BACKEND_HOST=127.0.0.1
BACKEND_PORT=8765
SEARCH_REGION=us-en
SEARCH_BACKEND=auto
REQUEST_TIMEOUT_SECONDS=120
```

The backend uses `127.0.0.1:8765` by default. If that port is already in use, close the other process or change `BACKEND_PORT` in `.env`.

## Run the application

With `.venv` activated and the working directory set to the repository root:

```powershell
python run.py
```

This starts the desktop window and the local backend together. Live search uses public search services through `ddgs`; network or provider failures may reduce the results available.

To confirm that the local backend is running while the window is open, visit these URLs in a browser:

```text
http://127.0.0.1:8765/health
http://127.0.0.1:8765/api/status
```

Both endpoints should return JSON with `"ok": true`.

## Run tests (when the test suite is present)

Install the development dependencies into the active `.venv`:

```powershell
python -m pip install -r requirements-dev.txt
```

Run pytest from the repository root:

```powershell
python -m pytest
```

This checkout currently has no `tests` directory, so pytest reports `no tests ran`. If tests are added or restored, the same command runs them from the active `.venv`.

## Build a packaged application

Install the development dependencies first, then run the root build script from an activated `.venv`:

```powershell
python -m pip install -r requirements-dev.txt
.\build.bat
```

The PyInstaller output is created under `dist\JobFinder`. The script also creates `.env` from `.env.example` when `.env` does not exist.

Run the packaged application with:

```powershell
.\dist\JobFinder\JobFinder.exe
```

The PyInstaller build is an `onedir` distribution, so keep the complete `dist\JobFinder` directory when copying or distributing the application. If you need different backend settings, place a `.env` file in the working directory before launching it.

## Installation and distribution

This checkout currently contains no native installer project. To distribute the application, copy the complete `dist\JobFinder` directory and launch `JobFinder.exe` from that directory.

The end-to-end source workflow is therefore:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
python -m pytest
.\build.bat
.\dist\JobFinder\JobFinder.exe
```

The first two commands are only needed once per checkout. On later runs, activate `.venv`, rebuild if the source changed, and launch the executable or use `python run.py` for development.

## Project layout

```text
run.py                 Desktop entry point and embedded backend startup
app/                   Application code, services, models, exports, and UI
build.bat              PyInstaller build script
requirements.txt       Runtime dependencies
requirements-dev.txt   Runtime plus test and packaging dependencies
pyproject.toml         Project metadata and tool configuration
```

## Architecture

```text
PySide6 UI -> Local FastAPI service -> Search -> Filter/Validate/Deduplicate/Rank -> CSV or Excel
```

Search results are kept in memory; this version does not use an application database.

## Troubleshooting

### PowerShell will not activate `.venv`

Allow scripts for the current PowerShell process, then activate again:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

### Port `8765` is already in use

Close the other application using the port, or set a different value in `.env`:

```text
BACKEND_PORT=8766
```

### Search returns no live results

Confirm that the computer has Internet access and broaden the search filters. The application uses public web search providers and does not require an API key, but those providers can fail or limit requests.

### PyInstaller is not found

Activate `.venv` and install the development dependencies before running `build.bat`:

```powershell
python -m pip install -r requirements-dev.txt
```
