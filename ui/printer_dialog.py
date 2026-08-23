"""Janela modal para escolher a impressora antes de enviar a etiqueta."""
from typing import Callable

import customtkinter as ctk

from printing.printer import listar_impressoras, obter_impressora_padrao


class SeletorImpressora(ctk.CTkToplevel):
    def __init__(self, master, ao_confirmar: Callable[[str | None], None]):
        super().__init__(master)
        self.ao_confirmar = ao_confirmar

        self.title("Selecionar Impressora")
        self.geometry("420x460")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        ctk.CTkLabel(
            self, text="Escolha a impressora", font=ctk.CTkFont(size=22, weight="bold")
        ).pack(pady=(25, 15))

        impressoras = listar_impressoras()
        padrao = obter_impressora_padrao()
        valor_inicial = padrao if padrao in impressoras else (impressoras[0] if impressoras else "")
        self.selecionada = ctk.StringVar(value=valor_inicial)

        if impressoras:
            lista = ctk.CTkScrollableFrame(self, width=360, height=250)
            lista.pack(padx=20, pady=(0, 20), fill="both", expand=True)
            for nome in impressoras:
                texto = f"{nome}  (padrão)" if nome == padrao else nome
                ctk.CTkRadioButton(
                    lista,
                    text=texto,
                    variable=self.selecionada,
                    value=nome,
                    font=ctk.CTkFont(size=15),
                ).pack(anchor="w", pady=8, padx=10)
        else:
            ctk.CTkLabel(
                self,
                text=(
                    "Nenhuma impressora encontrada.\n"
                    "Será usada a impressora padrão do sistema, se houver."
                ),
                font=ctk.CTkFont(size=14),
                text_color="gray30",
                justify="center",
                wraplength=360,
            ).pack(padx=20, pady=(0, 20), fill="both", expand=True)

        botoes = ctk.CTkFrame(self, fg_color="transparent")
        botoes.pack(pady=(0, 20))
        ctk.CTkButton(
            botoes,
            text="Cancelar",
            width=140,
            height=45,
            fg_color="gray40",
            hover_color="gray30",
            command=self.destroy,
        ).pack(side="left", padx=8)
        ctk.CTkButton(
            botoes,
            text="🖨  Imprimir",
            width=180,
            height=45,
            font=ctk.CTkFont(size=16, weight="bold"),
            command=self._confirmar,
        ).pack(side="left", padx=8)

    def _confirmar(self) -> None:
        nome = self.selecionada.get() or None
        self.destroy()
        self.ao_confirmar(nome)
