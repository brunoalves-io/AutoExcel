@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"
title AutoExcel by AB Alves - Instalacao

echo ==========================================================
echo   AutoExcel by AB Alves - Modo Desktop nativo
echo ==========================================================
echo.

set "VPY=%CD%\.venv_v4\Scripts\python.exe"
set "BASEPY_CMD="
set "BASEPY_EXE="
set "APP_EXE=%CD%\AutoExcel by AB Alves.exe"

rem 1) Reutiliza o ambiente desta pasta, se ja existir e funcionar.
if exist "%VPY%" (
  "%VPY%" -c "import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)" >nul 2>nul
  if not errorlevel 1 goto :venv_ok
)

if exist ".venv_v4" (
  echo Removendo ambiente local incompleto...
  rmdir /s /q ".venv_v4" >nul 2>nul
)

rem 2) Procura Python instalado normalmente.
py -3 -c "import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)" >nul 2>nul
if not errorlevel 1 (
  set "BASEPY_CMD=py -3"
  goto :create_from_cmd
)

python -c "import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)" >nul 2>nul
if not errorlevel 1 (
  set "BASEPY_CMD=python"
  goto :create_from_cmd
)

python3 -c "import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)" >nul 2>nul
if not errorlevel 1 (
  set "BASEPY_CMD=python3"
  goto :create_from_cmd
)

rem 3) Procura instalacoes tradicionais do Python no perfil do usuario.
for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python*") do (
  if exist "%%~fD\python.exe" (
    "%%~fD\python.exe" -c "import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)" >nul 2>nul
    if not errorlevel 1 (
      set "BASEPY_EXE=%%~fD\python.exe"
      goto :create_from_exe
    )
  )
)

rem 4) Procura instalacoes da Microsoft Store que exponham python.exe real.
for /d %%D in ("%LOCALAPPDATA%\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.*") do (
  if exist "%%~fD\python.exe" (
    "%%~fD\python.exe" -c "import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)" >nul 2>nul
    if not errorlevel 1 (
      set "BASEPY_EXE=%%~fD\python.exe"
      goto :create_from_exe
    )
  )
)

rem 5) Procura um ambiente Python de uma versao anterior do AutoExcel
rem    nas pastas ao lado desta. Isso resolve o caso em que o Python da
rem    Microsoft Store funciona dentro do app antigo, mas nao pelo comando python.
for /d %%D in ("%~dp0..\*") do (
  if /I not "%%~fD"=="%CD%" (
    if exist "%%~fD\.venv_v4\Scripts\python.exe" (
      "%%~fD\.venv_v4\Scripts\python.exe" -c "import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)" >nul 2>nul
      if not errorlevel 1 (
        set "BASEPY_EXE=%%~fD\.venv_v4\Scripts\python.exe"
        goto :create_from_exe
      )
    )
    if exist "%%~fD\.venv_v3\Scripts\python.exe" (
      "%%~fD\.venv_v3\Scripts\python.exe" -c "import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)" >nul 2>nul
      if not errorlevel 1 (
        set "BASEPY_EXE=%%~fD\.venv_v3\Scripts\python.exe"
        goto :create_from_exe
      )
    )
    if exist "%%~fD\.venv\Scripts\python.exe" (
      "%%~fD\.venv\Scripts\python.exe" -c "import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)" >nul 2>nul
      if not errorlevel 1 (
        set "BASEPY_EXE=%%~fD\.venv\Scripts\python.exe"
        goto :create_from_exe
      )
    )
  )
)

