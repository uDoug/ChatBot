import os
import json


class DataHandler:
    def __init__(self):
        self.data_dir = 'historicos'
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)

        self.user_id = None

    def save_data(self, data):
        """
        Salva os dados em um arquivo JSON.
        """

        nome_do_arquivo = f"{self.user_id}.json"
        caminho_do_arquivo = os.path.join(self.data_dir, nome_do_arquivo)

        if not os.path.exists(caminho_do_arquivo):
            print(f"Arquivo para o usuário {self.user_id} não encontrado. Criando novo arquivo.")

        file_path = os.path.join(self.data_dir, f'{self.user_id}.json')
        with open(file_path, 'w') as file:
            json.dump(data, file, indent=4, ensure_ascii=False)

    def load_data(self):
        """
        Carrega os dados de um arquivo JSON.
        """
        file_path = os.path.join(self.data_dir, f'{self.user_id}.json')
        if not os.path.exists(file_path):
            print(f"Arquivo para o usuário {self.user_id} não encontrado.")
            return None

        with open(file_path, 'r') as file:
            return json.load(file)