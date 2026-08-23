"""Widget de busca com autocomplete, usado na tela de impressão."""
from typing import Callable

import customtkinter as ctk


class BuscaAutocomplete(ctk.CTkFrame):
    """Campo de texto que exibe uma lista de sugestões clicáveis abaixo dele
    conforme o usuário digita. Ao clicar em uma sugestão, `ao_selecionar` é
    chamado com o nome escolhido."""

    def __init__(
        self,
        parent,
        width: int,
        fonte_dados: Callable[[str], list[str]],
        ao_selecionar: Callable[[str], None],
        **kwargs,
    ):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.fonte_dados = fonte_dados
        self.ao_selecionar = ao_selecionar
        self.width = width
        self.lista_frame: ctk.CTkFrame | None = None

        self.entry = ctk.CTkEntry(
            self,
            width=width,
            height=45,
            placeholder_text="Digite o nome do item...",
            font=ctk.CTkFont(size=16),
        )
        self.entry.pack()
        self.entry.bind("<KeyRelease>", self._on_key)
        self.entry.bind("<Return>", self._on_enter)
        self.entry.bind("<FocusOut>", lambda e: self.after(150, self._fechar_lista))

    def _on_key(self, event) -> None:
        if event.keysym in ("Up", "Down", "Return", "Escape", "Tab"):
            return

        termo = self.entry.get().strip()
        self._fechar_lista()
        if not termo:
            return

        resultados = self.fonte_dados(termo)[:8]
        if not resultados:
            return

        # Se o texto já bate exatamente (ignorando maiúsculas/minúsculas) com
        # um item cadastrado, seleciona sozinho -- sem isso, o usuário podia
        # digitar o nome inteiro e nada acontecia por não ter clicado na
        # sugestão.
        exato = next((r for r in resultados if r.lower() == termo.lower()), None)
        if exato:
            self.ao_selecionar(exato)

        # O dropdown é filho do container pai (não de `self`), porque `self`
        # só tem a altura do campo de texto: um filho posicionado abaixo
        # dele via place() seria recortado pelos limites da própria janela
        # de `self` e nunca apareceria na tela. O width precisa ir no
        # construtor: CTkFrame.place() não aceita width/height.
        self.lista_frame = ctk.CTkFrame(
            self.master, width=self.width, fg_color=("gray90", "gray20"), corner_radius=6
        )
        x = self.winfo_x()
        y = self.winfo_y() + self.entry.winfo_height()
        self.lista_frame.place(x=x, y=y)
        self.lista_frame.lift()

        for nome in resultados:
            ctk.CTkButton(
                self.lista_frame,
                text=nome,
                anchor="w",
                fg_color="transparent",
                hover_color=("gray80", "gray30"),
                text_color=("black", "white"),
                command=lambda n=nome: self._selecionar(n),
            ).pack(fill="x", padx=2, pady=1)

    def _on_enter(self, event) -> None:
        """Enter confirma a melhor sugestão sem precisar clicar nela: prioriza
        correspondência exata; senão usa a primeira sugestão da lista."""
        termo = self.entry.get().strip()
        if not termo:
            return
        resultados = self.fonte_dados(termo)
        if not resultados:
            return
        escolhido = next((r for r in resultados if r.lower() == termo.lower()), resultados[0])
        self._selecionar(escolhido)

    def _selecionar(self, nome: str) -> None:
        self.entry.delete(0, "end")
        self.entry.insert(0, nome)
        self._fechar_lista()
        self.ao_selecionar(nome)

    def _fechar_lista(self) -> None:
        if self.lista_frame is not None:
            self.lista_frame.destroy()
            self.lista_frame = None

    def limpar(self) -> None:
        self.entry.delete(0, "end")
        self._fechar_lista()
