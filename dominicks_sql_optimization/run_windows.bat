@echo off
setlocal
cd /d "%~dp0"
python run_all.py --data-dir "data" --repeats 7
if errorlevel 1 (
  echo.
  echo FAILED. Read the error above.
  pause
  exit /b 1
)
echo.
echo Finished. Open results\BENCHMARK_REPORT.md
pause
