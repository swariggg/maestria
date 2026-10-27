@echo off
echo ========================================================
echo Iniciando Backend FastAPI - APP Maestria (UIDE)
echo ========================================================
cd backend
call .venv\Scripts\activate
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
pause