rem 6) Faz a mesma busca nas pastas mais comuns, caso esta versao tenha
rem    sido extraida em outro local.
for %%R in ("%USERPROFILE%\Desktop" "%USERPROFILE%\Downloads" "%USERPROFILE%\Documents") do (
  if exist "%%~R" (
    for /d %%D in ("%%~R\*") do (
      if exist "%%~fD\.venv_v4\Scripts\python.exe" (
        "%%~fD\.venv_v4\Scripts\python.exe" -c "import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)" >nul 2>nul
        if not errorlevel 1 (
          set "BASEPY_EXE=%%~fD\.venv_v4\Scripts\python.exe"
          goto :create_from_exe
        )
      )
      if exist "%%~fD\.venv_v3\Scripts\python.exe" (
        "%%~fD\.venv_v3\Scripts\python.exe" -c "import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)" >nul 2>nul
        if not errorlevel 1 (
          set "BASEPY_EXE=%%~fD\.venv_v3\Scripts\python.exe"
          goto :create_from_exe
        )
      )
      if exist "%%~fD\.venv\Scripts\python.exe" (
        "%%~fD\.venv\Scripts\python.exe" -c "import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)" >nul 2>nul
        if not errorlevel 1 (
          set "BASEPY_EXE=%%~fD\.venv\Scripts\python.exe"
          goto :create_from_exe
        )
      )
    )
  )
)

echo.
echo Nao encontrei Python 3.11 ou superior nem um ambiente antigo do AutoExcel.
echo.
echo Se voce ainda tem a versao anterior funcionando, deixe a pasta dela
echo ao lado desta nova pasta e execute INICIAR_APP.bat novamente.
echo.
echo Teste opcional no CMD: python --version
pause
exit /b 1

:create_from_cmd
echo Python funcional encontrado: %BASEPY_CMD%
%BASEPY_CMD% --version
echo.
echo Criando ambiente local...
%BASEPY_CMD% -m venv ".venv_v4"
if errorlevel 1 goto :erro
goto :venv_ok

:create_from_exe
echo Python funcional encontrado em uma instalacao/versao anterior:
echo %BASEPY_EXE%
"%BASEPY_EXE%" --version
echo.
echo Criando ambiente local...
"%BASEPY_EXE%" -m venv ".venv_v4"
if errorlevel 1 goto :erro
goto :venv_ok

:venv_ok
set "VPY=%CD%\.venv_v4\Scripts\python.exe"
if not exist "%VPY%" goto :erro

"%VPY%" -c "import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)" >nul 2>nul
if errorlevel 1 goto :erro

"%VPY%" -c "import streamlit, pandas, ezdxf, openpyxl, webview" >nul 2>nul
if not errorlevel 1 goto :deps_ok

echo.
echo Instalando dependencias do AutoExcel...
echo Na primeira instalacao e necessario acesso a internet.
"%VPY%" -m pip install --upgrade pip
if errorlevel 1 goto :erro
"%VPY%" -m pip install -r requirements.txt
if errorlevel 1 goto :erro

:deps_ok
rem O icone da barra de tarefas vem do executavel principal.
rem Criamos um EXE real com o icone incorporado, enquanto o servidor
rem Streamlit continua usando o ambiente Python local em segundo plano.
if exist "%APP_EXE%" goto :ready

echo.
echo Preparando o executavel do AutoExcel com o icone personalizado...
echo Isso acontece apenas na primeira instalacao e pode levar alguns minutos.

"%VPY%" -c "import PyInstaller" >nul 2>nul
if errorlevel 1 (
  "%VPY%" -m pip install pyinstaller
  if errorlevel 1 goto :erro
)

if not exist ".build" mkdir ".build"
"%VPY%" -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --onefile ^
  --windowed ^
  --name "AutoExcel by AB Alves" ^
  --icon "%CD%\app_icon.ico" ^
  --distpath "%CD%" ^
  --workpath "%CD%\.build\work" ^
  --specpath "%CD%\.build" ^
  --collect-all webview ^
  "%CD%\desktop_launcher.py"
if errorlevel 1 goto :erro

if not exist "%APP_EXE%" goto :erro

:ready
> ".desktop_ready" echo ready

echo.
echo Instalacao pronta.
echo Abrindo AutoExcel by AB Alves...
start "" "%APP_EXE%"
exit /b 0

:erro
echo.
echo Ocorreu um erro durante a instalacao/inicializacao.
echo Envie as ultimas linhas desta janela para diagnostico.
echo.
pause
exit /b 1
