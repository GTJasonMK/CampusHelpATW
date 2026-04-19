@echo off
setlocal EnableExtensions

set "ROOT_DIR=%~dp0"
if "%ROOT_DIR:~-1%"=="\" set "ROOT_DIR=%ROOT_DIR:~0,-1%"
set "INSTALL_SCRIPT=%ROOT_DIR%\install.bat"
set "BACKEND_DIR=%ROOT_DIR%\backend"
set "BACKEND_ENV=%BACKEND_DIR%\.env"
set "MINIAPP_CONFIG=%ROOT_DIR%\miniapp-template\config\index.js"
set "PYTHON_EXE=%ROOT_DIR%\.venv\Scripts\python.exe"

if not exist "%PYTHON_EXE%" (
    echo [INFO] Project environment not found. Running install.bat first...
    call "%INSTALL_SCRIPT%"
    if errorlevel 1 exit /b 1
)

if not exist "%BACKEND_ENV%" (
    echo [INFO] Backend .env not found. Running install.bat first...
    call "%INSTALL_SCRIPT%"
    if errorlevel 1 exit /b 1
)

call :ensure_backend_dependencies
if errorlevel 1 exit /b 1

call :normalize_env_file
if errorlevel 1 exit /b 1

call :pick_free_port 3000 3999 BACKEND_PORT
if errorlevel 1 exit /b 1
set "LOCAL_API_BASE=http://127.0.0.1:%BACKEND_PORT%/api/v1"

call :read_database_url
if errorlevel 1 exit /b 1

if /I "%DB_MODE%"=="SQLITE" (
    echo [INFO] SQLite mode detected. Initializing local database if needed...
    pushd "%BACKEND_DIR%"
    set "OLD_PYTHONPATH=%PYTHONPATH%"
    set "PYTHONPATH=%BACKEND_DIR%"
    "%PYTHON_EXE%" scripts\init_sqlite_dev.py
    if defined OLD_PYTHONPATH (
        set "PYTHONPATH=%OLD_PYTHONPATH%"
    ) else (
        set "PYTHONPATH="
    )
    if errorlevel 1 (
        popd
        echo [ERROR] SQLite initialization failed.
        exit /b 1
    )
    popd
)

call :sync_miniapp_config
if errorlevel 1 (
    echo [WARN] Failed to update miniapp config automatically.
    echo [WARN] Set baseUrl manually to: %LOCAL_API_BASE%
)

echo [INFO] Backend port selected: %BACKEND_PORT%
echo [INFO] Miniapp baseUrl: %LOCAL_API_BASE%
echo [INFO] Swagger: http://127.0.0.1:%BACKEND_PORT%/docs
set "BACKEND_HEALTH_URL=http://127.0.0.1:%BACKEND_PORT%/healthz"

call :ensure_backend_running
if errorlevel 1 (
    echo [WARN] Backend did not become ready in time.
    echo [WARN] You can still inspect backend logs in the backend window.
)

echo [OK] Backend launched.
echo [OK] Backend health URL: %BACKEND_HEALTH_URL%
exit /b 0

:ensure_backend_dependencies
"%PYTHON_EXE%" -c "import multipart" >nul 2>nul
if errorlevel 1 (
    echo [INFO] Missing backend dependency detected: python-multipart.
    echo [INFO] Running install.bat to sync dependencies...
    call "%INSTALL_SCRIPT%"
    if errorlevel 1 (
        echo [ERROR] Failed to install required dependencies.
        exit /b 1
    )
)
exit /b 0

:pick_free_port
set "PORT_START=%~1"
set "PORT_END=%~2"
set "PORT_VAR_NAME=%~3"
set "SELECTED_PORT="

for /f "usebackq delims=" %%P in (`powershell -NoProfile -ExecutionPolicy Bypass -Command "$start=%PORT_START%; $end=%PORT_END%; $selected=$null; for($p=$start; $p -le $end; $p++){ $listener=[System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback,$p); try{ $listener.Start(); $listener.Stop(); $selected=$p; break } catch {} }; if($selected -eq $null){ exit 1 } ; Write-Output $selected"`) do (
    set "SELECTED_PORT=%%P"
)

if not defined SELECTED_PORT (
    echo [ERROR] No free port found in range %PORT_START%-%PORT_END%.
    exit /b 1
)
set "%PORT_VAR_NAME%=%SELECTED_PORT%"
exit /b 0

