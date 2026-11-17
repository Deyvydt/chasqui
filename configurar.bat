@echo off
chcp 65001 >nul
set PYTHONUTF8=1
cd /d "%~dp0"
call .venv\Scripts\activate.bat || (echo Primero corre instalar.bat & pause & exit /b 1)
echo === Chasqui: configuracion (despues de pegar tus keys en .env) ===

python scripts\importar_livekit.py

findstr /r /c:"^SIP_OUTBOUND_TRUNK_ID=..*" .env >nul
if errorlevel 1 (
  echo Configurando telefonia Twilio + LiveKit...
  python scripts\configurar_telefonia.py || (echo Fallo la telefonia: revisa tus keys de Twilio & pause & exit /b 1)
) else (
  echo Telefonia ya configurada.
)

echo.
python scripts\revisar_config.py || (pause & exit /b 1)
echo.
echo Enviando WhatsApp de prueba (antes manda "join ..." al +1 415 523 8886)...
python -m chasqui probar-whatsapp
echo.
echo Todo listo. Para la demo: doble clic en demo.bat
pause
