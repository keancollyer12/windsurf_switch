@echo off
setlocal

:: 1. Create virtual environment if it doesn't exist
if not exist "switcher-venv" (
    echo Creating virtual environment 'switcher-venv'...
    python -m venv switcher-venv
)

:: 2. Activate the virtual environment
echo Activating virtual environment...
call switcher-venv\Scripts\activate

:: 3. Install requirements
echo Installing dependencies from requirements.txt...
python -m pip install --upgrade pip
pip install -r requirements.txt

:: 4. Finished message
echo.
echo ===========================================
echo Setup Finished Successfully!
echo ===========================================
echo.

:menu
:: 5. Choice
echo [w] Run windsurf Switcher
echo [e] Exit
echo.

set /p choice="Enter your choice (w/e): "

if /I "%choice%"=="w" goto run_wind
if /I "%choice%"=="e" goto end_script

echo Invalid choice, please try again.
echo.
goto menu

:run_wind
echo Running windsurf Switcher application...
python3 windsurf_win.py
pause
goto end_script

:end_script
echo Exiting...
deactivate
exit
