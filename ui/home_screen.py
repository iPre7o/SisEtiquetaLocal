"""Tela inicial: apenas dois botões grandes, como pedido no requisito."""
import customtkinter as ctk


class HomeScreen(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        centro = ctk.CTkFrame(self, fg_color="transparent")
        centro.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(
            centro, text="Sistema de Etiquetas", font=ctk.CTkFont(size=32, weight="bold")
        ).pack(pady=(0, 50))

        ctk.CTkButton(
            centro,
            text="🖨  Imprimir Etiqueta",
            width=360,
            height=90,
            font=ctk.CTkFont(size=22, weight="bold"),
            command=lambda: controller.mostrar_tela("PrintScreen"),
        ).pack(pady=15)

        ctk.CTkButton(
            centro,
            text="📋  Cadastrar Etiqueta",
            width=360,
            height=90,
            font=ctk.CTkFont(size=22, weight="bold"),
            fg_color="#2b7a3d",
            hover_color="#225f30",
            command=lambda: controller.mostrar_tela("RegisterScreen"),
        ).pack(pady=15)

        ctk.CTkButton(
            centro,
            text="📐  Gerenciar Dimensões",
            width=360,
            height=90,
            font=ctk.CTkFont(size=22, weight="bold"),
            fg_color="#6c4ea6",
            hover_color="#573d87",
            command=lambda: controller.mostrar_tela("DimensoesScreen"),
        ).pack(pady=15)
