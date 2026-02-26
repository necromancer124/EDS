@echo off
title Bear Audio Limiter
:: 'py' is the standard launcher that usually works even if 'python' doesn't
py Main.py
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Python failed to start.
    echo Please make sure Python is installed and 'Add to PATH' was checked.
    pause
)
pause