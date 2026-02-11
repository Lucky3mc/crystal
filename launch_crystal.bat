@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

title Crystal AI Launcher

echo.
echo =========================================
echo        💎 Starting Crystal AI System
echo =========================================
echo.

REM ================================
REM SET PROJECT ROOT
REM ================================
set PROJECT_ROOT=C:\Users\user\Documents\crystal_ai
cd /d "%PROJECT_ROOT%" || (
    echo ❌ Failed to access project directory
    pause
    exit /b
)

REM ================================
REM CREATE LOGS FOLDER
REM ================================
if not exist logs mkdir logs

REM ================================
REM START LITELLM
REM ================================
echo 🔹 Starting LiteLLM Proxy on port 8000...
start "LiteLLM Proxy" cmd /k ^
    "litellm --config %PROJECT_ROOT%\litellm.yaml --port 8000 > %PROJECT_ROOT%\logs\litellm.log 2>&1"

timeout /t 2 /nobreak >nul

REM ================================
REM START CRYSTAL GUI
REM ================================
echo 🔹 Starting Crystal GUI (Streamlit)...
cd /d "%PROJECT_ROOT%"
start "Crystal GUI" cmd /k ^
    "streamlit run %PROJECT_ROOT%\gui\app.py --server.port 8501"

timeout /t 2 /nobreak >nul

REM ================================
REM OPEN BROWSER
REM ================================
echo 🔹 Opening Crystal Interface...
start http://localhost:8501

echo.
echo =========================================
echo        ✅ Crystal AI is running
echo =========================================
echo  - LiteLLM  : http://localhost:8000
echo  - GUI      : http://localhost:8501
echo =========================================
echo.

pause
endlocal
