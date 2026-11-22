@echo off
setlocal

if not exist "C:\SandScope\test_output" mkdir "C:\SandScope\test_output"

echo SandScope harmless simulator ran successfully. > "C:\SandScope\test_output\simulator_result.txt"

echo Harmless simulator completed.
exit /b 0
