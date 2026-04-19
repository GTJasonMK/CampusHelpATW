@echo off
setlocal EnableExtensions

set "ROOT_DIR=%~dp0"
if "%ROOT_DIR:~-1%"=="\" set "ROOT_DIR=%ROOT_DIR:~0,-1%"
set "INSTALL_SCRIPT=%ROOT_DIR%\install.bat"
set "BACKEND_DIR=%ROOT_DIR%\backend"
set "MINIAPP_DIR=%ROOT_DIR%\miniapp-template"
set "DIST_DIR=%ROOT_DIR%\dist"
set "PYTHON_EXE=%ROOT_DIR%\.venv\Scripts\python.exe"

if not exist "%PYTHON_EXE%" (
    echo [INFO] Project environment not found. Running install.bat first...
    call "%INSTALL_SCRIPT%"
    if errorlevel 1 exit /b 1
)

for /f "usebackq delims=" %%T in (`powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-Date -Format yyyyMMdd-HHmmss"`) do (
    set "BUILD_STAMP=%%T"
)
if not defined BUILD_STAMP (
    echo [ERROR] Failed to generate build timestamp.
    exit /b 1
)

if not exist "%DIST_DIR%" mkdir "%DIST_DIR%"
if errorlevel 1 (
    echo [ERROR] Failed to create dist directory: %DIST_DIR%
    exit /b 1
)

echo [INFO] Running Python bytecode compilation check...
"%PYTHON_EXE%" -m compileall "%BACKEND_DIR%\app"
if errorlevel 1 (
    echo [ERROR] Python compile check failed.
    exit /b 1
)

echo [INFO] Exporting OpenAPI schema...
pushd "%BACKEND_DIR%"
"%PYTHON_EXE%" -c "import json; from app.main import app; print(json.dumps(app.openapi(), ensure_ascii=False, indent=2))" > "%DIST_DIR%\openapi-%BUILD_STAMP%.json"
set "OPENAPI_EXIT=%ERRORLEVEL%"
popd
if not "%OPENAPI_EXIT%"=="0" (
    echo [ERROR] Failed to export OpenAPI schema.
    exit /b %OPENAPI_EXIT%
)

set "BACKEND_ZIP=%DIST_DIR%\backend-%BUILD_STAMP%.zip"
set "MINIAPP_ZIP=%DIST_DIR%\miniapp-template-%BUILD_STAMP%.zip"

echo [INFO] Packaging backend source...
powershell -NoProfile -ExecutionPolicy Bypass -Command "if(Test-Path '%BACKEND_ZIP%'){Remove-Item -Force '%BACKEND_ZIP%'}; $items=Get-ChildItem -Force -Path '%BACKEND_DIR%' | Where-Object { $_.Name -notin @('.env','.pytest_cache','.ruff_cache') }; Compress-Archive -Path ($items.FullName) -DestinationPath '%BACKEND_ZIP%' -Force"
if errorlevel 1 (
    echo [ERROR] Failed to package backend source.
    exit /b 1
)

echo [INFO] Packaging miniapp source...
powershell -NoProfile -ExecutionPolicy Bypass -Command "if(Test-Path '%MINIAPP_ZIP%'){Remove-Item -Force '%MINIAPP_ZIP%'}; Compress-Archive -Path '%MINIAPP_DIR%\*' -DestinationPath '%MINIAPP_ZIP%' -Force"
if errorlevel 1 (
    echo [ERROR] Failed to package miniapp source.
    exit /b 1
)

echo [OK] Build completed.
echo [OK] OpenAPI: %DIST_DIR%\openapi-%BUILD_STAMP%.json
echo [OK] Backend package: %BACKEND_ZIP%
echo [OK] Miniapp package: %MINIAPP_ZIP%
exit /b 0
