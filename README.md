# Sistema de Impressão e Cadastro de Etiquetas

Aplicação desktop 100% offline (Python + CustomTkinter + SQLite) para cadastrar
itens e imprimir etiquetas diretamente na impressora padrão do sistema
operacional, sem qualquer diálogo de impressão.

## Por que Python + CustomTkinter?

Entre as opções da stack obrigatória, Python foi escolhido por dois motivos:

- **Impressão nativa mais confiável e simples**: no Windows, `pywin32`
  (`win32print`/`win32ui`) fala direto com o driver GDI da impressora padrão.
  No Linux/macOS, o comando `lp` (CUPS) já vem pronto no SO. Em ambos os
  casos o trabalho vai direto ao spooler, sem abrir nenhuma janela — o que é
  bem mais simples e estável do que replicar o mesmo comportamento em
  Electron (que dependeria de `node-printer`/APIs nativas adicionais).
- **Interface amigável e leve**: CustomTkinter dá botões grandes, fontes
  modernas e tema claro/escuro com uma API simples, resultando em um
  executável único e leve (não carrega um Chromium embutido como o Electron).

## Estrutura do projeto

```
ETIQUETA/
├── main.py                  # Ponto de entrada
├── requirements.txt
├── database/
│   └── db.py                # Conexão SQLite + schema + queries
├── printing/
│   └── printer.py           # Geração da imagem da etiqueta + envio ao SO
├── ui/
│   ├── app.py                # Janela principal / navegação entre telas
│   ├── home_screen.py        # Tela inicial (3 botões grandes)
│   ├── register_screen.py    # Tela "Cadastrar Etiqueta" (com exclusão de itens)
│   ├── print_screen.py       # Tela "Imprimir Etiqueta" (com seletor de tamanho)
│   ├── dimensoes_screen.py   # Tela "Gerenciar Dimensões"
│   ├── printer_dialog.py     # Diálogo de seleção de impressora
│   └── widgets.py            # Campo de busca com autocomplete
├── assets/fonts/             # Fontes embutidas (DejaVu Sans) para a etiqueta
└── etiquetas.db               # Criado automaticamente na primeira execução
```

## Esquema do banco de dados (SQLite)

Um único arquivo `etiquetas.db`, criado automaticamente no primeiro start.

```sql
CREATE TABLE itens (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    nome           TEXT NOT NULL UNIQUE COLLATE NOCASE,
    validade_dias  INTEGER NOT NULL CHECK (validade_dias > 0),
    criado_em      TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);
```

- `nome` é único e case-insensitive (`COLLATE NOCASE`) para evitar cadastros
  duplicados como "Arroz" e "arroz".
- `validade_dias` guarda apenas o número de dias; a data de validade real é
  calculada na hora de imprimir (`hoje + validade_dias`), então mudar a data
  do sistema nunca deixa o banco desatualizado.

```sql
CREATE TABLE dimensoes (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    largura_mm         INTEGER NOT NULL CHECK (largura_mm > 0),
    altura_mm          INTEGER NOT NULL CHECK (altura_mm > 0),
    borda_lateral_mm   INTEGER NOT NULL DEFAULT 3 CHECK (borda_lateral_mm >= 0),
    borda_superior_mm  INTEGER NOT NULL DEFAULT 3 CHECK (borda_superior_mm >= 0),
    UNIQUE (largura_mm, altura_mm)
);
```

- Guarda os tamanhos de etiqueta disponíveis para impressão, cada um com sua
  própria margem de segurança (borda lateral e superior, em mm) — a área em
  que o texto nunca deve entrar. A dimensão **60 x 40 mm** (borda 3/3 mm) é
  semeada automaticamente na primeira execução.
- Gerenciada pela tela "Gerenciar Dimensões" (adicionar/excluir, com
  pré-visualização ao vivo); o tamanho escolhido também aparece no painel do
  canto superior direito da tela de impressão.
- Bancos criados antes dessas colunas existirem são migrados automaticamente
  no próximo start (`ALTER TABLE ... ADD COLUMN`, com borda padrão de 3mm).

## Como instalar

Requer **Python 3.10+** instalado.

```bash
cd ETIQUETA
python -m venv .venv

# Linux/macOS
source .venv/bin/activate
# Windows (PowerShell)
.venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

No Linux, o pacote de sistema `tk` precisa estar instalado (fornece a
biblioteca gráfica usada pelo Tkinter/CustomTkinter):

```bash
# Arch/CachyOS
sudo pacman -S tk
# Debian/Ubuntu
sudo apt install python3-tk
```

No Linux/macOS, a impressão usa o comando `lp` (CUPS), que já vem instalado
na grande maioria das distros e no macOS. Verifique se há uma impressora
padrão configurada:

```bash
lpstat -d
```

## Como rodar

```bash
python main.py
```

## Como compilar em um executável único

Usando [PyInstaller](https://pyinstaller.org) (já incluso no
`requirements.txt`):

**Linux/macOS:**
```bash
pyinstaller --onefile --windowed --name EtiquetaApp \
    --add-data "assets:assets" \
    main.py
