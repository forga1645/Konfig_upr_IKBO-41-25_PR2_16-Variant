@echo off
setlocal

rem ============================================================
rem  run.bat — запуск визуализатора зависимостей (вариант №16)
rem  Использование:
rem      run.bat                (берёт config.toml по умолчанию)
rem      run.bat my_config.toml (указывает свой конфиг)
rem ============================================================

rem Переходим в папку, где лежит этот bat-файл (корень проекта)
cd /d "%~dp0"

rem PYTHONPATH указывает на папку src
set "PYTHONPATH=%~dp0src"

rem Конфиг: первый аргумент или config.toml
set "CONFIG=%~1"
if "%CONFIG%"=="" set "CONFIG=config.toml"

rem Проверка: есть ли файл конфигурации
if not exist "%CONFIG%" (
    echo [ОШИБКА] Файл конфигурации не найден: %CONFIG%
    exit /b 2
)

rem Проверка: есть ли python в PATH
where python >nul 2>nul
if errorlevel 1 (
    echo [ОШИБКА] Python не найден в PATH.
    echo Установите Python 3.10+ и добавьте его в PATH.
    exit /b 2
)

rem Запуск
python -m dependency_visualizer --config "%CONFIG%"
set "RC=%ERRORLEVEL%"

endlocal & exit /b %RC%