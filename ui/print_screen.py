"""Tela de impressão: busca item, calcula datas automaticamente, deixa
escolher o tamanho da etiqueta e a impressora, mostra uma pré-visualização
ao vivo da etiqueta e imprime."""
from datetime import datetime, timedelta

import customtkinter as ctk

from database.db import buscar_dimensoes, buscar_itens
from printing.printer import gerar_imagem_etiqueta, imprimir_etiqueta
from ui.printer_dialog import SeletorImpressora
from ui.widgets import BuscaAutocomplete

PREVIEW_MAX_LARGURA = 380
PREVIEW_MAX_ALTURA = 300

ALINHAMENTOS = {
    "Centralizado": "centro",
    "Esquerda": "esquerda",
    "Direita": "direita",
}

TAMANHOS_TEXTO = {
    "Pequeno": "pequeno",
    "Médio": "medio",
    "Grande": "grande",
}


class PrintScreen(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.item_selecionado = None
        self.producao_atual: datetime | None = None
        self.validade_atual: datetime | None = None
        self.dimensoes_dict: dict[str, object] = {}
        self.dimensao_selecionada = None
        self._responsavel_pendente = ""
        self._quantidade_pendente = 1

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

        # Painel no canto superior direito: escolha do tamanho da etiqueta.
        painel_dimensao = ctk.CTkFrame(topo, fg_color=("gray90", "gray20"), corner_radius=8)
        painel_dimensao.pack(side="right")
        ctk.CTkLabel(
            painel_dimensao, text="Tamanho:", font=ctk.CTkFont(size=14, weight="bold")
        ).pack(side="left", padx=(14, 6), pady=8)
        self.dimensao_var = ctk.StringVar(value="")
        self.menu_dimensao = ctk.CTkOptionMenu(
            painel_dimensao,
            variable=self.dimensao_var,
            values=["--"],
            width=160,
            command=self._selecionar_dimensao,
        )
        self.menu_dimensao.pack(side="left", padx=(0, 14), pady=8)

        corpo = ctk.CTkFrame(self, fg_color="transparent")
        corpo.pack(fill="both", expand=True, padx=60, pady=(10, 30))
        corpo.grid_columnconfigure(0, weight=0)
        corpo.grid_columnconfigure(1, weight=1)
        corpo.grid_rowconfigure(0, weight=1)

        # --- coluna esquerda: formulário -------------------------------
        form = ctk.CTkFrame(corpo, fg_color="transparent")
        form.grid(row=0, column=0, sticky="n", padx=(0, 40))

        ctk.CTkLabel(
            form, text="Imprimir Etiqueta", font=ctk.CTkFont(size=28, weight="bold")
        ).pack(pady=(0, 30), anchor="w")

        ctk.CTkLabel(form, text="Buscar item cadastrado:", font=ctk.CTkFont(size=16)).pack(
            anchor="w"
        )
        self.busca = BuscaAutocomplete(
            form,
            width=420,
            fonte_dados=lambda termo: [i["nome"] for i in buscar_itens(termo)],
            ao_selecionar=self.selecionar_item,
        )
        self.busca.pack(pady=(5, 20))

        self.info_var = ctk.StringVar(value="Selecione um item para ver produção e validade.")
        ctk.CTkLabel(
            form,
            textvariable=self.info_var,
            font=ctk.CTkFont(size=14),
            text_color="gray30",
            justify="left",
        ).pack(pady=(0, 20), anchor="w")

        ctk.CTkLabel(form, text="Alinhamento do texto:", font=ctk.CTkFont(size=16)).pack(
            anchor="w"
        )
        self.alinhamento_var = ctk.StringVar(value="Centralizado")
        self.seg_alinhamento = ctk.CTkSegmentedButton(
            form,
            values=list(ALINHAMENTOS.keys()),
            variable=self.alinhamento_var,
            command=lambda v: self._atualizar_preview(),
        )
        self.seg_alinhamento.pack(pady=(5, 20), fill="x")

        ctk.CTkLabel(form, text="Tamanho do texto:", font=ctk.CTkFont(size=16)).pack(
            anchor="w"
        )
        self.tamanho_texto_var = ctk.StringVar(value="Pequeno")
        self.seg_tamanho_texto = ctk.CTkSegmentedButton(
            form,
            values=list(TAMANHOS_TEXTO.keys()),
            variable=self.tamanho_texto_var,
            command=lambda v: self._atualizar_preview(),
        )
        self.seg_tamanho_texto.pack(pady=(5, 20), fill="x")

        ctk.CTkLabel(form, text="Nome do Responsável:", font=ctk.CTkFont(size=16)).pack(
            anchor="w"
        )
        self.entry_responsavel = ctk.CTkEntry(
            form, width=420, height=45, font=ctk.CTkFont(size=16)
        )
        self.entry_responsavel.pack(pady=(5, 20))
        self.entry_responsavel.bind("<KeyRelease>", lambda e: self._atualizar_preview())

        ctk.CTkLabel(
            form, text="Quantidade de etiquetas:", font=ctk.CTkFont(size=16)
        ).pack(anchor="w")
        self.entry_quantidade = ctk.CTkEntry(
            form, width=420, height=45, font=ctk.CTkFont(size=16)
        )
        self.entry_quantidade.pack(pady=(5, 30))

        self.btn_imprimir = ctk.CTkButton(
            form,
            text="🖨  Imprimir Etiqueta",
            width=420,
            height=70,
            font=ctk.CTkFont(size=20, weight="bold"),
            state="disabled",
            command=self.imprimir,
        )
        self.btn_imprimir.pack()

        self.status_var = ctk.StringVar(value="")
        self.status_label = ctk.CTkLabel(
            form, textvariable=self.status_var, font=ctk.CTkFont(size=15, weight="bold")
        )
        self.status_label.pack(pady=(15, 0))

        # --- coluna direita: pré-visualização ao vivo -------------------
        preview_container = ctk.CTkFrame(corpo, fg_color=("gray95", "gray17"), corner_radius=10)
        preview_container.grid(row=0, column=1, sticky="n")

        ctk.CTkLabel(
            preview_container,
            text="Pré-visualização da etiqueta",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(pady=(18, 12))

        self.preview_label = ctk.CTkLabel(
            preview_container,
            text="Selecione um item para\nver como a etiqueta vai ficar.",
            font=ctk.CTkFont(size=13),
            text_color="gray50",
            fg_color="white",
            corner_radius=6,
            width=PREVIEW_MAX_LARGURA,
            height=PREVIEW_MAX_ALTURA,
        )
        self.preview_label.pack(padx=20, pady=(0, 20))

    def ao_exibir(self) -> None:
        """Chamado toda vez que a tela é aberta: reseta seleção e formulário."""
        self.item_selecionado = None
        self.producao_atual = None
        self.validade_atual = None
        self.busca.limpar()
        self.entry_responsavel.delete(0, "end")
        self.entry_quantidade.delete(0, "end")
        self.entry_quantidade.insert(0, "1")
        self.alinhamento_var.set("Centralizado")
        self.tamanho_texto_var.set("Pequeno")
        self.info_var.set("Selecione um item para ver produção e validade.")
        self.status_var.set("")
        self.btn_imprimir.configure(state="disabled")
        self._atualizar_dimensoes()
        self._atualizar_preview()

    def _atualizar_dimensoes(self) -> None:
        """Recarrega os tamanhos de etiqueta cadastrados no seletor do canto,
        preservando a seleção atual quando ela ainda existir."""
        dimensoes = buscar_dimensoes()
        self.dimensoes_dict = {
            f"{d['largura_mm']} x {d['altura_mm']} mm": d for d in dimensoes
        }
        valores = list(self.dimensoes_dict.keys())

        if valores:
            self.menu_dimensao.configure(values=valores, state="normal")
            atual = self.dimensao_var.get()
            if atual not in self.dimensoes_dict:
                self.dimensao_var.set(valores[0])
            self.dimensao_selecionada = self.dimensoes_dict[self.dimensao_var.get()]
        else:
            self.menu_dimensao.configure(values=["Nenhuma cadastrada"], state="disabled")
            self.dimensao_var.set("Nenhuma cadastrada")
            self.dimensao_selecionada = None

    def _selecionar_dimensao(self, valor: str) -> None:
        self.dimensao_selecionada = self.dimensoes_dict.get(valor)
        self._atualizar_preview()

    def selecionar_item(self, nome_item: str) -> None:
        itens = buscar_itens(nome_item)
        item = next((i for i in itens if i["nome"] == nome_item), None)
        if not item:
            return

        self.item_selecionado = item
        self.producao_atual = datetime.now()
        # O dia da produção conta como o 1º dia do prazo de validade: "3 dias
        # de validade" a partir de hoje vence daqui a 2 dias, não 3.
        self.validade_atual = self.producao_atual + timedelta(days=item["validade_dias"] - 1)

        self.info_var.set(
            f"Produção: {self.producao_atual.strftime('%d/%m/%Y')}\n"
            f"Validade: {self.validade_atual.strftime('%d/%m/%Y')}"
        )
        self.btn_imprimir.configure(state="normal")
        self.status_var.set("")
        self._atualizar_preview()

    def _atualizar_preview(self) -> None:
        """Redesenha a pré-visualização com os dados atuais do formulário --
        exatamente a mesma imagem que vai para a impressora, então qualquer
        corte ou texto grande demais já aparece aqui antes de imprimir."""
        if not self.item_selecionado or not self.dimensao_selecionada:
            self.preview_label.configure(
                image=None,
                text="Selecione um item e o tamanho\npara ver como a etiqueta vai ficar.",
            )
            return

        responsavel = self.entry_responsavel.get().strip() or "—"
        alinhamento = ALINHAMENTOS.get(self.alinhamento_var.get(), "centro")
        tamanho_texto = TAMANHOS_TEXTO.get(self.tamanho_texto_var.get(), "pequeno")
        imagem = gerar_imagem_etiqueta(
            nome_item=self.item_selecionado["nome"],
            producao=self.producao_atual,
            validade=self.validade_atual,
            responsavel=responsavel,
            largura_mm=self.dimensao_selecionada["largura_mm"],
            altura_mm=self.dimensao_selecionada["altura_mm"],
            borda_lateral_mm=self.dimensao_selecionada["borda_lateral_mm"],
            borda_superior_mm=self.dimensao_selecionada["borda_superior_mm"],
            alinhamento=alinhamento,
            tamanho_texto=tamanho_texto,
        )

        escala = min(PREVIEW_MAX_LARGURA / imagem.width, PREVIEW_MAX_ALTURA / imagem.height)
        tamanho_exibicao = (round(imagem.width * escala), round(imagem.height * escala))

        preview_img = ctk.CTkImage(
            light_image=imagem, dark_image=imagem, size=tamanho_exibicao
        )
        self.preview_label.configure(image=preview_img, text="")
        self.preview_label.image = preview_img

    def imprimir(self) -> None:
        responsavel = self.entry_responsavel.get().strip()
        quantidade_texto = self.entry_quantidade.get().strip()

        if not self.item_selecionado:
            self._erro("Selecione um item primeiro.")
            return
        if not responsavel:
            self._erro("Informe o nome do responsável.")
            return
        if not self.dimensao_selecionada:
            self._erro("Cadastre um tamanho de etiqueta em 'Gerenciar Dimensões'.")
            return
        if not quantidade_texto.isdigit() or int(quantidade_texto) <= 0:
            self._erro("Quantidade de etiquetas deve ser um número maior que zero.")
            return

        self._responsavel_pendente = responsavel
        self._quantidade_pendente = int(quantidade_texto)
        SeletorImpressora(self, ao_confirmar=self._enviar_impressao)

    def _enviar_impressao(self, nome_impressora: str | None) -> None:
        alinhamento = ALINHAMENTOS.get(self.alinhamento_var.get(), "centro")
        tamanho_texto = TAMANHOS_TEXTO.get(self.tamanho_texto_var.get(), "pequeno")
        try:
            imprimir_etiqueta(
                nome_item=self.item_selecionado["nome"],
                producao=self.producao_atual,
                validade=self.validade_atual,
                responsavel=self._responsavel_pendente,
                largura_mm=self.dimensao_selecionada["largura_mm"],
                altura_mm=self.dimensao_selecionada["altura_mm"],
                borda_lateral_mm=self.dimensao_selecionada["borda_lateral_mm"],
                borda_superior_mm=self.dimensao_selecionada["borda_superior_mm"],
                alinhamento=alinhamento,
                tamanho_texto=tamanho_texto,
                impressora=nome_impressora,
                copias=self._quantidade_pendente,
            )
            self.status_label.configure(text_color="#2b7a3d")
            plural = "s" if self._quantidade_pendente > 1 else ""
            self.status_var.set(
                f"✔ {self._quantidade_pendente} etiqueta{plural} enviada{plural} para a impressora!"
            )
        except Exception as e:
            self._erro(f"Erro ao imprimir: {e}")

    def _erro(self, mensagem: str) -> None:
        self.status_label.configure(text_color="#c0392b")
        self.status_var.set(mensagem)
