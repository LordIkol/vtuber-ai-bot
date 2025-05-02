@echo off
echo ===================================
echo VTuber AI Bot Installer
echo ===================================
echo.

:: Check if Git is installed
git --version > nul 2>&1
if %errorlevel% neq 0 (
    echo Git is not installed. Please install Git from https://git-scm.com/downloads
    echo After installing Git, run this installer again.
    pause
    exit /b 1
)

:: Check if Python is installed
python --version > nul 2>&1
if %errorlevel% neq 0 (
    echo Python is not installed. Please install Python 3.9 or higher from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    echo After installing Python, run this installer again.
    pause
    exit /b 1
)

:: Create installation directory
set INSTALL_DIR=%USERPROFILE%\VTuberAIBot
echo Installing to: %INSTALL_DIR%

if not exist "%INSTALL_DIR%" (
    echo Creating installation directory...
    mkdir "%INSTALL_DIR%"
)

:: Clone or update the repository
cd "%INSTALL_DIR%"
if exist .git (
    echo Updating repository...
    git pull
) else (
    echo Cloning repository...
    git clone https://github.com/LordIkol/vtuber-ai-bot.git .
)

:: Create a virtual environment if it doesn't exist
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)

:: Activate the virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

:: Install or upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip

:: Install requirements
echo Installing dependencies...
pip install -r requirements.txt

:: Create .env file from example if it doesn't exist
if not exist .env (
    echo Creating .env file from example...
    copy .env.example .env
    echo Please edit the .env file to configure your API keys and settings.
)

:: Create start.bat if it doesn't exist
echo @echo off > start.bat
echo echo ================================== >> start.bat
echo echo Starting VTuber AI Bot >> start.bat
echo echo ================================== >> start.bat
echo echo. >> start.bat
echo call venv\Scripts\activate.bat >> start.bat
echo python ui_main.py >> start.bat
echo if %%errorlevel%% neq 0 ( >> start.bat
echo     echo. >> start.bat
echo     echo Application exited with an error. Press any key to close this window. >> start.bat
echo     pause ^> nul >> start.bat
echo ) >> start.bat

:: Create desktop shortcut
echo Creating desktop shortcut...
powershell "$WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%USERPROFILE%\Desktop\VTuber AI Bot.lnk'); $Shortcut.TargetPath = '%INSTALL_DIR%\start.bat'; $Shortcut.WorkingDirectory = '%INSTALL_DIR%'; $Shortcut.Save()"

echo.
echo ===================================
echo Installation completed successfully!
echo ===================================
echo.
echo VTuber AI Bot has been installed to: %INSTALL_DIR%
echo.
echo To start the VTuber AI Bot:
echo 1. Use the desktop shortcut, or
echo 2. Run start.bat in the installation directory
echo.
echo Before first use, edit the .env file in the installation directory
echo to configure your API keys and settings.
echo.
echo Enjoy your VTuber AI Bot!
echo.
pause
