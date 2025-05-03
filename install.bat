@echo off
setlocal enabledelayedexpansion
echo ===================================
echo VTuber AI Bot Installer
echo ===================================
echo.

:: Check if Git is installed
git --version >nul 2>&1
if errorlevel 1 (
    echo Git is not installed. Please install Git from https://git-scm.com/downloads
    echo After installing Git, run this installer again.
    pause
    exit /b 1
)

:: Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Python is not installed. Please install Python 3.9 or higher from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    echo After installing Python, run this installer again.
    pause
    exit /b 1
)

:: Create installation directory
set "INSTALL_DIR=%USERPROFILE%\VTuberAIBot"
echo Installing to: "%INSTALL_DIR%"

if not exist "%INSTALL_DIR%" (
    echo Creating installation directory...
    mkdir "%INSTALL_DIR%"
)

:: Clone or update the repository
cd /d "%INSTALL_DIR%"
echo Current directory: "%CD%"

if exist ".git" (
    echo Updating repository...
    git pull
) else (
    :: Check if directory is empty
    dir /a /b | findstr "." >nul
    if not errorlevel 1 (
        echo.
        echo WARNING: Directory is not empty. Creating a new directory...
        cd ..
        set "INSTALL_DIR=%USERPROFILE%\VTuberAIBot_%RANDOM%"
        echo New installation directory: "%INSTALL_DIR%"
        mkdir "%INSTALL_DIR%"
        cd /d "%INSTALL_DIR%"
        echo Changed to directory: "%CD%"
    )

    echo Cloning repository...
    git clone https://github.com/LordIkol/vtuber-ai-bot.git .

    if errorlevel 1 (
        echo ERROR: Git clone failed. Trying alternative approach...

        cd /d "%TEMP%"
        if exist vtuber-temp rmdir /s /q vtuber-temp
        mkdir vtuber-temp
        cd vtuber-temp

        echo Cloning to temporary directory...
        git clone https://github.com/LordIkol/vtuber-ai-bot.git .

        if errorlevel 1 (
            echo CRITICAL ERROR: Git clone failed again. Please check your internet connection and Git installation.
            exit /b 1
        )

        echo Copying files to installation directory...
        xcopy /E /Y /I * "%INSTALL_DIR%\"
        cd /d "%INSTALL_DIR%"
    )

    echo Verifying files...
    dir
)

:: Create a virtual environment if it doesn't exist
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

:: Activate the virtual environment
echo Activating virtual environment...
call "venv\Scripts\activate.bat"

:: Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip

:: Install requirements
echo Installing dependencies...
if exist requirements-minimal.txt (
    echo Using minimal requirements file for better compatibility...
    pip install -r requirements-minimal.txt
) else if exist requirements.txt (
    echo Using full requirements file...
    pip install -r requirements.txt
) else (
    echo WARNING: No requirements file found. Installing essential packages...
    pip install nicegui openai pyaudio sounddevice TTS python-dotenv
)

:: Create .env file from example if it doesn't exist
if not exist ".env" (
    echo Creating .env file from example...
    if exist ".env.example" (
        copy ".env.example" ".env"
    ) else (
        echo WARNING: .env.example not found. Creating a basic .env file...
        (
            echo # OpenAI Configuration
            echo OPENAI_API_KEY=your_api_key_here
            echo.
            echo # Audio Configuration
            echo SAMPLE_RATE=44100
            echo CHUNK_SIZE=1024
            echo SILENCE_THRESHOLD=300
            echo SILENCE_DURATION=2.0
            echo.
            echo # TTS Configuration
            echo TTS_VOLUME=0.2
            echo TTS_ENGINE=coqui
        ) > ".env"
    )
    echo Please edit the .env file to configure your API keys and settings.
)

:: Create start.bat
(
    echo @echo off
    echo echo ==================================
    echo echo Starting VTuber AI Bot
    echo echo ==================================
    echo echo.
    echo call "venv\Scripts\activate.bat"
    echo python ui_main.py
    echo if %%errorlevel%% neq 0 (
    echo     echo.
    echo     echo Application exited with an error. Press any key to close this window.
    echo     pause ^>nul
    echo )
) > "start.bat"

:: Create desktop shortcut
echo Creating desktop shortcut...
powershell -NoProfile -Command ^
    "$WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%USERPROFILE%\Desktop\VTuber AI Bot.lnk'); $Shortcut.TargetPath = '%INSTALL_DIR%\start.bat'; $Shortcut.WorkingDirectory = '%INSTALL_DIR%'; $Shortcut.Save()" 2>nul

if errorlevel 1 (
    echo Warning: Could not create desktop shortcut. You can still run start.bat from the installation directory.
) else (
    echo Desktop shortcut created successfully.
)

echo.
:: Final verification
echo Performing final verification...
if not exist "%INSTALL_DIR%\ui_main.py" (
    echo.
    echo ERROR: Critical files are missing from the installation directory.
    echo Please try running the installer again or manually download from:
    echo https://github.com/LordIkol/vtuber-ai-bot
    echo.
    pause
    exit /b 1
)

echo.
echo ===================================
echo Installation completed successfully!
echo ===================================
echo.
echo VTuber AI Bot has been installed to: "%INSTALL_DIR%"
echo.
echo Files in installation directory:
dir "%INSTALL_DIR%"
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
