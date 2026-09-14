# AutoExcel by AB Alves

Aplicativo desktop para Windows que lê arquivos DXF de loteamentos, identifica quadras, lotes e áreas, valida a numeração e gera automaticamente uma planilha Excel no padrão do projeto.

## Principais recursos

- leitura direta de arquivos `.dxf`;
- suporte a múltiplas quadras;
- associação geométrica de lote, área e quadra;
- validação de numeração contínua dos lotes;
- geração de Excel formatado com totais e agrupamentos;
- execução em modo desktop no Windows;
- processamento local, sem necessidade de API externa.

## Executável único para Windows

A partir da versão `v1.1.0`, o AutoExcel é publicado como um único arquivo:

`AutoExcel-by-AB-Alves.exe`

Esse executável já leva dentro dele o Python, Streamlit, pywebview, pandas, ezdxf, openpyxl e os demais componentes necessários ao aplicativo.

No computador do usuário não é necessário:

- instalar Python;
- instalar bibliotecas;
- executar `pip`;
- extrair ZIP;
- executar arquivo `.bat` de instalação;
- baixar dependências adicionais.

Basta baixar o `.exe` da página **Releases** e executá-lo.

## Arquivos principais do código-fonte

- `app.py` — interface e fluxo principal;
- `dxf_reader.py` — leitura e interpretação do DXF;
- `core.py` — geração e formatação do Excel;
- `desktop_launcher.py` — inicialização da janela e do servidor interno empacotado;
- `requirements.txt` — dependências usadas no build;
- `scripts/build_windows.ps1` — geração do executável standalone;
- `.github/workflows/build-windows.yml` — build e publicação automática no GitHub Actions.

## Build automático

O workflow **Build Windows** compila o aplicativo em um runner Windows usando PyInstaller em modo `onefile`.

Ao terminar, ele publica diretamente o arquivo:

`AutoExcel-by-AB-Alves.exe`

Quando o valor de `RELEASE_VERSION` é alterado para uma nova versão, o GitHub cria automaticamente uma Release e anexa esse executável.

## Autor

AB Alves
