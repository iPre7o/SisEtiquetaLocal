"""Tela de cadastro de um novo item (nome + validade em dias), com gestão
(exclusão) dos itens já cadastrados."""
import sqlite3
from tkinter import messagebox

import customtkinter as ctk

from database.db import buscar_itens, excluir_item, inserir_item


class RegisterScreen(ctk.CTkFrame):
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
        corpo.pack(fill="both", expand=True, padx=60, pady=(0, 30))
        corpo.grid_columnconfigure(1, weight=1)
        corpo.grid_rowconfigure(0, weight=1)

        # --- coluna esquerda: formulário de cadastro ---
        form = ctk.CTkFrame(corpo, fg_color="transparent")
        form.grid(row=0, column=0, sticky="n", padx=(0, 40))

        ctk.CTkLabel(
            form, text="Cadastrar Etiqueta", font=ctk.CTkFont(size=26, weight="bold")
        ).pack(pady=(10, 30), anchor="w")

        ctk.CTkLabel(form, text="Nome do Item:", font=ctk.CTkFont(size=16)).pack(anchor="w")
        self.entry_nome = ctk.CTkEntry(form, width=320, height=45, font=ctk.CTkFont(size=16))
        self.entry_nome.pack(pady=(5, 20))

        ctk.CTkLabel(
            form, text="Prazo de Validade (dias):", font=ctk.CTkFont(size=16)
        ).pack(anchor="w")
        self.entry_dias = ctk.CTkEntry(form, width=320, height=45, font=ctk.CTkFont(size=16))
        self.entry_dias.pack(pady=(5, 30))

        ctk.CTkButton(
            form,
            text="💾  Salvar Cadastro",
            width=320,
            height=60,
            font=ctk.CTkFont(size=18, weight="bold"),
            fg_color="#2b7a3d",
            hover_color="#225f30",
            command=self.salvar,
        ).pack()

        self.status_var = ctk.StringVar(value="")
        self.status_label = ctk.CTkLabel(
            form,
            textvariable=self.status_var,
            font=ctk.CTkFont(size=14, weight="bold"),
            wraplength=320,
            justify="left",
        )
        self.status_label.pack(pady=(15, 0), anchor="w")

        # --- coluna direita: itens cadastrados, com exclusão ---
        lista_container = ctk.CTkFrame(corpo, fg_color="transparent")
        lista_container.grid(row=0, column=1, sticky="nsew")

        ctk.CTkLabel(
            lista_container, text="Itens cadastrados", font=ctk.CTkFont(size=18, weight="bold")
        ).pack(anchor="w", pady=(10, 10))

        self.lista_scroll = ctk.CTkScrollableFrame(
            lista_container, fg_color=("gray95", "gray17")
        )
        self.lista_scroll.pack(fill="both", expand=True)

    def ao_exibir(self) -> None:
        """Chamado toda vez que a tela é aberta: garante formulário limpo e lista atual."""
        self.entry_nome.delete(0, "end")
        self.entry_dias.delete(0, "end")
        self.status_var.set("")
        self._atualizar_lista()
        self.entry_nome.focus()

    def salvar(self) -> None:
        nome = self.entry_nome.get().strip()
        dias_texto = self.entry_dias.get().strip()

        if not nome:
            self._erro("Informe o nome do item.")
            return
        if not dias_texto.isdigit() or int(dias_texto) <= 0:
            self._erro("Prazo de validade deve ser um número de dias maior que zero.")
            return

        try:
            inserir_item(nome, int(dias_texto))
        except sqlite3.IntegrityError:
            self._erro("Já existe um item cadastrado com esse nome.")
            return

        self.status_label.configure(text_color="#2b7a3d")
        self.status_var.set(f"✔ '{nome}' cadastrado com sucesso!")
        self.entry_nome.delete(0, "end")
        self.entry_dias.delete(0, "end")
        self.entry_nome.focus()
        self._atualizar_lista()

    def _atualizar_lista(self) -> None:
        for widget in self.lista_scroll.winfo_children():
            widget.destroy()

        itens = buscar_itens()
        if not itens:
            ctk.CTkLabel(
                self.lista_scroll,
                text="Nenhum item cadastrado.",
                text_color="gray50",
                font=ctk.CTkFont(size=14),
            ).pack(pady=20)
            return

        for item in itens:
            linha = ctk.CTkFrame(self.lista_scroll, fg_color="transparent")
            linha.pack(fill="x", pady=4, padx=6)
            ctk.CTkLabel(
                linha,
                text=f"{item['nome']}  ({item['validade_dias']} dias)",
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
                command=lambda i=item: self._excluir(i),
            ).pack(side="right")

    def _excluir(self, item: sqlite3.Row) -> None:
        confirma = messagebox.askyesno(
            "Excluir item",
            f"Excluir o item '{item['nome']}'?\n\nEsta ação não pode ser desfeita.",
        )
        if not confirma:
            return
        excluir_item(item["id"])
        self._atualizar_lista()

    def _erro(self, mensagem: str) -> None:
        self.status_label.configure(text_color="#c0392b")
        self.status_var.set(mensagem)
