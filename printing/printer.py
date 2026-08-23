"""
Geração e envio da etiqueta diretamente para a impressora escolhida pelo
usuário (ou a padrão do sistema), sem abrir nenhuma janela de impressão do
navegador/SO.

Estratégia:
  1. A etiqueta é desenhada como uma imagem (Pillow) no tamanho físico (mm)
     escolhido pelo usuário.
  2. Windows -> enviada via GDI (win32print/win32ui), direto ao driver.
  3. Linux/macOS -> enviada via CUPS (comando `lp`), direto ao spooler.

Em ambos os casos não existe diálogo de impressão do SO: o trabalho vai
silenciosamente para a impressora escolhida na tela de impressão do app.
"""
import platform
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# Resolução da etiqueta gerada: pixels por milímetro.
PX_POR_MM = 12

# Multiplicador do tamanho-base da fonte para cada opção do menu "Tamanho do
# Texto". "grande" começa propositalmente enorme -- o ajuste automático de
# encolhimento (mesmo usado para não cortar nomes compridos) sempre reduz até
# o maior tamanho que ainda cabe com segurança, então "grande" acaba
# preenchendo a etiqueta sem nunca ultrapassar a borda.
TAMANHOS_TEXTO = {
    "pequeno": 1.0,
    "medio": 1.35,
    "grande": 2.3,
}

if getattr(sys, "frozen", False):
    # Empacotado com PyInstaller (--add-data): os arquivos de assets ficam
    # extraídos em sys._MEIPASS, não ao lado de __file__.
    FONT_DIR = Path(sys._MEIPASS) / "assets" / "fonts"
else:
    FONT_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"


def _carregar_fonte(tamanho: int, negrito: bool = False) -> ImageFont.FreeTypeFont:
    """Carrega a fonte embutida no projeto (funciona igual em qualquer SO)."""
    nome_arquivo = "DejaVuSans-Bold.ttf" if negrito else "DejaVuSans.ttf"
    caminho = FONT_DIR / nome_arquivo
    if caminho.exists():
        return ImageFont.truetype(str(caminho), max(tamanho, 8))
    return ImageFont.load_default()


def _fonte_ajustada(
    draw: ImageDraw.ImageDraw,
    texto: str,
    tamanho_inicial: int,
    largura_max: float,
    negrito: bool = False,
) -> tuple[ImageFont.FreeTypeFont, str]:
    """Escolhe a maior fonte (até `tamanho_inicial`) que faz `texto` caber em
    `largura_max` px. Se mesmo no tamanho mínimo não couber, trunca o texto
    com reticências -- garante que nada seja cortado ao imprimir."""
    tamanho_min = max(8, round(tamanho_inicial * 0.5))
    tamanho = tamanho_inicial
    while tamanho > tamanho_min:
        fonte = _carregar_fonte(tamanho, negrito)
        if draw.textlength(texto, font=fonte) <= largura_max:
            return fonte, texto
        tamanho -= 1

    fonte = _carregar_fonte(tamanho_min, negrito)
    if draw.textlength(texto, font=fonte) <= largura_max:
        return fonte, texto

    truncado = texto
    while len(truncado) > 1 and draw.textlength(truncado + "…", font=fonte) > largura_max:
        truncado = truncado[:-1]
    return fonte, (truncado + "…" if truncado != texto else texto)


def _altura_texto(draw: ImageDraw.ImageDraw, texto: str, fonte: ImageFont.FreeTypeFont) -> int:
    bbox = draw.textbbox((0, 0), texto, font=fonte)
    return bbox[3] - bbox[1]


def _posicionar_x(alinhamento: str, largura_px: int, margem: int, largura_texto: float) -> float:
    if alinhamento == "esquerda":
        return margem
    if alinhamento == "direita":
        return largura_px - margem - largura_texto
    return (largura_px - largura_texto) / 2  # "centro" (padrão)


