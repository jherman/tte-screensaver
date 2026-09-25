@echo off
setlocal
REM Build script for TTE Screensaver
REM Creates dist\tte-screensaver.scr, which can be installed as a Windows screensaver.
REM Everything is installed into .venv, never into the global Python, so it works from any prompt.

cd /d "%~dp0"
echo Building TTE Screensaver...

if not exist ".venv\Scripts\python.exe" (
    echo Creating .venv...
    py -3 -m venv .venv || python -m venv .venv
    if not exist ".venv\Scripts\python.exe" goto :failed
)
set "PYTHON=.venv\Scripts\python.exe"

REM Install dependencies if needed
"%PYTHON%" -m pip install --quiet --disable-pip-version-check -r requirements.txt pyinstaller
if errorlevel 1 goto :failed

REM Remove the previous build, so a failed build cannot pass for a fresh one
if exist "dist\tte-screensaver.exe" del "dist\tte-screensaver.exe" || goto :failed
if exist "dist\tte-screensaver.scr" del "dist\tte-screensaver.scr" || goto :failed

REM Build with PyInstaller
"%PYTHON%" -m PyInstaller --noconfirm --onefile --windowed ^
    --name "tte-screensaver" ^
    --add-data "assets;assets" ^
    --hidden-import terminaltexteffects.effects.effect_beams ^
    --hidden-import terminaltexteffects.effects.effect_binarypath ^
    --hidden-import terminaltexteffects.effects.effect_blackhole ^
    --hidden-import terminaltexteffects.effects.effect_bouncyballs ^
    --hidden-import terminaltexteffects.effects.effect_bubbles ^
    --hidden-import terminaltexteffects.effects.effect_burn ^
    --hidden-import terminaltexteffects.effects.effect_colorshift ^
    --hidden-import terminaltexteffects.effects.effect_crumble ^
    --hidden-import terminaltexteffects.effects.effect_decrypt ^
    --hidden-import terminaltexteffects.effects.effect_errorcorrect ^
    --hidden-import terminaltexteffects.effects.effect_expand ^
    --hidden-import terminaltexteffects.effects.effect_fireworks ^
    --hidden-import terminaltexteffects.effects.effect_highlight ^
    --hidden-import terminaltexteffects.effects.effect_laseretch ^
    --hidden-import terminaltexteffects.effects.effect_matrix ^
    --hidden-import terminaltexteffects.effects.effect_middleout ^
    --hidden-import terminaltexteffects.effects.effect_orbittingvolley ^
    --hidden-import terminaltexteffects.effects.effect_overflow ^
    --hidden-import terminaltexteffects.effects.effect_pour ^
    --hidden-import terminaltexteffects.effects.effect_print ^
    --hidden-import terminaltexteffects.effects.effect_rain ^
    --hidden-import terminaltexteffects.effects.effect_random_sequence ^
    --hidden-import terminaltexteffects.effects.effect_rings ^
    --hidden-import terminaltexteffects.effects.effect_scattered ^
    --hidden-import terminaltexteffects.effects.effect_slice ^
    --hidden-import terminaltexteffects.effects.effect_slide ^
    --hidden-import terminaltexteffects.effects.effect_spotlights ^
    --hidden-import terminaltexteffects.effects.effect_spray ^
    --hidden-import terminaltexteffects.effects.effect_swarm ^
    --hidden-import terminaltexteffects.effects.effect_sweep ^
    --hidden-import terminaltexteffects.effects.effect_synthgrid ^
    --hidden-import terminaltexteffects.effects.effect_unstable ^
    --hidden-import terminaltexteffects.effects.effect_vhstape ^
    --hidden-import terminaltexteffects.effects.effect_waves ^
    --hidden-import terminaltexteffects.effects.effect_wipe ^
    run.py
if errorlevel 1 goto :failed
if not exist "dist\tte-screensaver.exe" goto :failed

REM Rename to .scr
copy /y "dist\tte-screensaver.exe" "dist\tte-screensaver.scr" >nul || goto :failed
echo.
echo Build complete!
echo.
echo To install the screensaver:
echo   1. Copy dist\tte-screensaver.scr to C:\Windows\System32\
echo   2. Right-click desktop ^> Personalize ^> Lock screen ^> Screen saver settings
echo   3. Select "tte-screensaver" from the dropdown
echo.
echo Or just right-click the .scr file and select "Install"
exit /b 0

:failed
echo.
echo Build failed!
exit /b 1
