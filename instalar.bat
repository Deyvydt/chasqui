@echo off
chcp 65001 >nul
set PYTHONUTF8=1
cd /d "%~dp0"
echo === Chasqui: instalacion (solo una vez) ===

where python >nul 2>nul || (echo No encontre Python. Instala Python 3.11+ desde python.org y vuelve a correr. & pause & exit /b 1)

if not exist .venv (
  echo Creando entorno virtual .venv ...
  python -m venv .venv || (echo Error creando el venv & pause & exit /b 1)
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip -q
echo Instalando dependencias (toma unos minutos)...
pip install -r requirements.txt -q || (echo Error instalando dependencias & pause & exit /b 1)
python -m chasqui.agent download-files

if not exist .env copy .env.example .env >nul
python scripts\importar_livekit.py
echo.
python scripts\revisar_config.py
echo.
echo Listo. Pega en .env las keys que faltan (marcadas con X) y luego corre configurar.bat
pause
