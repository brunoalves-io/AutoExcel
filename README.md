# AutoExcel by AB Alves

Aplicativo desktop para Windows que lê arquivos DXF de loteamentos, identifica quadras, lotes e áreas e gera automaticamente uma planilha Excel formatada.

## Recursos

- leitura direta de arquivos `.dxf`;
- suporte a múltiplas quadras;
- associação geométrica entre lote, área e quadra;
- validação de numeração contínua;
- agrupamento de áreas iguais consecutivas;
- geração de Excel com totais e formatação;
- processamento 100% local;
- executável único para Windows, sem exigir Python ou dependências externas.

## Estrutura do projeto

- `app.py` — interface e fluxo principal;
- `dxf_reader.py` — leitura e interpretação dos arquivos DXF;
- `core.py` — validação, organização dos dados e geração do Excel;
- `desktop_launcher.py` — inicialização da janela desktop e do servidor interno;
- `app_icon.png` — arte oficial usada para gerar o ícone do executável;
- `requirements.txt` — dependências do projeto;
- `scripts/build_windows.ps1` — build do executável standalone;
- `.github/workflows/build-windows.yml` — compilação, teste e publicação automática;
- `RELEASE_VERSION` — versão que será publicada na próxima Release.

## Download

Para usar o programa, não é necessário clonar o repositório nem instalar dependências.

Baixe o `.exe` mais recente na seção **Releases** do GitHub e execute-o no Windows.

## Build

O GitHub Actions compila o AutoExcel com PyInstaller em modo `onefile`, incorpora as dependências e gera um único executável para Windows.

Quando `RELEASE_VERSION` recebe uma versão ainda não publicada, o workflow cria automaticamente uma nova Release e anexa o `.exe` correspondente.

## Autor

AB Alves
