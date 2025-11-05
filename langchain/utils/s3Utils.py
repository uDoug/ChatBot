import boto3
import os
from botocore.exceptions import ClientError


class S3Utils:
    """
    Classe para interagir com o Amazon S3.
    """
    def __init__(self, bucket_name):
        """ 
        Inicializa a classe S3Utils com o nome do bucket.
        """
        self.bucket_name = bucket_name
        self.s3_resource = boto3.resource('s3')
        try:
            # Checa se o bucket existe e se temos acesso a ele
            self.s3_resource.meta.client.head_bucket(Bucket=bucket_name)
            self.bucket = self.s3_resource.Bucket(self.bucket_name)
            print(f"Classe S3Utils inicializada com sucesso para o bucket '{self.bucket_name}'.")
        except ClientError as e:
            # Se o bucket não existir ou não tivermos permissão, um erro será lançado
            error_code = e.response['Error']['Code']
            if error_code == '404':
                print(f"Erro: O bucket '{self.bucket_name}' não foi encontrado.")
            elif error_code == '403':
                print(f"Erro: Acesso negado ao bucket '{self.bucket_name}'. Verifique suas permissões do IAM.")
            else:
                print(f"Um erro inesperado ocorreu: {e}")
            # Impede a continuação se o bucket não for acessível
            self.bucket = None
            raise e

    def list_all_pdfs(self):
        """
        Lista as chaves de todos os arquivos PDF no bucket.
        """
        if not self.bucket:
            print("Não é possível listar os arquivos, pois o bucket não foi inicializado corretamente.")
            return []

        pdf_keys = []
        print(f"Buscando arquivos PDF no bucket '{self.bucket_name}'...")
        try:
            # Itera através de todos os objetos no bucket usando o objeto de bucket da classe
            for obj in self.bucket.objects.all():
                if obj.key.lower().endswith('.pdf'):
                    print(f"  - Encontrado: {obj.key}")
                    pdf_keys.append(obj.key)
        except ClientError as e:
            print(f"Ocorreu um erro ao listar os objetos: {e}")
            return []
            
        print(f"\nTotal de arquivos PDF encontrados: {len(pdf_keys)}\n")
        return pdf_keys

    def download_pdfs(self, pdf_keys):
        """
        Faz o download dos arquivos PDF para pasta dataset.
        Verifica se o arquivo já existe localmente antes de fazer o download.
        """
        pdf_list = []
        
        # Criar pasta dataset se não existir
        os.makedirs("dataset", exist_ok=True)
        
        for pdf in pdf_keys:
            pdf_name = pdf.split("/")[-1]
            local_path = f"dataset/{pdf_name}"
            
            # Verifica se o arquivo já existe localmente
            if os.path.exists(local_path):
                print(f"Arquivo '{pdf_name}' já existe localmente. Pulando download...")
                pdf_list.append(pdf_name)
                continue
            
            print(f"Downloading '{pdf}'...")
            try:
                self.s3_resource.Object(bucket_name=self.bucket_name, key=pdf).download_file(local_path)
                pdf_list.append(pdf_name)
                print(f"Download completo: {pdf}")
            except ClientError as e:
                print(f"Erro ao fazer download de '{pdf}': {e}")
                
        print(f"\nTotal de arquivos PDF processados: {len(pdf_list)}")
        return pdf_list

    def get_local_pdfs(self):
        """
        Lista todos os arquivos PDF disponíveis localmente na pasta dataset.
        """
        dataset_path = "dataset"
        if not os.path.exists(dataset_path):
            return []
        
        local_pdfs = []
        for file in os.listdir(dataset_path):
            if file.lower().endswith('.pdf'):
                local_pdfs.append(file)
        
        print(f"Arquivos PDF locais encontrados: {local_pdfs}")
        return local_pdfs
    
    
    def upload_file(self, file):
        try:
            s3_path = 'audios/audio.ogg'
            self.bucket.upload_file(file, s3_path)
            print('Audio salvo no s3')
            return s3_path
        except ClientError as e:
            print(f'Erro ao fazer upload do audio {e}')
            return