import logging

class StandardBaseAgent:
    def __init__(self):
        self.modelo_llm = None
        self.tratamento_excecoes = True
    def registrar_modelo_llm(self, modelo):
        self.modelo_llm = modelo
    def tratar_excecao(self, excecao):
        if self.tratamento_excecoes:
            logging.error(excecao)
        else:
            raise excecao