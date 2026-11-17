@echo off
chcp 65001 >nul
set PYTHONUTF8=1
cd /d "%~dp0"
call .venv\Scripts\activate.bat || (echo Primero corre instalar.bat & pause & exit /b 1)
echo === Chasqui: demo ===
echo Abriendo el agente de voz en otra ventana...
start "Chasqui - agente de voz" cmd /k ".venv\Scripts\python.exe -m chasqui.agent dev"
echo Esperando 20 segundos a que el agente se conecte a LiveKit...
timeout /t 20 /nobreak >nul
python -m chasqui correr --forzar
echo.
echo Contesta tu celular :)  Cuando termines, cierra la ventana del agente.
pause
