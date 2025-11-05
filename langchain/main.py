from utils.s3Utils import S3Utils
from utils.dataUtils import DataHandler
from utils.bedrockUtils import BedrockUtils
from utils.transcribeUtils import Trasncribe
import os
import dotenv
import telebot
 
class LangChainMain:
    """
    Classe principal para executar operações com o LangChain e S3.
    """
    def __init__(self, bucket_name):
        self.s3_handler = S3Utils(bucket_name)
        self.bedrock_handler = BedrockUtils()
        self.transcribe_handle = Trasncribe()
        self.vector_store = None
 
    def run(self, question, userName, history):
        """
        Executa o processo principal.
        """
 
        if self.vector_store is None:
            print("Primeira execução: Realizando setup inicial (download e embeddings)...")
            pdf_dataset = self.s3_handler.download_pdfs(self.s3_handler.list_all_pdfs())
           
            if not pdf_dataset:
                return "Não existe nenhum documento para basear minha resposta."
           
            self.vector_store = self.bedrock_handler.make_embeddings(EMBEDDING_MODEL, pdf_dataset)
            print("Setup inicial concluído.")
       
        print(self.vector_store._collection.count())
 
        response = self.bedrock_handler.ask_llm(MODEL_ID, self.vector_store, question, userName, history)
       
        return response
 
if __name__ == "__main__":
    dotenv.load_dotenv()
 
    BOT_TOKEN = os.getenv('BOT_API_TOKEN')
    BUCKET_NAME = os.getenv('BUCKET_NAME')
 
    bot = telebot.TeleBot(BOT_TOKEN)
 
    EMBEDDING_MODEL = 'amazon.titan-embed-text-v2:0'
    MODEL_ID = 'amazon.nova-pro-v1:0'
 
    # O cache em memória para as conversas ativas
    message_history = {}
 
    print("Inicializando instâncias...")
    langchain_main = LangChainMain(BUCKET_NAME)
    data_handler = DataHandler()
   
    @bot.message_handler(func=lambda message: True)
    def handle_message(msg: telebot.types.Message):
        global message_history # Use global para modificar
       
        QUESTION = msg.text
        user_name = msg.from_user.first_name
        user_id = msg.from_user.id
 
        if user_id not in message_history:
            print(f"Usuário {user_id} não está em cache. Carregando histórico do disco...")
            data_handler.user_id = user_id
            loaded_history = data_handler.load_data()
            message_history[user_id] = loaded_history if loaded_history is not None else []
       
       
 
        print(f"Recebida pergunta de {user_name} (ID: {user_id})")
       
        try:
            response = langchain_main.run(
                question=QUESTION,
                userName=user_name,
                history=message_history[user_id]
            )
 
            message_history[user_id].append({"role": "user", "content": QUESTION})
            message_history[user_id].append({"role": "Themis", "content": response})
 
            data_handler.user_id = user_id
            data_handler.save_data(message_history[user_id])
           
            bot.send_message(msg.chat.id, response)
           
        except Exception as e:
            print(f"Ocorreu um erro: {e}")
            bot.send_message(msg.chat.id, "Ocorreu um erro ao processar sua solicitação. Tente novamente.")
 
 
    @bot.message_handler(content_types=['audio', 'voice'])
    def message_audio(msg:telebot.types.Message):
        global message_history # Use global para modificar
 
        user_name = msg.from_user.first_name
        user_id = msg.from_user.id
       
        try:
            file_id = msg.voice.file_id if msg.voice else msg.audio.file_id
            file_info = bot.get_file(file_id)
            file_dowload = bot.download_file(file_info.file_path)
 
            local_filename = 'audio.ogg'
            with open (local_filename, 'wb') as file:
                file.write(file_dowload)
 
        except Exception as e:
            print(f'erro ao receber audio {e}')
 
        try:            
            s3_path = langchain_main.s3_handler.upload_file(local_filename)
            os.remove(local_filename)
 
            s3_audio_url = f's3://{BUCKET_NAME}/{s3_path}'
        except Exception as e:
            print(f'erro ao salvar s3 {e}')
 
 
        try:
            job_name = langchain_main.transcribe_handle.audio_transcripition(s3_audio_url)
           
            trancription_url = langchain_main.transcribe_handle.wait_trancripition(job_name)
               
            QUESTION = langchain_main.transcribe_handle.download_transcription(trancription_url)
        except Exception as e:
            print(f'erro na trancrição do audio {e}')
       
        print(QUESTION)
 
        if user_id not in message_history:
            print(f"Usuário {user_id} não está em cache. Carregando histórico do disco...")
            data_handler.user_id = user_id
            loaded_history = data_handler.load_data()
            message_history[user_id] = loaded_history if loaded_history is not None else []
       
       
 
        print(f"Recebida pergunta de {user_name} (ID: {user_id})")
       
        try:
            response = langchain_main.run(
                question=QUESTION,
                userName=user_name,
                history=message_history[user_id]
            )
 
            message_history[user_id].append({"role": "user", "content": QUESTION})
            message_history[user_id].append({"role": "Themis", "content": response})
 
            data_handler.user_id = user_id
            data_handler.save_data(message_history[user_id])
           
            bot.send_message(msg.chat.id, response)
           
        except Exception as e:
            print(f"Ocorreu um erro: {e}")
            bot.send_message(msg.chat.id, "Ocorreu um erro ao processar sua solicitação. Tente novamente.")
 
 
   
 
    print("Bot iniciado e aguardando mensagens...")
    bot.infinity_polling()