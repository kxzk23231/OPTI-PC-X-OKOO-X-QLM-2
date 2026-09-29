@echo off
REM Nécessite Python 3.9+ (uniquement sur la machine qui compile)
py -m pip install --upgrade pyinstaller || goto :err
py -m PyInstaller --noconfirm --clean --onefile --windowed --uac-admin --name "PC OPT" main.py || goto :err
echo.
echo Termine : dist\PC OPT.exe
pause
exit /b 0
:err
echo Echec de la compilation.
pause
exit /b 1
