$ErrorActionPreference = "Stop"

Write-Host "==========================================="
Write-Host " AutoExcel by AB Alves - Standalone Build"
Write-Host "==========================================="

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

Write-Host "Python:"
python --version

Write-Host "Atualizando pip..."
python -m pip install --upgrade pip

Write-Host "Instalando dependencias..."
python -m pip install -r requirements.txt
python -m pip install pyinstaller

$buildDir = Join-Path $repoRoot "build"
$distDir = Join-Path $repoRoot "dist"
$releaseDir = Join-Path $repoRoot "release"
$releaseExe = Join-Path $releaseDir "AutoExcel-by-AB-Alves.exe"

foreach ($path in @($buildDir, $distDir, $releaseDir)) {
    if (Test-Path $path) {
        Remove-Item $path -Recurse -Force
    }
}

New-Item -ItemType Directory -Force -Path $buildDir | Out-Null
New-Item -ItemType Directory -Force -Path $distDir | Out-Null
New-Item -ItemType Directory -Force -Path $releaseDir | Out-Null

Write-Host "Gerando executavel totalmente independente..."
$pyInstallerArgs = @(
    "--noconfirm",
    "--clean",
    "--onefile",
    "--windowed",
    "--name", "AutoExcel by AB Alves",
    "--icon", (Join-Path $repoRoot "app_icon.ico"),
    "--distpath", $distDir,
    "--workpath", (Join-Path $buildDir "pyinstaller"),
    "--specpath", (Join-Path $buildDir "spec"),
    "--add-data", ((Join-Path $repoRoot "app.py") + ";."),
    "--add-data", ((Join-Path $repoRoot "app_icon.ico") + ";."),
    "--hidden-import", "core",
    "--hidden-import", "dxf_reader",
    "--hidden-import", "pandas",
    "--hidden-import", "openpyxl",
    "--collect-all", "streamlit",
    "--collect-all", "webview",
    (Join-Path $repoRoot "desktop_launcher.py")
)
python -m PyInstaller @pyInstallerArgs

$exePath = Join-Path $distDir "AutoExcel by AB Alves.exe"
if (-not (Test-Path $exePath)) {
    throw "O executavel nao foi criado: $exePath"
}

Copy-Item $exePath -Destination $releaseExe -Force

if (-not (Test-Path $releaseExe)) {
    throw "O executavel final nao foi criado: $releaseExe"
}

Write-Host "Build concluido. Nenhum Python, ZIP ou dependência externa será necessário no computador do usuário:"
Get-Item $releaseExe | Format-List Name,Length,FullName
