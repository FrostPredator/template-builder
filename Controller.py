# -*- coding: utf-8 -*-
""" @author: Gabriel Maccari """

from PyQt6.QtWidgets import *
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt
from icecream import ic


class Controlador:
    def __init__(self, modelo, interface):
        super(Controlador, self).__init__()

        # Atributos do controlador
        self.modelo = modelo
        self.interface = interface
        self.caminho_caderneta = None

        # Conecta os botões de abrir arquivo e gerar a caderneta às funções
        self.interface.botao_abrir_arquivo.clicked.connect(self.botao_abrir_arquivo_clicado)
        self.interface.botao_gerar_nova_caderneta.clicked.connect(self.botao_gerar_nova_caderneta_clicado)

        # Define a função a ser conectada aos botões de status das colunas
        self.interface.funcao_botoes_status = self.icone_status_clicado

        self.interface.checkbox_continuar_caderneta.clicked.connect(self.checkbox_continuar_caderneta_clicada)

        self.interface.show()

    def botao_abrir_arquivo_clicado(self):
        """
        Chama a função para abrir a tabela no controlador. Caso um arquivo seja aberto com sucesso, atualiza o
        rotulo_arquivo com o nome do arquivo selecionado e chama o método checar_colunas para atualizar os ícones de
        status.
        :returns: Nada.
        """
        ic()

        try:
            # arquivo_aberto, num_pontos = False, "-"   # Eu removi isso e A PRINCÍPIO não quebrou nada :)
            caminho = mostrar_dialogo_arquivo(
                "Selecione uma tabela contendo os dados de entrada.",
                "Pasta de trabalho do Excel (*.xlsx);;Pasta de trabalho habilitada para macro do Excel (*.xlsm);;"
            )
            if caminho == "":
                return

            arquivo_aberto, num_pontos = self.modelo.abrir_tabela(caminho)

            if not arquivo_aberto:
                return

            partes_caminho = caminho.split("/")
            self.interface.rotulo_arquivo.setText(partes_caminho[-1])
            self.interface.num_pontos.setText(str(num_pontos) if num_pontos > 0 else "-")
            self.interface.combobox_ponto_inicio.clear()
            self.interface.combobox_ponto_inicio.addItems(self.modelo.df["Ponto"])

            self.modelo.abrir_aba_listas(caminho)

            self.checar_colunas()

            if "nan" in self.modelo.df.columns:
                mostrar_popup(
                    "Atenção! Existem colunas com nomes inválidos na tabela que podem causar erros ou "
                    "anomalias no funcionamento da ferramenta. Verifique se as fórmulas presentes nas células de "
                    "cabeçalho das colunas de estruturas (colunas S a AL) não foram comprometidas. Isso geralmente "
                    "ocorre ao recortar e colar células na aba de Listas ao preencher as estruturas.",
                    parent=self.interface
                )

        except Exception as exception:
            mostrar_popup(f"{exception}", tipo_msg="erro", parent=self.interface)
            ic(exception)

    def checar_colunas(self):
        """
        Chama a função do controlador para checar se cada coluna está no formato especificado. Atualiza os botões de
        status conforme o resultado. Se todas as colunas estiverem OK, habilita o botão para gerar o template.
        :returns: Nada.
        """
        ic()

        status_colunas = self.modelo.checar_colunas()
        for widget, status in zip(self.interface.botoes_status, status_colunas):
            widget.definir_status(status)
        if all(stts == "ok" for stts in status_colunas):
            self.interface.botao_gerar_nova_caderneta.setEnabled(True)
        else:
            self.interface.botao_gerar_nova_caderneta.setEnabled(False)

    def icone_status_clicado(self, coluna: str, status: str):
        """
        Chama a função do controlador para identificar os problemas na coluna e mostra os resultados em uma popup.
        :param coluna: A coluna a ser verificada.
        :param status: O status da coluna ("ok", "faltando", "problemas", "nulos" ou "dominio").
        :returns: Nada.
        """
        ic(coluna, status)

        try:
            localizar_problemas = {
                "coluna_faltando": lambda coluna_faltando: [],
                "fora_de_formato": self.modelo.localizar_problemas_formato,
                "celulas_vazias": self.modelo.localizar_celulas_vazias,
                "valores_nao_permitidos": self.modelo.localizar_problemas_dominio,
                "fora_do_intervalo": self.modelo.localizar_problemas_intervalo,
                "valores_repetidos": self.modelo.localizar_valores_repetidos
            }

            if status not in localizar_problemas.keys():
                raise Exception(f"O status informado não foi reconhecido: {status}")

            indices_problemas = localizar_problemas[status](coluna)

            msg = self.modelo.montar_msg_problemas(status, coluna, indices_problemas)
            mostrar_popup(msg, "notificacao", self.interface)

        except Exception as exception:
            mostrar_popup(f"{exception}", tipo_msg="erro", parent=self.interface)
            ic(exception)

    def checkbox_continuar_caderneta_clicada(self):
        """
        Atualiza a interface e permite ao usuário selecionar um arquivo de template para continuar uma caderneta.
        :returns: Nada.
        """
        ic()

        continuar_caderneta = self.interface.checkbox_continuar_caderneta.isChecked()
        if continuar_caderneta:
            self.interface.checkbox_folha_rosto.setChecked(False)
            self.caminho_caderneta = mostrar_dialogo_arquivo(
                "Selecione a caderneta a ser continuada", "Documento do Word (*.docx);;",
                "abrir", self.interface
            )
        else:
            self.caminho_caderneta = None
        self.interface.rotulo_ponto_inicio.setEnabled(continuar_caderneta)
        self.interface.combobox_ponto_inicio.setEnabled(continuar_caderneta)

    def botao_gerar_nova_caderneta_clicado(self):
        """
        Chama as funções do controlador para gerar a caderneta e exportá-la.
        :returns: Nada.
        """
        ic()

        try:
            mostrar_cursor_espera()
            montar_folha_de_rosto = self.interface.checkbox_folha_rosto.isChecked()
            montar_folhas_semestre = self.interface.checkbox_folhas_semestre.isChecked()
            continuar_caderneta = self.caminho_caderneta
            ponto_inicio = self.interface.combobox_ponto_inicio.currentText()
            indice_ponto_inicio = self.modelo.df.index[self.modelo.df["Ponto"] == ponto_inicio]
            self.modelo.gerar_caderneta(montar_folha_de_rosto, montar_folhas_semestre, indice_ponto_inicio, continuar_caderneta)
            mostrar_cursor_espera(False)
            caminho_saida = mostrar_dialogo_arquivo("Salvar caderneta", "Documento do Word (*.docx)",
                                                    modo="salvar")
            if caminho_saida != "":
                self.modelo.salvar_caderneta(caminho_saida)
                mostrar_popup("Caderneta criada com sucesso!")
        except PermissionError as exception:
            mostrar_popup(f"Erro ao salvar a caderneta. Verifique se o arquivo {caminho_saida} não está aberto"
                          f" em outro programa e se você possui privilégios para salvar na pasta selecionada.",
                          tipo_msg="erro", parent=self.interface)
            ic(exception)
        except Exception as exception:
            mostrar_popup(f"{exception}", tipo_msg="erro", parent=self.interface)
            ic(exception)


