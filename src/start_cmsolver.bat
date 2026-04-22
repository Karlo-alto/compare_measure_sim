@echo off
setlocal

set "CMSOLVER=C:\kwebelhaus\karl\cm_core\build\windows-release\bin\cmsolver.exe"

if not exist "%CMSOLVER%" (
    echo FEHLER: cmsolver.exe nicht gefunden unter:
    echo %CMSOLVER%
    pause
    exit /b 1
)

set /p "PATH_rm1=Bitte Pfad zur Eingabedatei angeben: "

if "%PATH_rm1%"=="" (
    echo FEHLER: Kein Pfad angegeben.
    pause
    exit /b 1
)

if not exist "%PATH_rm1%" (
    echo WARNUNG: Die angegebene Datei wurde nicht gefunden: %PATH_rm1%
    pause
)

echo.
echo Starte cmsolver mit:
echo   %CMSOLVER% -sim 15 "%PATH_rm1%" -hf emmi 1
echo.

"%CMSOLVER%" -sim 15 "%PATH_rm1%" -hf emmi 1

echo.
echo cmsolver beendet mit Exitcode: %ERRORLEVEL%
pause
endlocal