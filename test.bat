@echo off
setlocal EnableExtensions

set "ROOT_DIR=%~dp0"
if "%ROOT_DIR:~-1%"=="\" set "ROOT_DIR=%ROOT_DIR:~0,-1%"
set "INSTALL_SCRIPT=%ROOT_DIR%\install.bat"
set "BACKEND_DIR=%ROOT_DIR%\backend"
set "PYTHON_EXE=%ROOT_DIR%\.venv\Scripts\python.exe"

if not exist "%PYTHON_EXE%" (
    echo [INFO] Project environment not found. Running install.bat first...
    call "%INSTALL_SCRIPT%"
    if errorlevel 1 exit /b 1
)

if not exist "%BACKEND_DIR%\tests" (
    echo [ERROR] Test directory not found: %BACKEND_DIR%\tests
    exit /b 1
)

echo [INFO] Running pytest with timeout 60 seconds...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$p=Start-Process -FilePath '%PYTHON_EXE%' -ArgumentList '-m','pytest','-q' -WorkingDirectory '%BACKEND_DIR%' -NoNewWindow -PassThru; if(-not $p.WaitForExit(60)){ try{$p.Kill()}catch{}; Write-Host '[ERROR] pytest timed out after 60 seconds.'; exit 124 }; exit $p.ExitCode"
set "TEST_EXIT=%ERRORLEVEL%"

if not "%TEST_EXIT%"=="0" (
    echo [ERROR] Tests failed with code %TEST_EXIT%.
    exit /b %TEST_EXIT%
)

echo [OK] All tests passed.
exit /b 0
