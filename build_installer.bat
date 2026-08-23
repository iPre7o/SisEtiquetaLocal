@echo off
setlocal enabledelayedexpansion

echo ================================================
echo   Sistema de Etiquetas - Gerador do Instalador
echo ================================================
echo.
echo Este script deve ser executado no WINDOWS, a partir da
echo raiz do projeto (a pasta onde estao main.py e requirements.txt).
echo.

REM --- 1. Verifica se o Python esta instalado -------------------------
where python >nul 2>nul
if errorlevel 1 (
    echo [ERRO] Python nao encontrado no PATH.
    echo Baixe e instale o Python 3.10+ em https://www.python.org/downloads/
    echo Marque a opcao "Add python.exe to PATH" durante a instalacao.
    pause
    exit /b 1
)

REM --- 2. Cria o ambiente virtual, se ainda nao existir ---------------
if not exist ".venv" (
    echo Criando ambiente virtual em .venv ...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERRO] Falha ao criar o ambiente virtual.
        pause
        exit /b 1
    )
)

REM Usamos sempre o python.exe de dentro do .venv pelo caminho completo, em
REM vez de "activate.bat" + comandos soltos (pip, pyinstaller). Isso evita o
REM erro comum "'pyinstaller' nao e reconhecido como um comando interno",
REM que acontece quando a pasta .venv\Scripts nao entra no PATH da sessao.
set "PYEXE=.venv\Scripts\python.exe"

if not exist "%PYEXE%" (
    echo [ERRO] Nao encontrei %PYEXE%.
    echo O ambiente virtual pode ter sido criado incompleto. Apague a pasta
    echo .venv e rode este script novamente.
    pause
    exit /b 1
)

REM --- 3. Baixa e instala todas as dependencias (PyPI) ----------------
echo.
echo Baixando e instalando as dependencias do projeto...
"%PYEXE%" -m pip install --upgrade pip
"%PYEXE%" -m pip install -r requirements.txt
if errorlevel 1 (
    echo [ERRO] Falha ao instalar as dependencias. Verifique sua conexao com a internet.
    pause
    exit /b 1
)

REM --- 4. Gera o executavel standalone com o PyInstaller --------------
echo.
echo Gerando o executavel (EtiquetaApp.exe) com o PyInstaller...
"%PYEXE%" -m PyInstaller --noconfirm --onefile --windowed --name EtiquetaApp --add-data "assets;assets" main.py
if errorlevel 1 (
    echo [ERRO] Falha ao gerar o executavel com o PyInstaller.
    pause
    exit /b 1
)

REM --- 5. Compila o instalador com o Inno Setup ------------------------
echo.

REM O instalador do Inno Setup normalmente NAO adiciona o iscc.exe ao PATH
REM do Windows, entao primeiro tentamos o PATH e, se nao achar, procuramos
REM nos dois locais padrao de instalacao (32 e 64 bits).
set "ISCC="
where iscc >nul 2>nul
if not errorlevel 1 (
    set "ISCC=iscc"
) else if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" (
    set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
) else if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" (
    set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
)

if not defined ISCC (
    echo [AVISO] Inno Setup (ISCC) nao encontrado.
    echo Baixe e instale em: https://jrsoftware.org/isdl.php
    echo Depois rode este script novamente, ou compile manualmente: de
    echo duplo clique em installer\setup.iss para abrir no Inno Setup
    echo Compiler e clique no botao "Compile" (ou aperte Ctrl+F9).
    echo.
    echo O executavel do app ja foi gerado em: dist\EtiquetaApp.exe
    pause
    exit /b 1
)

echo Compilando o instalador com o Inno Setup...
"%ISCC%" installer\setup.iss
if errorlevel 1 (
    echo [ERRO] Falha ao compilar o instalador.
    pause
    exit /b 1
)

echo.
echo ================================================
echo   Pronto!
echo   Instalador gerado em:
echo   installer\output\SistemaDeEtiquetas_Setup.exe
echo ================================================
pause
