@echo off
REM Quick start script for Utah Campaign Finance app (Windows)

echo.
echo Utah Campaign Finance Disclosures - Quick Start
echo ==================================================
echo.

REM Check if virtual environment exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies
echo Installing dependencies...
pip install -q -r requirements.txt

REM Check if database exists
if not exist "db.sqlite3" (
    echo Setting up database...
    python manage.py makemigrations
    python manage.py migrate

    echo.
    echo Create an admin user (you can do this later with: python manage.py createsuperuser)
    set /p CREATEUSER="Create admin user now? (y/n): "
    if /i "%CREATEUSER%"=="y" (
        python manage.py createsuperuser
    )

    echo.
    echo Import sample data? This will import report #198820 for testing.
    set /p IMPORTDATA="Import sample report? (y/n): "
    if /i "%IMPORTDATA%"=="y" (
        python manage.py import_disclosure https://disclosures.utah.gov/Search/PublicSearch/Report/198820
    )
)

echo.
echo Setup complete!
echo.
echo Starting development server...
echo    Visit: http://localhost:8000/
echo    Admin: http://localhost:8000/admin/
echo.
echo    Press Ctrl+C to stop the server
echo.

python manage.py runserver

pause
