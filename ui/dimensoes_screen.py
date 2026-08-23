"""Tela de gerenciamento dos tamanhos (dimensões) de etiqueta disponíveis,
com pré-visualização ao vivo enquanto o usuário digita."""
import sqlite3
from datetime import datetime, timedelta
from tkinter import messagebox

import customtkinter as ctk

from database.db import buscar_dimensoes, excluir_dimensao, inserir_dimensao
from printing.printer import gerar_imagem_etiqueta

PREVIEW_MAX_LARGURA = 300
PREVIEW_MAX_ALTURA = 260


class DimensoesScreen(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        topo = ctk.CTkFrame(self, fg_color="transparent")
        topo.pack(fill="x", padx=20, pady=20)
        ctk.CTkButton(
            topo,
            text="← Voltar",
            width=120,
            height=40,
            fg_color="gray40",
            hover_color="gray30",
            command=lambda: controller.mostrar_tela("HomeScreen"),
        ).pack(side="left")

        corpo = ctk.CTkFrame(self, fg_color="transparent")
        corpo.pack(fill="both", expand=True, padx=50, pady=(0, 30))
        corpo.grid_columnconfigure(2, weight=1)
        corpo.grid_rowconfigure(0, weight=1)

        # --- coluna 1: formulário para adicionar ------------------------
        form = ctk.CTkFrame(corpo, fg_color="transparent")
        form.grid(row=0, column=0, sticky="n", padx=(0, 30))

        ctk.CTkLabel(
            form, text="Tamanhos de Etiqueta", font=ctk.CTkFont(size=24, weight="bold")
        ).pack(pady=(10, 20), anchor="w")

        ctk.CTkLabel(form, text="Largura (mm):", font=ctk.CTkFont(size=15)).pack(anchor="w")
        self.entry_largura = ctk.CTkEntry(form, width=260, height=42, font=ctk.CTkFont(size=15))
        self.entry_largura.pack(pady=(5, 14))

        ctk.CTkLabel(form, text="Altura (mm):", font=ctk.CTkFont(size=15)).pack(anchor="w")
        self.entry_altura = ctk.CTkEntry(form, width=260, height=42, font=ctk.CTkFont(size=15))
        self.entry_altura.pack(pady=(5, 14))

        ctk.CTkLabel(
            form, text="Borda lateral (mm):", font=ctk.CTkFont(size=15)
        ).pack(anchor="w")
        self.entry_borda_lateral = ctk.CTkEntry(
            form, width=260, height=42, font=ctk.CTkFont(size=15)
        )
        self.entry_borda_lateral.pack(pady=(5, 14))

        ctk.CTkLabel(
            form, text="Borda superior (mm):", font=ctk.CTkFont(size=15)
        ).pack(anchor="w")
        self.entry_borda_superior = ctk.CTkEntry(
            form, width=260, height=42, font=ctk.CTkFont(size=15)
        )
        self.entry_borda_superior.pack(pady=(5, 22))

        for campo in (
            self.entry_largura,
            self.entry_altura,
            self.entry_borda_lateral,
            self.entry_borda_superior,
        ):
            campo.bind("<KeyRelease>", lambda e: self._atualizar_preview())

        ctk.CTkButton(
            form,
            text="➕  Adicionar Dimensão",
            width=260,
            height=55,
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color="#2b7a3d",
            hover_color="#225f30",
            command=self.salvar,
        ).pack()

        self.status_var = ctk.StringVar(value="")
        self.status_label = ctk.CTkLabel(
            form,
            textvariable=self.status_var,
            font=ctk.CTkFont(size=13, weight="bold"),
            wraplength=260,
            justify="left",
        )
        self.status_label.pack(pady=(15, 0), anchor="w")

        # --- coluna 2: pré-visualização ao vivo --------------------------
        preview_container = ctk.CTkFrame(corpo, fg_color=("gray95", "gray17"), corner_radius=10)
        preview_container.grid(row=0, column=1, sticky="n", padx=(0, 30))

        ctk.CTkLabel(
            preview_container, text="Pré-visualização", font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=(16, 10))

        self.preview_label = ctk.CTkLabel(
            preview_container,
            text="Preencha largura e altura\npara ver a etiqueta.",
            font=ctk.CTkFont(size=13),
            text_color="gray50",
            fg_color="white",
            corner_radius=6,
            width=PREVIEW_MAX_LARGURA,
            height=PREVIEW_MAX_ALTURA,
        )
        self.preview_label.pack(padx=18, pady=(0, 18))

        # --- coluna 3: dimensões cadastradas, com exclusão ---------------
        lista_container = ctk.CTkFrame(corpo, fg_color="transparent")
        lista_container.grid(row=0, column=2, sticky="nsew")

        ctk.CTkLabel(
            lista_container,
            text="Dimensões cadastradas",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).pack(anchor="w", pady=(10, 10))

        self.lista_scroll = ctk.CTkScrollableFrame(
            lista_container, fg_color=("gray95", "gray17")
        )
        self.lista_scroll.pack(fill="both", expand=True)

    def ao_exibir(self) -> None:
        self.entry_largura.delete(0, "end")
        self.entry_altura.delete(0, "end")
        self.entry_borda_lateral.delete(0, "end")
        self.entry_borda_lateral.insert(0, "3")
        self.entry_borda_superior.delete(0, "end")
        self.entry_borda_superior.insert(0, "3")
        self.status_var.set("")
        self._atualizar_lista()
        self._atualizar_preview()
        self.entry_largura.focus()

    def _valores_formulario(self) -> tuple[int, int, int, int] | None:
        """Lê e valida os 4 campos numéricos. Retorna None se algo for inválido."""
        textos = (
            self.entry_largura.get().strip(),
            self.entry_altura.get().strip(),
            self.entry_borda_lateral.get().strip(),
            self.entry_borda_superior.get().strip(),
        )
        if not all(t.isdigit() for t in textos):
            return None
        largura, altura, borda_lateral, borda_superior = (int(t) for t in textos)
        if largura <= 0 or altura <= 0:
            return None
        return largura, altura, borda_lateral, borda_superior

    def _atualizar_preview(self) -> None:
        valores = self._valores_formulario()
        if valores is None:
            self.preview_label.configure(
                image=None, text="Preencha largura e altura\npara ver a etiqueta."
            )
            return

        largura_mm, altura_mm, borda_lateral_mm, borda_superior_mm = valores
        agora = datetime.now()
        imagem = gerar_imagem_etiqueta(
            nome_item="ITEM DE EXEMPLO",
            producao=agora,
            validade=agora + timedelta(days=7),
            responsavel="RESPONSÁVEL",
            largura_mm=largura_mm,
            altura_mm=altura_mm,
            borda_lateral_mm=borda_lateral_mm,
            borda_superior_mm=borda_superior_mm,
        )

        escala = min(PREVIEW_MAX_LARGURA / imagem.width, PREVIEW_MAX_ALTURA / imagem.height)
        tamanho_exibicao = (round(imagem.width * escala), round(imagem.height * escala))

        preview_img = ctk.CTkImage(light_image=imagem, dark_image=imagem, size=tamanho_exibicao)
        self.preview_label.configure(image=preview_img, text="")
        self.preview_label.image = preview_img

    def salvar(self) -> None:
        largura_texto = self.entry_largura.get().strip()
        altura_texto = self.entry_altura.get().strip()
        borda_lateral_texto = self.entry_borda_lateral.get().strip()
        borda_superior_texto = self.entry_borda_superior.get().strip()

        if not largura_texto.isdigit() or int(largura_texto) <= 0:
            self._erro("Largura deve ser um número de milímetros maior que zero.")
            return
        if not altura_texto.isdigit() or int(altura_texto) <= 0:
            self._erro("Altura deve ser um número de milímetros maior que zero.")
            return
        if not borda_lateral_texto.isdigit():
            self._erro("Borda lateral deve ser um número de milímetros (0 ou mais).")
            return
        if not borda_superior_texto.isdigit():
            self._erro("Borda superior deve ser um número de milímetros (0 ou mais).")
            return

        try:
            inserir_dimensao(
                int(largura_texto),
                int(altura_texto),
                int(borda_lateral_texto),
                int(borda_superior_texto),
            )
        except sqlite3.IntegrityError:
            self._erro("Essa dimensão já está cadastrada.")
            return

        self.status_label.configure(text_color="#2b7a3d")
        self.status_var.set(f"✔ {largura_texto} x {altura_texto} mm cadastrada com sucesso!")
        self.entry_largura.delete(0, "end")
        self.entry_altura.delete(0, "end")
        self.entry_borda_lateral.delete(0, "end")
        self.entry_borda_lateral.insert(0, "3")
        self.entry_borda_superior.delete(0, "end")
        self.entry_borda_superior.insert(0, "3")
        self.entry_largura.focus()
        self._atualizar_lista()
        self._atualizar_preview()

    def _atualizar_lista(self) -> None:
        for widget in self.lista_scroll.winfo_children():
            widget.destroy()

        dimensoes = buscar_dimensoes()
        if not dimensoes:
            ctk.CTkLabel(
                self.lista_scroll,
                text="Nenhuma dimensão cadastrada.",
                text_color="gray50",
                font=ctk.CTkFont(size=14),
            ).pack(pady=20)
            return

        for dim in dimensoes:
            linha = ctk.CTkFrame(self.lista_scroll, fg_color="transparent")
            linha.pack(fill="x", pady=4, padx=6)
            ctk.CTkLabel(
                linha,
                text=(
                    f"{dim['largura_mm']} x {dim['altura_mm']} mm  ·  "
                    f"borda {dim['borda_lateral_mm']}/{dim['borda_superior_mm']} mm"
                ),
                font=ctk.CTkFont(size=15),
                anchor="w",
            ).pack(side="left", padx=(0, 10), fill="x", expand=True)
            ctk.CTkButton(
                linha,
                text="🗑 Excluir",
                width=100,
                height=32,
                fg_color="#c0392b",
                hover_color="#962d22",
                font=ctk.CTkFont(size=13),
                command=lambda d=dim: self._excluir(d),
            ).pack(side="right")

    def _excluir(self, dimensao: sqlite3.Row) -> None:
        confirma = messagebox.askyesno(
            "Excluir dimensão",
            f"Excluir a dimensão {dimensao['largura_mm']} x {dimensao['altura_mm']} mm?",
        )
        if not confirma:
            return
        excluir_dimensao(dimensao["id"])
        self._atualizar_lista()

    def _erro(self, mensagem: str) -> None:
        self.status_label.configure(text_color="#c0392b")
        self.status_var.set(mensagem)
