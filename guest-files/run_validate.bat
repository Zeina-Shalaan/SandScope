
@echo off
setlocal

cd /d C:\SandScope

echo Running SandScope baseline validation...

py -3.13 C:\SandScope\environment\validate_baseline.py > C:\SandScope\baseline_validation.txt 2>&1

set "RESULT=%ERRORLEVEL%"

echo %RESULT% > C:\SandScope\baseline_validation.exit

type C:\SandScope\baseline_validation.txt

echo.
echo Validator exit code: %RESULT%

exit /b %RESULT%

