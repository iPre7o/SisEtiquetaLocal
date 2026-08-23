"""
Camada de acesso ao banco de dados SQLite.
Um único arquivo local (etiquetas.db), sem servidor, sem dependência externa.
"""
import sqlite3
import sys
from pathlib import Path

if getattr(sys, "frozen", False):
    # Empacotado com PyInstaller: __file__ aponta para a pasta temporária de
    # extração, que é apagada a cada execução. sys.executable, em vez disso,
    # é o caminho real do .exe instalado -- é ali que o banco deve morar
    # para os cadastros sobreviverem entre uma abertura e outra do app.
    _DB_DIR = Path(sys.executable).resolve().parent
else:
    _DB_DIR = Path(__file__).resolve().parent.parent

DB_PATH = _DB_DIR / "etiquetas.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Cria as tabelas caso ainda não existam e semeia a dimensão padrão 60x40mm.
    Chamado uma vez no start."""
    conn = get_connection()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS itens (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                nome           TEXT NOT NULL UNIQUE COLLATE NOCASE,
                validade_dias  INTEGER NOT NULL CHECK (validade_dias > 0),
                criado_em      TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS dimensoes (
                id                 INTEGER PRIMARY KEY AUTOINCREMENT,
                largura_mm         INTEGER NOT NULL CHECK (largura_mm > 0),
                altura_mm          INTEGER NOT NULL CHECK (altura_mm > 0),
                borda_lateral_mm   INTEGER NOT NULL DEFAULT 3 CHECK (borda_lateral_mm >= 0),
                borda_superior_mm  INTEGER NOT NULL DEFAULT 3 CHECK (borda_superior_mm >= 0),
                UNIQUE (largura_mm, altura_mm)
            )
            """
        )
        # Migração para bancos criados antes das colunas de borda existirem.
        colunas = {linha["name"] for linha in conn.execute("PRAGMA table_info(dimensoes)")}
        if "borda_lateral_mm" not in colunas:
            conn.execute(
                "ALTER TABLE dimensoes ADD COLUMN borda_lateral_mm INTEGER NOT NULL DEFAULT 3"
            )
        if "borda_superior_mm" not in colunas:
            conn.execute(
                "ALTER TABLE dimensoes ADD COLUMN borda_superior_mm INTEGER NOT NULL DEFAULT 3"
            )
        conn.execute(
            "INSERT OR IGNORE INTO dimensoes (largura_mm, altura_mm) VALUES (60, 40)"
        )
        conn.commit()
    finally:
        conn.close()


def inserir_item(nome: str, validade_dias: int) -> None:
    """Insere um novo item. Lança sqlite3.IntegrityError se o nome já existir."""
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO itens (nome, validade_dias) VALUES (?, ?)",
            (nome.strip(), validade_dias),
        )
        conn.commit()
    finally:
        conn.close()


def buscar_itens(termo: str = "") -> list[sqlite3.Row]:
    """Busca itens cujo nome contenha o termo (case-insensitive). Vazio = todos."""
    conn = get_connection()
    try:
        if termo:
            cursor = conn.execute(
                "SELECT * FROM itens WHERE nome LIKE ? ORDER BY nome ASC",
                (f"%{termo}%",),
            )
        else:
            cursor = conn.execute("SELECT * FROM itens ORDER BY nome ASC")
        return cursor.fetchall()
    finally:
        conn.close()


def excluir_item(item_id: int) -> None:
    """Remove definitivamente um item cadastrado."""
    conn = get_connection()
    try:
        conn.execute("DELETE FROM itens WHERE id = ?", (item_id,))
        conn.commit()
    finally:
        conn.close()


def inserir_dimensao(
    largura_mm: int, altura_mm: int, borda_lateral_mm: int = 3, borda_superior_mm: int = 3
) -> None:
    """Insere um novo tamanho de etiqueta. Lança sqlite3.IntegrityError se já existir."""
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO dimensoes (largura_mm, altura_mm, borda_lateral_mm, borda_superior_mm)
            VALUES (?, ?, ?, ?)
            """,
            (largura_mm, altura_mm, borda_lateral_mm, borda_superior_mm),
        )
        conn.commit()
    finally:
        conn.close()


def buscar_dimensoes() -> list[sqlite3.Row]:
    """Lista todos os tamanhos de etiqueta cadastrados, do menor para o maior."""
    conn = get_connection()
    try:
        cursor = conn.execute("SELECT * FROM dimensoes ORDER BY largura_mm, altura_mm")
        return cursor.fetchall()
    finally:
        conn.close()


def excluir_dimensao(dimensao_id: int) -> None:
    """Remove definitivamente um tamanho de etiqueta."""
    conn = get_connection()
    try:
        conn.execute("DELETE FROM dimensoes WHERE id = ?", (dimensao_id,))
        conn.commit()
    finally:
        conn.close()