def mostrar_dialogo_arquivo(titulo: str, filtro: str, modo="abrir", parent: QMainWindow = None):
    """
    Abre um diálogo de seleção/salvamento de arquivo.
    :param titulo: O título da janela.
    :param filtro: Filtros de tipo de arquivo (Ex: "Planilha do Excel (*.xlsx);;Planilha com macro do Excel (*.xlsm)")
    :param modo: "abrir" ou "salvar". Define se o diálogo será de abertura ou salvamento de arquivo.
    :param parent: A janela pai (Default = None).
    :returns: Nada.
    """
    dialog = QFileDialog(parent)
    if modo == "abrir":
        caminho, tipo = dialog.getOpenFileName(caption=titulo, filter=filtro, parent=parent)
    else:
        caminho, tipo = dialog.getSaveFileName(caption=titulo, filter=filtro, parent=parent)
    return caminho


def mostrar_cursor_espera(ativar: bool = True):
    """
    Troca o cursor do mouse por um cursor de espera.
    :param ativar: Default True. False para restaurar o cursor normal.
    :returns: Nada.
    """
    if ativar:
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
    else:
        QApplication.restoreOverrideCursor()


def mostrar_popup(mensagem: str, tipo_msg: str = "notificacao", parent: QMainWindow = None):
    """
    Mostra uma popup com uma mensagem ao usuário.
    :param mensagem: A mensagem a ser exibida na popup.
    :param tipo_msg: "notificacao" ou "erro" (define o ícone da popup). O valor padrão é "notificacao".
    :param parent: A janela pai (Default = None).
    :returns: Nada.
    """
    tipos_popup = {
        "notificacao": {"titulo": "Notificação", "icone": "config/icones/info.png"},
        "erro":        {"titulo": "Erro",        "icone": "config/icones/error.png"}
    }
    title = tipos_popup[tipo_msg]["titulo"]
    icon = QIcon(tipos_popup[tipo_msg]["icone"])

    popup = QMessageBox(parent)
    popup.setText(mensagem)
    popup.setWindowTitle(title)
    popup.setWindowIcon(icon)
    popup.exec()
