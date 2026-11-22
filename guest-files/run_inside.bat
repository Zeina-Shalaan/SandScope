
@echo off
setlocal

REM SandScope controlled execution runner
REM Arguments:
REM   %1 = approved simulator executable
REM   %2 = output directory

if "%~1"=="" (
    echo ERROR: No simulator path provided.
    exit /b 1
)

if "%~2"=="" (
    echo ERROR: No output directory provided.
    exit /b 1
)

set "SAMPLE=%~1"
set "OUT=%~2"

if not exist "%SAMPLE%" (
    echo ERROR: Simulator does not exist.
    exit /b 1
)

if not exist "%OUT%" mkdir "%OUT%"

if not exist "%OUT%" (
    echo ERROR: Could not create output directory.
    exit /b 1
)

set "LOG=%OUT%\execution_metadata.txt"

echo SandScope Execution Metadata > "%LOG%"
echo ============================= >> "%LOG%"
echo Start time: %DATE% %TIME% >> "%LOG%"
echo Simulator: %SAMPLE% >> "%LOG%"
echo Computer: %COMPUTERNAME% >> "%LOG%"
echo User: %USERNAME% >> "%LOG%"

echo.
echo Starting approved simulator...
start /wait "" "%SAMPLE%"
set "EXIT_CODE=%ERRORLEVEL%"

echo End time: %DATE% %TIME% >> "%LOG%"
echo Exit code: %EXIT_CODE% >> "%LOG%"

echo.
echo Simulator finished with exit code %EXIT_CODE%.

exit /b %EXIT_CODE%
