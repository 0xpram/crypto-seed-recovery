@echo off
echo Building Crypto Seed Recovery Tool...
pyinstaller --onefile --windowed --name "Crypto Seed Recovery" --icon=NONE seed_recovery.py
echo.
echo Build complete! Check the 'dist' folder for the executable!
pause
