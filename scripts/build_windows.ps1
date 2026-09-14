$ErrorActionPreference = "Stop"

Write-Host "==========================================="
Write-Host " AutoExcel by AB Alves - Build Windows"
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
$bundleDir = Join-Path $releaseDir "AutoExcel-by-AB-Alves-Windows"
$zipPath = Join-Path $releaseDir "AutoExcel-by-AB-Alves-Windows.zip"

foreach ($path in @($buildDir, $distDir, $releaseDir)) {
    if (Test-Path $path) {
        Remove-Item $path -Recurse -Force
    }
}

New-Item -ItemType Directory -Force -Path $buildDir | Out-Null
New-Item -ItemType Directory -Force -Path $distDir | Out-Null
New-Item -ItemType Directory -Force -Path $bundleDir | Out-Null

Write-Host "Gerando executavel..."
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
    "--collect-all", "webview",
    (Join-Path $repoRoot "desktop_launcher.py")
)
python -m PyInstaller @pyInstallerArgs

$exePath = Join-Path $distDir "AutoExcel by AB Alves.exe"
if (-not (Test-Path $exePath)) {
    throw "O executavel nao foi criado: $exePath"
}

Write-Host "Montando pacote portatil..."
$filesToCopy = @(
    "app.py",
    "core.py",
    "dxf_reader.py",
    "desktop_launcher.py",
    "requirements.txt",
    "INICIAR_APP.bat",
    "AutoExcel by AB Alves.vbs",
    "CRIAR_ATALHO_NA_AREA_DE_TRABALHO.bat",
    "app_icon.ico",
    "app_icon.png",
    "README.md"
)

Copy-Item $exePath -Destination $bundleDir -Force
foreach ($file in $filesToCopy) {
    $source = Join-Path $repoRoot $file
    if (Test-Path $source) {
        Copy-Item $source -Destination $bundleDir -Force
    }
}

$instructions = @"
AutoExcel by AB Alves - Windows

1. Extraia todos os arquivos desta pasta.
2. Execute INICIAR_APP.bat na primeira vez.
3. Depois, abra pelo arquivo AutoExcel by AB Alves.exe ou crie o atalho da Area de Trabalho.

Observacao: na primeira execucao o instalador configura o ambiente Python local necessario ao servidor Streamlit.
"@
Set-Content -Path (Join-Path $bundleDir "LEIA-ME.txt") -Value $instructions -Encoding UTF8

Write-Host "Compactando pacote..."
Compress-Archive -Path (Join-Path $bundleDir "*") -DestinationPath $zipPath -CompressionLevel Optimal -Force

Write-Host "Build concluido:"
Write-Host $exePath
Write-Host $zipPath