def _montar_blocos(
    draw: ImageDraw.ImageDraw,
    linhas: list[tuple[str, str]],
    tamanho_rotulo: int,
    tamanho_valor: int,
    largura_util: float,
    espaco_rotulo_valor: int,
    espaco_entre_blocos: int,
) -> tuple[list, int]:
    """Monta cada bloco (rótulo + valor, já com a fonte do valor ajustada
    para caber na largura útil) e retorna também a altura total ocupada."""
    blocos = []
    altura_total = 0
    for rotulo, valor in linhas:
        fonte_rotulo = _carregar_fonte(tamanho_rotulo, negrito=True)
        fonte_valor, valor_final = _fonte_ajustada(draw, valor, tamanho_valor, largura_util)
        altura_rotulo = _altura_texto(draw, rotulo, fonte_rotulo)
        altura_valor = _altura_texto(draw, valor_final, fonte_valor)
        blocos.append((rotulo, fonte_rotulo, altura_rotulo, valor_final, fonte_valor, altura_valor))
        altura_total += altura_rotulo + espaco_rotulo_valor + altura_valor
    altura_total += espaco_entre_blocos * (len(blocos) - 1)
    return blocos, altura_total


def gerar_imagem_etiqueta(
    nome_item: str,
    producao: datetime,
    validade: datetime,
    responsavel: str,
    largura_mm: int = 60,
    altura_mm: int = 40,
    borda_lateral_mm: float = 3,
    borda_superior_mm: float = 3,
    alinhamento: str = "centro",
    tamanho_texto: str = "pequeno",
) -> Image.Image:
    """Monta a imagem da etiqueta na ordem exigida: ITEM, PRODUÇÃO, VALIDADE,
    RESPONSÁVEL. `alinhamento` é "centro", "esquerda" ou "direita".
    `tamanho_texto` é "pequeno", "medio" ou "grande" (menu de tamanho do
    texto na tela de impressão). `borda_lateral_mm`/`borda_superior_mm`
    definem a margem de segurança em que o texto nunca deve entrar. A fonte
    do valor encolhe automaticamente (na largura e, se preciso, na altura
    também) para nunca ultrapassar essas margens e sair cortada ao imprimir
    -- inclusive quando "grande" pede mais espaço do que a etiqueta tem."""
    largura_px = largura_mm * PX_POR_MM
    altura_px = altura_mm * PX_POR_MM

    # Escala de referência: o layout original foi desenhado para 800x500px
    # (~66x40mm). Mantemos a mesma proporção visual para qualquer tamanho.
    escala = min(largura_px / 800, altura_px / 500)

    img = Image.new("RGB", (largura_px, altura_px), "white")
    draw = ImageDraw.Draw(img)

    margem_lateral = max(2, round(borda_lateral_mm * PX_POR_MM))
    margem_superior = max(2, round(borda_superior_mm * PX_POR_MM))
    largura_util = max(20, largura_px - 2 * margem_lateral)
    altura_disponivel = max(20, altura_px - 2 * margem_superior)

    multiplicador = TAMANHOS_TEXTO.get(tamanho_texto, 1.0)
    tamanho_rotulo = max(8, round(24 * escala * multiplicador))
    tamanho_valor = max(10, round(32 * escala * multiplicador))
    espaco_rotulo_valor = max(2, round(8 * escala))
    espaco_entre_blocos = max(6, round(20 * escala))

    linhas = [
        ("ITEM:", nome_item.upper()),
        ("PRODUÇÃO:", producao.strftime("%d/%m/%Y")),
        ("VALIDADE:", validade.strftime("%d/%m/%Y")),
        ("RESPONSÁVEL:", responsavel.upper()),
    ]

    # Encolhe as fontes progressivamente até o bloco inteiro caber na altura
    # disponível (respeitando a borda superior) -- garante que a etiqueta
    # nunca saia cortada verticalmente, mesmo com bordas grandes ou etiquetas
    # bem pequenas.
    for _tentativa in range(6):
        blocos, altura_total = _montar_blocos(
            draw, linhas, tamanho_rotulo, tamanho_valor, largura_util,
            espaco_rotulo_valor, espaco_entre_blocos,
        )
        if altura_total <= altura_disponivel or tamanho_valor <= 8:
            break
        fator = max(0.6, altura_disponivel / altura_total)
        tamanho_rotulo = max(6, round(tamanho_rotulo * fator))
        tamanho_valor = max(8, round(tamanho_valor * fator))

    y = max(margem_superior, (altura_px - altura_total) // 2)

    for rotulo, fonte_rotulo, altura_rotulo, valor_final, fonte_valor, altura_valor in blocos:
        largura_rotulo = draw.textlength(rotulo, font=fonte_rotulo)
        x_rotulo = _posicionar_x(alinhamento, largura_px, margem_lateral, largura_rotulo)
        draw.text((x_rotulo, y), rotulo, font=fonte_rotulo, fill="black")
        y += altura_rotulo + espaco_rotulo_valor

        largura_valor = draw.textlength(valor_final, font=fonte_valor)
        x_valor = _posicionar_x(alinhamento, largura_px, margem_lateral, largura_valor)
        draw.text((x_valor, y), valor_final, font=fonte_valor, fill="black")
        y += altura_valor + espaco_entre_blocos

    borda = max(2, round(3 * escala))
    margem_borda = max(2, round(6 * escala))
    draw.rectangle(
        [(margem_borda, margem_borda), (largura_px - margem_borda, altura_px - margem_borda)],
        outline="black",
        width=borda,
    )
    return img


def imprimir_etiqueta(
    nome_item: str,
    producao: datetime,
    validade: datetime,
    responsavel: str,
    largura_mm: int = 60,
    altura_mm: int = 40,
    borda_lateral_mm: float = 3,
    borda_superior_mm: float = 3,
    alinhamento: str = "centro",
    tamanho_texto: str = "pequeno",
    impressora: str | None = None,
    copias: int = 1,
) -> None:
    """Ponto de entrada único: gera a imagem e despacha para o SO correto.
    `impressora` é o nome escolhido pelo usuário; None = impressora padrão do SO.
    `copias` é a quantidade de etiquetas idênticas a imprimir."""
    imagem = gerar_imagem_etiqueta(
        nome_item, producao, validade, responsavel,
        largura_mm, altura_mm, borda_lateral_mm, borda_superior_mm, alinhamento,
        tamanho_texto,
    )
    sistema = platform.system()
    copias = max(1, copias)

    if sistema == "Windows":
        _imprimir_windows(imagem, impressora, copias, largura_mm, altura_mm)
    else:
        _imprimir_unix(imagem, impressora, largura_mm, altura_mm, copias)


def _ajustar_tamanho_papel(nome_impressora: str, largura_mm: float, altura_mm: float) -> None:
    """Tenta ajustar o tamanho de papel salvo na impressora para bater com a
    etiqueta física (ex.: Zebra ZD230 configurada para um tamanho de página
    diferente do 60x40mm real da etiqueta carregada).

    Isto é só uma tentativa: fica tudo dentro de um único try/except que
    cobre literalmente tudo, então qualquer falha aqui (driver que recusa,
    permissão insuficiente, impressora sem DEVMODE, etc.) é apenas ignorada
    silenciosamente -- a impressão em si, chamada logo depois desta função,
    nunca depende do resultado deste ajuste."""
    try:
        import win32con
        import win32print

        handle = win32print.OpenPrinter(nome_impressora)
        try:
            info = win32print.GetPrinter(handle, 2)
            devmode = info["pDevMode"]
            if devmode is None:
                return
            devmode.PaperSize = 0  # 0 = usar PaperWidth/PaperLength customizados
            devmode.PaperWidth = round(largura_mm * 10)  # décimos de mm
            devmode.PaperLength = round(altura_mm * 10)
            devmode.Fields |= (
                win32con.DM_PAPERSIZE | win32con.DM_PAPERWIDTH | win32con.DM_PAPERLENGTH
            )
            info["pDevMode"] = devmode
            win32print.SetPrinter(handle, 2, info, 0)
        finally:
            win32print.ClosePrinter(handle)
    except Exception:
        pass


def _imprimir_windows(
    imagem: Image.Image,
    impressora: str | None = None,
    copias: int = 1,
    largura_mm: float | None = None,
    altura_mm: float | None = None,
) -> None:
    """Envia a imagem via GDI direto para a impressora escolhida (sem diálogo).

    Impressoras térmicas de etiqueta (ex.: Zebra ZD230) guardam no driver o
    último tamanho de página que foi usado -- que não necessariamente bate
    com a etiqueta física carregada (60x40mm, por exemplo). Antes desta
    correção, o código só lia esse tamanho salvo (GetDeviceCaps) e escalava a
    imagem para caber nele; se o driver estivesse configurado para outro
    tamanho de papel, a etiqueta saía com a proporção/tamanho errados.

    Por isso, quando `largura_mm`/`altura_mm` são informados, tentamos, como
    um passo à parte e totalmente isolado, ajustar o tamanho de papel salvo
    na impressora para bater com a etiqueta física antes de abrir a conexão
    de impressão. Se esse ajuste falhar por qualquer motivo (driver que não
    aceita, permissão insuficiente, etc.), ele é simplesmente ignorado -- a
    impressão em si sempre segue pelo mesmo caminho testado e comprovado,
    nunca é interrompida por causa disso.
    """
    import win32print
    import win32ui
    from PIL import ImageWin

    nome_impressora = impressora or win32print.GetDefaultPrinter()

    if largura_mm and altura_mm:
        _ajustar_tamanho_papel(nome_impressora, largura_mm, altura_mm)

    hDC = win32ui.CreateDC()
    hDC.CreatePrinterDC(nome_impressora)

    HORZRES, VERTRES = 8, 10  # índices GetDeviceCaps para área imprimível
    largura_pagina = hDC.GetDeviceCaps(HORZRES)
    altura_pagina = hDC.GetDeviceCaps(VERTRES)

    proporcao = min(largura_pagina / imagem.width, altura_pagina / imagem.height)
    largura_final = int(imagem.width * proporcao)
    altura_final = int(imagem.height * proporcao)

    dib = ImageWin.Dib(imagem)
    hDC.StartDoc("Etiqueta")
    for _ in range(copias):
        hDC.StartPage()
        dib.draw(hDC.GetHandleOutput(), (0, 0, largura_final, altura_final))
        hDC.EndPage()
    hDC.EndDoc()
    hDC.DeleteDC()


def _imprimir_unix(
    imagem: Image.Image,
    impressora: str | None = None,
    largura_mm: int | None = None,
    altura_mm: int | None = None,
    copias: int = 1,
) -> None:
    """Envia a imagem para o CUPS via comando `lp`, na impressora escolhida."""
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        caminho_tmp = tmp.name
    imagem.save(caminho_tmp, "PNG")

    cmd_base = ["lp"]
    if impressora:
        cmd_base += ["-d", impressora]
    if copias > 1:
        cmd_base += ["-n", str(copias)]

    try:
        cmd = cmd_base + [caminho_tmp]
        if largura_mm and altura_mm:
            cmd = cmd_base + ["-o", f"media=Custom.{largura_mm}x{altura_mm}mm", caminho_tmp]
        subprocess.run(cmd, check=True, capture_output=True)
    except subprocess.CalledProcessError:
        # Nem toda impressora aceita tamanho de mídia customizado; tenta de
        # novo com as opções padrão dela antes de desistir.
        subprocess.run(cmd_base + [caminho_tmp], check=True, capture_output=True)
    finally:
        Path(caminho_tmp).unlink(missing_ok=True)


def listar_impressoras() -> list[str]:
    """Lista os nomes das impressoras instaladas no SO."""
    if platform.system() == "Windows":
        import win32print

        flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
        return [info[2] for info in win32print.EnumPrinters(flags)]

    try:
        saida = subprocess.run(
            ["lpstat", "-p"], capture_output=True, text=True, check=True
        ).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []

    nomes = []
    for linha in saida.splitlines():
        if linha.startswith("printer "):
            nomes.append(linha.split()[1])
    return nomes


def obter_impressora_padrao() -> str | None:
    """Retorna o nome da impressora padrão configurada no SO, se houver."""
    if platform.system() == "Windows":
        import win32print

        try:
            return win32print.GetDefaultPrinter()
        except Exception:
            return None

    try:
        saida = subprocess.run(
            ["lpstat", "-d"], capture_output=True, text=True, check=True
        ).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None

    if ":" in saida:
        nome = saida.split(":", 1)[1].strip()
        return nome or None
    return None