```

**Windows (PowerShell):**
```powershell
pyinstaller --onefile --windowed --name EtiquetaApp `
    --add-data "assets;assets" `
    main.py
```

O executável final fica em `dist/EtiquetaApp` (ou `dist/EtiquetaApp.exe` no
Windows). Ele cria o arquivo `etiquetas.db` na primeira execução, na mesma
pasta do executável.

> **Nota Windows:** garanta que `pywin32` foi instalado (`pip install
> pywin32`, já incluso no `requirements.txt` para esse SO) antes de compilar,
> senão a impressão falhará ao rodar no Windows.

## Gerando o instalador Windows (.exe)

O projeto inclui um instalador pronto (`installer/setup.iss`, um script do
[Inno Setup](https://jrsoftware.org/isdl.php)) que empacota o app num único
`SistemaDeEtiquetas_Setup.exe`: ele baixa e instala as dependências do
projeto, gera o executável, cria o atalho na Área de Trabalho e no Menu
Iniciar, e registra um desinstalador em "Adicionar ou remover programas".

> **Importante:** a compilação precisa rodar **num computador Windows**
> (PyInstaller empacota para o mesmo SO em que é executado — não é possível
> gerar o `.exe` do Windows a partir do Linux/macOS deste ambiente de
> desenvolvimento).

Num Windows com **Python 3.10+** e o **Inno Setup** instalados, basta:

1. Copiar a pasta do projeto para o Windows (ou clonar o repositório).
2. Dar duplo clique em **`build_installer.bat`** na raiz do projeto (ou
   rodá-lo pelo terminal).

O script faz tudo sozinho, nesta ordem:

1. Cria o ambiente virtual (`.venv`), se ainda não existir.
2. Baixa e instala todas as dependências (`customtkinter`, `Pillow`,
   `pywin32`, `pyinstaller`) via `pip`.
3. Gera `dist/EtiquetaApp.exe` com o PyInstaller (com as fontes já
   embutidas).
4. Compila `installer/setup.iss` com o Inno Setup (`iscc`).

Ao final, o instalador pronto para distribuir fica em:

```
installer/output/SistemaDeEtiquetas_Setup.exe
```

Basta enviar esse único arquivo para o computador do usuário final e
executá-lo: ele mostra um assistente simples (Avançar → Avançar →
Instalar), com uma caixa marcada por padrão para criar o atalho na Área de
Trabalho, e ao final oferece abrir o programa na hora.

Se o Inno Setup não estiver instalado, baixe-o em
https://jrsoftware.org/isdl.php (opção "Inno Setup Compiler", gratuito) e
rode `build_installer.bat` novamente — ou compile manualmente abrindo
`installer/setup.iss` no programa do Inno Setup.

## Fluxo de uso

1. **Tela inicial** → três botões: "Imprimir Etiqueta", "Cadastrar Etiqueta"
   e "Gerenciar Dimensões".
2. **Cadastrar Etiqueta** → informe nome do item e prazo de validade em dias
   → "Salvar Cadastro" → mensagem de sucesso e campos limpos automaticamente.
   À direita, a lista de itens já cadastrados permite excluir qualquer um
   deles (com confirmação antes de apagar).
3. **Gerenciar Dimensões** → informe largura, altura e as bordas (lateral e
   superior, em mm — já vêm pré-preenchidas com 3mm) → uma pré-visualização
   ao vivo, no meio da tela, mostra exatamente como uma etiqueta desse
   tamanho vai ficar antes mesmo de salvar → "Adicionar Dimensão". A lista à
   direita mostra todos os tamanhos cadastrados, cada um com opção de
   excluir.
4. **Imprimir Etiqueta** → no canto superior direito, escolha o tamanho da
   etiqueta (populado a partir da tela "Gerenciar Dimensões") → digite o
   nome do item na busca (sugestões aparecem em tempo real; digitar o nome
   inteiro ou apertar Enter também seleciona, sem precisar clicar) → o
   sistema mostra data/hora de produção e validade calculada → escolha o
   alinhamento do texto (Centralizado / Esquerda / Direita) e o tamanho do
   texto (Pequeno / Médio / Grande — "Grande" preenche a etiqueta ao máximo
   sem nunca cortar) → digite o responsável → informe a quantidade de
   etiquetas → a pré-visualização à
   direita atualiza sozinha a cada mudança, sempre com a mesma imagem que
   vai para a impressora → "Imprimir Etiqueta" → uma janela pede para
   escolher a impressora (lista todas as instaladas no SO, com a padrão
   pré-selecionada) → "Imprimir" → as etiquetas vão direto para a impressora
   escolhida, sem diálogos do sistema operacional.

A fonte do valor de cada campo encolhe automaticamente (e, em último caso,
trunca com reticências) para nunca ultrapassar a borda configurada e sair
cortada ao imprimir — mesmo com nomes longos em etiquetas pequenas.

A etiqueta impressa segue sempre esta ordem:

```
ITEM:        [Nome do Produto]
PRODUÇÃO:    [DD/MM/AAAA - HH:MM]
VALIDADE:    [DD/MM/AAAA]
RESPONSÁVEL: [Nome inserido]
```