:ensure_backend_running
call :check_backend_ready
if not errorlevel 1 (
    echo [INFO] Backend is already running on port %BACKEND_PORT%.
    exit /b 0
)

call :start_backend_process
if errorlevel 1 (
    echo [ERROR] Failed to start backend process.
    exit /b 1
)

call :wait_backend_ready 45
if errorlevel 1 exit /b 1
exit /b 0

:start_backend_process
start "CampusHelpATW Backend" /D "%BACKEND_DIR%" "%PYTHON_EXE%" -m uvicorn app.main:app --host 127.0.0.1 --port %BACKEND_PORT% --reload --app-dir "%BACKEND_DIR%" --reload-dir "%BACKEND_DIR%"
if errorlevel 1 exit /b 1
echo [INFO] Backend process launched in a new window.
exit /b 0

:check_backend_ready
powershell -NoProfile -ExecutionPolicy Bypass -Command "try{ $r=Invoke-WebRequest -Uri '%BACKEND_HEALTH_URL%' -UseBasicParsing -TimeoutSec 2; if($r.StatusCode -ge 200 -and $r.StatusCode -lt 500){ exit 0 } else { exit 1 } } catch { exit 1 }"
if errorlevel 1 exit /b 1
exit /b 0

:wait_backend_ready
set "WAIT_SECONDS=%~1"
if "%WAIT_SECONDS%"=="" set "WAIT_SECONDS=30"

for /L %%I in (1,1,%WAIT_SECONDS%) do (
    call :check_backend_ready
    if not errorlevel 1 (
        echo [INFO] Backend is ready.
        exit /b 0
    )
    >nul timeout /t 1 /nobreak
)
exit /b 1

:read_database_url
set "DATABASE_URL="
for /f "usebackq delims=" %%L in (`powershell -NoProfile -ExecutionPolicy Bypass -Command "$line=(Get-Content -Path '%BACKEND_ENV%' | Where-Object {$_ -match '^\s*DATABASE_URL='} | Select-Object -First 1); if($line){ $line.Substring($line.IndexOf('=')+1).Trim() }"`) do (
    set "DATABASE_URL=%%L"
)

if not defined DATABASE_URL (
    echo [WARN] DATABASE_URL not found in backend .env. Defaulting to SQLite.
    set "DATABASE_URL=sqlite+aiosqlite:///./campus_help_atw.dev.db"
    >> "%BACKEND_ENV%" echo DATABASE_URL=sqlite+aiosqlite:///./campus_help_atw.dev.db
)

set "DB_MODE=MYSQL"
echo %DATABASE_URL% | findstr /I /B "sqlite+aiosqlite://" >nul
if not errorlevel 1 set "DB_MODE=SQLITE"
exit /b 0

:sync_miniapp_config
if not exist "%MINIAPP_CONFIG%" (
    echo [WARN] Miniapp config file not found: %MINIAPP_CONFIG%
    exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -Command "$f='%MINIAPP_CONFIG%'; $content=[System.IO.File]::ReadAllText($f); $q=[char]34; $pattern=('baseUrl:\s*' + $q + '[^' + $q + ']+' + $q); $replacement=('baseUrl: ' + $q + $env:LOCAL_API_BASE + $q); $updated=[regex]::Replace($content,$pattern,$replacement); if($updated.Length -gt 0 -and $updated[0] -eq [char]0xFEFF){$updated=$updated.Substring(1)}; $enc=New-Object System.Text.UTF8Encoding($false); [System.IO.File]::WriteAllText($f,$updated,$enc)"
if errorlevel 1 exit /b 1
exit /b 0

:normalize_env_file
if not exist "%BACKEND_ENV%" (
    echo [ERROR] Backend env file not found: %BACKEND_ENV%
    exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -Command "$p='%BACKEND_ENV%'; $c=[System.IO.File]::ReadAllText($p); if($c.Length -gt 0 -and $c[0] -eq [char]0xFEFF){$c=$c.Substring(1)}; $enc=New-Object System.Text.UTF8Encoding($false); [System.IO.File]::WriteAllText($p,$c,$enc)"
if errorlevel 1 (
    echo [ERROR] Failed to normalize backend .env encoding.
    exit /b 1
)
exit /b 0
