@echo off
setlocal enabledelayedexpansion

echo.
echo 🚀 Talent Portfolio - Automated Setup
echo ======================================
echo.

set "PYTHON_CMD="

REM Prefer Python 3.13, then 3.12, then 3.11, then 3.10 via py launcher
where py >nul 2>&1
if not errorlevel 1 (
    py -3.13 -c "import sys; raise SystemExit(0 if (3,10) <= sys.version_info[:2] < (3,14) else 1)" >nul 2>&1
    if not errorlevel 1 set "PYTHON_CMD=py -3.13"

    if not defined PYTHON_CMD (
        py -3.12 -c "import sys; raise SystemExit(0 if (3,10) <= sys.version_info[:2] < (3,14) else 1)" >nul 2>&1
        if not errorlevel 1 set "PYTHON_CMD=py -3.12"
    )

    if not defined PYTHON_CMD (
        py -3.11 -c "import sys; raise SystemExit(0 if (3,10) <= sys.version_info[:2] < (3,14) else 1)" >nul 2>&1
        if not errorlevel 1 set "PYTHON_CMD=py -3.11"
    )

    if not defined PYTHON_CMD (
        py -3.10 -c "import sys; raise SystemExit(0 if (3,10) <= sys.version_info[:2] < (3,14) else 1)" >nul 2>&1
        if not errorlevel 1 set "PYTHON_CMD=py -3.10"
    )
)

REM Fallback to plain python if it is in supported range
if not defined PYTHON_CMD (
    python -c "import sys; raise SystemExit(0 if (3,10) <= sys.version_info[:2] < (3,14) else 1)" >nul 2>&1
    if not errorlevel 1 set "PYTHON_CMD=python"
)

if not defined PYTHON_CMD (
    echo ❌ No supported Python version found.
    echo    Required: Python >=3.10 and ^<3.14
    echo    Please install Python 3.13, 3.12, 3.11, or 3.10 and rerun setup.
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('%PYTHON_CMD% --version') do set PYVER=%%i
echo ✅ Python selected: %PYVER%
echo.

REM Create virtual environment
echo 📦 Creating virtual environment...
%PYTHON_CMD% -m venv .venv
call .venv\Scripts\activate.bat
set "PYTHON_EXE=%CD%\.venv\Scripts\python.exe"

REM Upgrade pip
echo 📦 Upgrading pip...
"%PYTHON_EXE%" -m pip install --upgrade pip

REM Install dependencies
echo 📦 Installing dependencies...
"%PYTHON_EXE%" -m pip install -r talentPortfolio\requirements.txt

REM Navigate to talentPortfolio
cd talentPortfolio

REM Create .env file if it doesn't exist
if not exist .env (
    echo.
    echo 🔐 Creating .env file...
    "%PYTHON_EXE%" -c "from django.core.management.utils import get_random_secret_key; print(f'SECRET_KEY={get_random_secret_key()}')" > .env
    echo DEBUG=True >> .env
    echo ✅ .env file created with a generated SECRET_KEY
) else (
    echo ✅ .env file already exists
)

REM Run migrations
echo.
echo 🗄️  Applying database migrations...
"%PYTHON_EXE%" manage.py migrate

REM Generate test data
echo.
set /p generate_data="📊 Populate database with users? (2 student users per course & 1 faculty user per course total courses: 229) (y/n)"
if /i "%generate_data%"=="y" (
    echo.
    echo 🎓 Generating student test data (2 student per course)...
    "%PYTHON_EXE%" manage.py generate_student_stress_test_data --students-per-course 2

    echo.
    echo 👨‍💼 Generating faculty test data (1 faculty per course)...
    "%PYTHON_EXE%" manage.py generate_faculty_stress_test_data 

    echo ✅ Test data generated successfully!
)

REM Create superuser prompt
echo.
set /p create_superuser="👤 Create a superuser account for admin access? (y/n): "
if /i "%create_superuser%"=="y" (
    "%PYTHON_EXE%" manage.py createsuperuser
)

REM Start the server
echo.
echo 🎉 Setup complete! Starting development server...
echo.
echo 📍 Application: http://127.0.0.1:8000/
echo 📍 Admin Panel: http://127.0.0.1:8000/admin/
echo.
"%PYTHON_EXE%" manage.py runserver

pause
