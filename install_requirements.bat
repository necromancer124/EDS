@echo off
title 🐾 Bear Audio Limiter - Setup
echo ===========================================
echo   Installing Audio Dependencies...
echo ===========================================
echo.

:: Using 'py -m' bypasses the "pip not recognized" error
py -m pip install pycaw comtypes

echo.
echo ===========================================
echo   ✅ Installation Complete!
echo ===========================================
pause