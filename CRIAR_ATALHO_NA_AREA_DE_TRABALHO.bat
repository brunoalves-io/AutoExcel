@echo off
setlocal
cd /d "%~dp0"
set "APP_EXE=%CD%\AutoExcel by AB Alves.exe"

if not exist "%APP_EXE%" (
  echo Primeiro execute INICIAR_APP.bat para criar o executavel do AutoExcel.
  pause
  exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$desktop=[Environment]::GetFolderPath('Desktop');" ^
  "$w=New-Object -ComObject WScript.Shell;" ^
  "$s=$w.CreateShortcut((Join-Path $desktop 'AutoExcel by AB Alves.lnk'));" ^
  "$s.TargetPath='%APP_EXE%';" ^
  "$s.WorkingDirectory='%CD%';" ^
  "$s.Description='AutoExcel by AB Alves';" ^
  "$s.IconLocation='%APP_EXE%,0';" ^
  "$s.Save()"

if errorlevel 1 (
  echo Nao foi possivel criar o atalho automaticamente.
  pause
  exit /b 1
)

echo.
echo Atalho criado na Area de Trabalho com o icone do AutoExcel.
timeout /t 2 >nul
exit /b 0
