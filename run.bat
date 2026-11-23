@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
set "PYTHONPATH=%CD%\src"

set "CONFIG_FILE=config.test.toml"

echo Запуск с конфигурацией: %CONFIG_FILE%
echo (Если используется сетевой режим, загрузка пакетов с NuGet может занять до 1 минуты...)
echo.

py -3 -u -m dependency_visualizer --config "%CONFIG_FILE%" %*

echo.
if errorlevel 1 (
    echo Программа завершилась с ошибкой.
) else (
    echo Готово!
)
pause
endlocal