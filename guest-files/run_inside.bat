
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

set "PROCMON=C:\SandScope\tools\procmon\Procmon64.exe"
set "PML=%OUT%\trace.pml"

if not exist "%PROCMON%" (
    echo ERROR: Procmon not found at %PROCMON%.
    exit /b 1
)

REM Remove the previous run's logs, so a failed capture cannot silently reuse them.
del /q "%OUT%\trace.pml" "%OUT%\trace.csv" "%OUT%\sysmon.xml" "%OUT%\events.json" "%OUT%\events_all.json" "%OUT%\behavior_findings.json" 2>nul

REM Clear old Sysmon events so sysmon.xml holds only this run.
wevtutil cl Microsoft-Windows-Sysmon/Operational

echo.
echo Starting Procmon capture...
start "" "%PROCMON%" /AcceptEula /Quiet /Minimized /BackingFile "%PML%"
REM Wait until Procmon is actually capturing, so the sample's first events are not missed.
"%PROCMON%" /WaitForIdle

echo.
echo Starting approved simulator...
start /wait "" "%SAMPLE%"
set "EXIT_CODE=%ERRORLEVEL%"

echo.
echo Stopping Procmon and converting the trace to CSV...
"%PROCMON%" /Terminate
"%PROCMON%" /AcceptEula /Quiet /OpenLog "%PML%" /SaveAs "%OUT%\trace.csv"

if not exist "%OUT%\trace.csv" echo WARNING: trace.csv was not created. >> "%LOG%"

echo.
echo Exporting Sysmon events...
REM /e:Events adds a root element; /uni:true writes UTF-16 so characters like the (R) symbol are not garbled.
wevtutil qe Microsoft-Windows-Sysmon/Operational /f:xml /e:Events /uni:true > "%OUT%\sysmon.xml"
if errorlevel 1 echo WARNING: Sysmon export failed. >> "%LOG%"

echo End time: %DATE% %TIME% >> "%LOG%"
echo Exit code: %EXIT_CODE% >> "%LOG%"

echo.
echo Simulator finished with exit code %EXIT_CODE%.

exit /b %EXIT_CODE%
