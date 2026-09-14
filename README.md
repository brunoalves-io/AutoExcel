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
- `INICIAR_APP.bat` — instalação e inicialização no Windows.

## Autor

AB Alves
