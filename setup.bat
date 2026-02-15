@echo off
echo ===========================================
echo   Dalanda - Setup Script
echo ===========================================
echo.

echo [1/4] Installing Python dependencies...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ERROR: Failed to install Python dependencies
    pause
    exit /b 1
)

echo.
echo [2/4] Pulling Ollama models (make sure Ollama is installed)...
echo Pulling phi3.5 (Text Agent ~2.2GB)...
ollama pull phi3.5
echo Pulling llama3.2 (Verifier ~2.0GB)...
ollama pull llama3.2

echo.
echo [3/4] Installing UI dependencies...
cd user-interface
call npm install
cd ..

echo.
echo ===========================================
echo   Setup Complete!
echo ===========================================
echo.
echo To run the app:
echo   1. Start Ollama:  ollama serve
echo   2. Start Backend: python api.py
echo   3. Start UI:      cd user-interface ^&^& npm run dev
echo.
echo Then open http://localhost:5173 in your browser
echo.
pause
