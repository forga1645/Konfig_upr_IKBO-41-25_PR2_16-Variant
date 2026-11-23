@echo off
setlocal
cd /d "%~dp0"
set PYTHONPATH=%CD%\src

where py >nul 2>nul
if %errorlevel%==0 (
    py -3.11 -c "import sys" >nul 2>nul
    if %errorlevel%==0 (
        py -3.11 -m dependency_visualizer --config config.toml
        goto :finish
    )
)

python -c "import sys" >nul 2>nul
if %errorlevel% neq 0 (
    echo Python 3.11 or newer was not found.
    echo Install Python and enable "Add Python to PATH".
    pause
    exit /b 1
)

set PYTHONPATH=%CD%\src
python -m dependency_visualizer --config config.toml

:finish
if %errorlevel% neq 0 (
    echo.
    echo Application finished with an error.
)
pause
endlocal
