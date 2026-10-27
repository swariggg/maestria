@echo off
echo ========================================================
echo Ejecutando Bateria de Pruebas Automatizadas (Pytest)
echo ========================================================
cd backend
call .venv\Scripts\activate
pytest -v
pause
