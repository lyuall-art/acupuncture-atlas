@echo off
title Acupuncture AI Backend
cd /d C:\Users\Lyu\.openclaw\workspace\acupuncture\backend
echo Starting backend server...
call .venv\Scripts\activate
start "Backend" cmd /k "uvicorn main:app --host 0.0.0.0 --port 8000"
timeout /t 3 >nul
echo Starting tunnel...
start "Tunnel" cmd /k "lt --port 8000 --subdomain acuviz"