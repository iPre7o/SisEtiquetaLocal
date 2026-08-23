"""Janela principal: controla a navegação entre as telas (padrão container)."""
import customtkinter as ctk

from database.db import init_db
from ui.dimensoes_screen import DimensoesScreen
from ui.home_screen import HomeScreen
from ui.print_screen import PrintScreen
from ui.register_screen import RegisterScreen

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        init_db()

        self.title("Sistema de Etiquetas")
        self.geometry("900x650")
        self.minsize(800, 600)

        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(fill="both", expand=True)

        self.frames = {}
        for Tela in (HomeScreen, RegisterScreen, PrintScreen, DimensoesScreen):
            frame = Tela(self.container, self)
            self.frames[Tela.__name__] = frame
            frame.place(relx=0, rely=0, relwidth=1, relheight=1)

        self.mostrar_tela("HomeScreen")

    def mostrar_tela(self, nome_tela: str) -> None:
        frame = self.frames[nome_tela]
        if hasattr(frame, "ao_exibir"):
            frame.ao_exibir()
        frame.tkraise()
