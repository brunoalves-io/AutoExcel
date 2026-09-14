# AutoExcel by AB Alves

Aplicativo desktop para Windows que lê arquivos DXF de loteamentos, identifica quadras, lotes e áreas, valida a numeração e gera automaticamente uma planilha Excel no padrão do projeto.

## Principais recursos

- leitura direta de arquivos `.dxf`;
- suporte a múltiplas quadras;
- associação geométrica de lote, área e quadra;
- validação de numeração contínua dos lotes;
- geração de Excel formatado com totais e agrupamentos;
- execução em modo desktop no Windows;
- funcionamento local, sem necessidade de API externa.

## Arquivos principais

- `app.py` — interface e fluxo principal;
- `dxf_reader.py` — leitura e interpretação do DXF;
- `core.py` — geração e formatação do Excel;
- `desktop_launcher.py` — inicialização da janela desktop;
- `requirements.txt` — dependências Python;
- `INICIAR_APP.bat` — instalação e inicialização no Windows;
- `scripts/build_windows.ps1` — geração do executável e pacote Windows;
- `.github/workflows/build-windows.yml` — automação do build no GitHub Actions.

## Build automático para Windows

O repositório possui um workflow do GitHub Actions chamado **Build Windows**.

Ele é executado automaticamente quando alterações relevantes chegam à branch `main` e também pode ser iniciado manualmente em **Actions → Build Windows → Run workflow**.

Ao terminar, o workflow publica o artefato:

`AutoExcel-by-AB-Alves-Windows.zip`

O pacote contém o executável **AutoExcel by AB Alves.exe**, os arquivos necessários do aplicativo e o instalador de primeira execução.

### Criar uma versão oficial

Ao criar e enviar uma tag no formato `v*`, por exemplo `v1.0.0`, o mesmo workflow também cria automaticamente uma **GitHub Release** e anexa o pacote Windows à versão.

## Autor

AB Alves
