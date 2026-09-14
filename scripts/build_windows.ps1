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
python -m pip install pyinstaller pillow

# Traduz diretamente o texto nativo do frontend do Streamlit usado pelo
# file_uploader. Isso evita depender de seletores CSS internos, que podem
# mudar entre versoes do Streamlit.
Write-Host "Traduzindo texto nativo do uploader do Streamlit..."
$translateUploaderScript = @'
from pathlib import Path
import streamlit
import sys

static_dir = Path(streamlit.__file__).resolve().parent / "static"
if not static_dir.exists():
    raise SystemExit(f"Diretorio static do Streamlit nao encontrado: {static_dir}")

needle = " per file"
replacement = " por arquivo"
occurrences = 0
changed_files = []

for path in static_dir.rglob("*.js"):
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        continue
    count = text.count(needle)
    if count:
        path.write_text(text.replace(needle, replacement), encoding="utf-8")
        occurrences += count
        changed_files.append(str(path))

print(f"Ocorrencias traduzidas: {occurrences}")
for path in changed_files:
    print(f"  - {path}")

if occurrences == 0:
    raise SystemExit("Nao foi encontrada a string nativa ' per file' no frontend do Streamlit")
'@
$translateUploaderScript | python -
if ($LASTEXITCODE -ne 0) {
    throw "Falha ao traduzir o texto nativo do uploader do Streamlit"
}

$version = (Get-Content (Join-Path $repoRoot "RELEASE_VERSION") -Raw).Trim()
if ([string]::IsNullOrWhiteSpace($version)) {
    throw "RELEASE_VERSION esta vazio"
}
if (-not $version.StartsWith("v")) {
    $version = "v$version"
}

$buildDir = Join-Path $repoRoot "build"
$distDir = Join-Path $repoRoot "dist"
$releaseDir = Join-Path $repoRoot "release"
$releaseExe = Join-Path $releaseDir ("AutoExcel-by-AB-Alves-{0}.exe" -f $version)

foreach ($path in @($buildDir, $distDir, $releaseDir)) {
    if (Test-Path $path) {
        Remove-Item $path -Recurse -Force
    }
}

New-Item -ItemType Directory -Force -Path $buildDir | Out-Null
New-Item -ItemType Directory -Force -Path $distDir | Out-Null
New-Item -ItemType Directory -Force -Path $releaseDir | Out-Null

# Gera um ICO Windows real, multi-resolucao, a partir da arte oficial.
# Evita depender da conversao automatica de PNG do PyInstaller, que pode
# resultar em icone generico/branco no Explorer em algumas versoes do Windows.
$sourcePng = Join-Path $repoRoot "app_icon.png"
$windowsIco = Join-Path $buildDir "app_icon_windows.ico"
$iconScript = @'
from PIL import Image
from pathlib import Path
import sys

src = Path(sys.argv[1])
out = Path(sys.argv[2])
img = Image.open(src).convert("RGBA")

canvas = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
img.thumbnail((240, 240), Image.Resampling.LANCZOS)
x = (256 - img.width) // 2
y = (256 - img.height) // 2
canvas.alpha_composite(img, (x, y))

sizes = [(16,16), (20,20), (24,24), (32,32), (40,40), (48,48), (64,64), (96,96), (128,128), (256,256)]
canvas.save(out, format="ICO", sizes=sizes)
print(f"ICO criado: {out} ({out.stat().st_size} bytes)")
'@
$iconScript | python - $sourcePng $windowsIco
if ($LASTEXITCODE -ne 0 -or -not (Test-Path $windowsIco)) {
    throw "Falha ao gerar o icone Windows multi-resolucao"
}
if ((Get-Item $windowsIco).Length -lt 20000) {
    throw "ICO Windows gerado parece invalido ou incompleto"
}

Write-Host "Gerando executavel totalmente independente com ICO Windows multi-resolucao..."

$pyInstallerArgs = @(
    "--noconfirm",
    "--clean",
    "--onefile",
    "--windowed",
    "--name", "AutoExcel by AB Alves",
    "--icon", $windowsIco,
    "--distpath", $distDir,
    "--workpath", (Join-Path $buildDir "pyinstaller"),
    "--specpath", (Join-Path $buildDir "spec"),
    "--add-data", ((Join-Path $repoRoot "app.py") + ";."),
    "--add-data", ((Join-Path $repoRoot "app_icon.png") + ";."),
    "--hidden-import", "core",
    "--hidden-import", "dxf_reader",
    "--hidden-import", "pandas",
    "--hidden-import", "openpyxl",
    "--collect-all", "streamlit",
    "--collect-all", "webview",
    (Join-Path $repoRoot "desktop_launcher.py")
)

python -m PyInstaller @pyInstallerArgs
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller falhou com codigo $LASTEXITCODE"
}

$exePath = Join-Path $distDir "AutoExcel by AB Alves.exe"
if (-not (Test-Path $exePath)) {
    throw "O executavel nao foi criado: $exePath"
}

$exeInfo = Get-Item $exePath
if ($exeInfo.Length -lt 5MB) {
    throw "O executavel gerado parece incompleto: $($exeInfo.Length) bytes"
}

Copy-Item $exePath -Destination $releaseExe -Force

if (-not (Test-Path $releaseExe)) {
    throw "O executavel final nao foi criado: $releaseExe"
}

Write-Host "Build concluido. Nenhum Python, ZIP ou dependencia externa sera necessario no computador do usuario:"
Get-Item $releaseExe | Format-List Name,Length,FullName
