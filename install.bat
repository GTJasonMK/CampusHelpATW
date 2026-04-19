@echo off
setlocal EnableExtensions

set "ROOT_DIR=%~dp0"
if "%ROOT_DIR:~-1%"=="\" set "ROOT_DIR=%ROOT_DIR:~0,-1%"
set "BACKEND_DIR=%ROOT_DIR%\backend"
set "VENV_DIR=%ROOT_DIR%\.venv"
set "BACKEND_ENV=%BACKEND_DIR%\.env"
set "BACKEND_ENV_EXAMPLE=%BACKEND_DIR%\.env.example"

call :detect_host_python
if errorlevel 1 exit /b 1
call :ensure_venv
if errorlevel 1 exit /b 1
call :ensure_uv
if errorlevel 1 exit /b 1
call :prepare_env_file
if errorlevel 1 exit /b 1
call :install_requirements
if errorlevel 1 exit /b 1

echo [OK] Installation completed.
echo [OK] Virtual environment: %VENV_DIR%
echo [OK] Backend env: %BACKEND_ENV%
exit /b 0

:detect_host_python
set "HOST_PYTHON_EXE="
set "HOST_PYTHON_FLAG="
where py >nul 2>nul
if not errorlevel 1 (
    set "HOST_PYTHON_EXE=py"
    set "HOST_PYTHON_FLAG=-3"
)
if not defined HOST_PYTHON_EXE (
    where python >nul 2>nul
    if not errorlevel 1 (
        set "HOST_PYTHON_EXE=python"
        set "HOST_PYTHON_FLAG="
    )
)
if not defined HOST_PYTHON_EXE (
    echo [ERROR] Python 3 was not found in PATH.
    echo [HINT] Install Python 3.10+ and run this script again.
    exit /b 1
)
exit /b 0

:ensure_venv
if not exist "%VENV_DIR%\Scripts\python.exe" (
    echo [INFO] Creating project virtual environment...
    "%HOST_PYTHON_EXE%" %HOST_PYTHON_FLAG% -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        exit /b 1
    )
)
set "PYTHON_EXE=%VENV_DIR%\Scripts\python.exe"
if not exist "%PYTHON_EXE%" (
    echo [ERROR] Virtual environment python is missing: %PYTHON_EXE%
    exit /b 1
)
exit /b 0

:ensure_uv
set "UV_EXE=%VENV_DIR%\Scripts\uv.exe"
if exist "%UV_EXE%" exit /b 0

echo [WARN] uv is required for dependency management and is not available yet.
set "CONSENT="
set /p "CONSENT=Install uv into the project virtual environment now? [Y/N]: "
if /I not "%CONSENT%"=="Y" if /I not "%CONSENT%"=="YES" (
    echo [ERROR] uv installation was declined. Aborting.
    exit /b 1
)

echo [INFO] Installing uv into .venv...
"%PYTHON_EXE%" -m pip install --upgrade pip
if errorlevel 1 (
    echo [ERROR] Failed to upgrade pip in .venv.
    exit /b 1
)
"%PYTHON_EXE%" -m pip install uv
if errorlevel 1 (
    echo [ERROR] Failed to install uv in .venv.
    exit /b 1
)

if not exist "%UV_EXE%" (
    echo [ERROR] uv executable was not found after installation.
    exit /b 1
)
exit /b 0

:prepare_env_file
if not exist "%BACKEND_DIR%" (
    echo [ERROR] Backend directory not found: %BACKEND_DIR%
    exit /b 1
)
if not exist "%BACKEND_ENV_EXAMPLE%" (
    echo [ERROR] Missing backend .env example file: %BACKEND_ENV_EXAMPLE%
    exit /b 1
)

set "ENV_CREATED=0"
if not exist "%BACKEND_ENV%" (
    copy /Y "%BACKEND_ENV_EXAMPLE%" "%BACKEND_ENV%" >nul
    if errorlevel 1 (
        echo [ERROR] Failed to create backend .env.
        exit /b 1
    )
    set "ENV_CREATED=1"
)

if "%ENV_CREATED%"=="1" (
    echo [INFO] Setting default DATABASE_URL to local SQLite for first-time setup.
    powershell -NoProfile -ExecutionPolicy Bypass -Command "$p='%BACKEND_ENV%'; $c=[System.IO.File]::ReadAllText($p); $c=[regex]::Replace($c,'(?m)^DATABASE_URL=.*$','DATABASE_URL=sqlite+aiosqlite:///./campus_help_atw.dev.db'); if($c.Length -gt 0 -and $c[0] -eq [char]0xFEFF){$c=$c.Substring(1)}; $enc=New-Object System.Text.UTF8Encoding($false); [System.IO.File]::WriteAllText($p,$c,$enc)"
    if errorlevel 1 (
        echo [ERROR] Failed to update DATABASE_URL in %BACKEND_ENV%.
        exit /b 1
    )
)
exit /b 0

:install_requirements
if not exist "%BACKEND_DIR%\requirements.txt" (
    echo [ERROR] Missing %BACKEND_DIR%\requirements.txt
    exit /b 1
)

echo [INFO] Installing backend runtime dependencies...
"%UV_EXE%" pip install --python "%PYTHON_EXE%" -r "%BACKEND_DIR%\requirements.txt"
if errorlevel 1 (
    echo [ERROR] Failed to install runtime dependencies.
    exit /b 1
)

if exist "%BACKEND_DIR%\requirements-dev.txt" (
    echo [INFO] Installing backend development dependencies...
    "%UV_EXE%" pip install --python "%PYTHON_EXE%" -r "%BACKEND_DIR%\requirements-dev.txt"
    if errorlevel 1 (
        echo [ERROR] Failed to install development dependencies.
        exit /b 1
    )
)
exit /b 0
