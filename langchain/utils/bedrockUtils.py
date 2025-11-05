import boto3
import os
from langchain_aws import BedrockEmbeddings
from langchain.document_loaders import PyPDFLoader
from langchain_aws import ChatBedrock
from langchain_chroma import Chroma
from langchain_core.output_parsers import StrOutputParser
from langchain_text_splitters import RecursiveCharacterTextSplitter
from operator import itemgetter
 
from langchain_core.messages import HumanMessage, AIMessage
 
from langchain.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
    MessagesPlaceholder,
)
 
 
class BedrockUtils:
    """
    Classe utilitária para interações com o Amazon Bedrock.
    """
    def __init__(self):
        """
        Inicializa a classe com o ID do modelo Bedrock.
        """
        self.bedrock = boto3.client('bedrock-runtime')
   
    @staticmethod
    def make_embeddings(embedding_model_id, downloaded_pdfs):
        """
        Obtém embeddings para um texto usando o modelo Bedrock.
        Verifica se o vector store já existe antes de criar os embeddings.
        """
        vector_store_path = 'vector_store/chroma/'
       
        # Verifica se o vector store já existe
        if os.path.exists(vector_store_path) and os.listdir(vector_store_path):
            print("Vector store já existe. Carregando vector store existente...")
            try:
                # Carrega o vector store existente
                vector_store = Chroma(
                    persist_directory=vector_store_path,
                    embedding_function=BedrockEmbeddings(model_id=embedding_model_id)
                )
                print("Vector store carregado com sucesso!")
 
                return vector_store
           
            except Exception as e:
                print(f"Erro ao carregar vector store existente: {e}")
                print("Criando novo vector store...")
       
        # Se não existe vector store ou houve erro, cria um novo
        print("Criando novo vector store com embeddings...")
       
        loaders = []
        for downloaded_pdf in downloaded_pdfs:
            pdf_path = f"dataset/{downloaded_pdf}"
            if os.path.exists(pdf_path):
                loaders.append(PyPDFLoader(pdf_path))
            else:
                print(f"Aviso: Arquivo '{pdf_path}' não encontrado. Pulando...")
 
        if not loaders:
            raise ValueError("Nenhum arquivo PDF válido encontrado para processar.")
 
        docs = []
        for loader in loaders:
            try:
                docs.extend(loader.load())
            except Exception as e:
                print(f"Erro ao carregar PDF: {e}")
 
        if not docs:
            raise ValueError("Nenhum documento foi carregado com sucesso.")
 
        r_splitter = RecursiveCharacterTextSplitter(chunk_size=1000,
                                                    chunk_overlap=180,
                                                    separators=["\n\n", "\n"],
                                                    add_start_index=True)
 
        docs_splitted = r_splitter.split_documents(docs)
       
        if os.path.exists(vector_store_path):
            vector_store = Chroma(
                persist_directory=vector_store_path,
                embedding_function=BedrockEmbeddings(model_id=embedding_model_id)
            )
            print("Vector store carregado com sucesso, mas não estava vazio. Verifique se os documentos estão atualizados.")
        else:
            vector_store = Chroma.from_documents(
                documents=docs_splitted,
                embedding=BedrockEmbeddings(model_id=embedding_model_id),
                persist_directory=vector_store_path
            )
            print("Vector store criado do zero.")
 
        return vector_store
 
    @staticmethod
    def check_and_update_vector_store(embedding_model_id, downloaded_pdfs):
        """
        Verifica se todos os PDFs estão no vector store e atualiza se necessário.
        """
        vector_store_path = 'vector_store/chroma/'
       
        # Se não existe vector store, cria um novo
        if not os.path.exists(vector_store_path) or not os.listdir(vector_store_path):
            return BedrockUtils.make_embeddings(embedding_model_id, downloaded_pdfs)
       
        try:
            # Carrega o vector store existente
            vector_store = Chroma(
                persist_directory=vector_store_path,
                embedding_function=BedrockEmbeddings(model_id=embedding_model_id)
            )
           
            # Verifica se todos os PDFs estão representados no vector store
            # Aqui você pode implementar lógica adicional para verificar
            # se documentos específicos precisam ser adicionados
           
            print("Vector store verificado e carregado com sucesso!")
            return vector_store
           
        except Exception as e:
            print(f"Erro ao verificar vector store: {e}")
            print("Recriando vector store...")
            return BedrockUtils.make_embeddings(embedding_model_id, downloaded_pdfs)
 
    def ask_llm(self, model_id, vector_store, question, userName, history):
 
        system_prompt_template = """\
        # Persona e Objetivo Principal
 
        Você é Themis, uma assistente jurídica virtual. Sua atuação consiste na análise de documentos jurídicos e no esclarecimento de dúvidas legais, **exclusivamente com base no material de contexto fornecido**. Seu objetivo é oferecer apoio técnico, preciso, confiável e isento de opiniões pessoais ou interpretações externas ao contexto.
 
        ---
 
        # Instruções Adicionais de Resposta
 
        - Sempre cite, entre aspas, trechos relevantes do `{context}` para justificar sua análise, quando possível, cite apenas o necessário e de maneira formatada em utf-8 legível para seres humanos.
        - Estruture suas respostas de forma clara, utilizando parágrafos curtos e listas numeradas se necessário.
        - Se a dúvida for muito ampla, peça um recorte mais específico ao usuário.
        - Em caso de contradição entre o `{context}` e o `{history}`, priorize sempre o conteúdo do `{context}`.
 
        ---
 
        # Análise do Histórico da Conversa (Instrução Crítica)
 
        Antes de responder, você **deve** analisar o `{history}` para contextualizar a pergunta atual.
 
        * **Formato do Histórico:** O histórico é uma lista de diálogos. `role: 'user'` é uma mensagem enviada pelo `{userName}`, e `role: 'Themis'` é uma resposta sua.
 
        * **Se o Histórico estiver Vazio (`[]`):** Significa que esta é a **primeira interação**. Nesse caso, inicie sua resposta com uma breve apresentação antes de abordar a pergunta. Por exemplo: "Olá, {userName}. Eu sou Themis, sua assistente jurídica virtual. Sobre sua dúvida,..."
 
        * **Se o Histórico NÃO estiver Vazio:** Analise as trocas anteriores para entender o fluxo da conversa. Preste atenção especial a:
            * **Perguntas de Acompanhamento:** A `{question}` atual pode ser uma continuação de um tópico anterior. Use o histórico para entender a ligação.
            * **Referências e Pronomens:** O usuário pode usar termos como "isso", "aquilo", "ele" ou "o artigo mencionado" que se referem a algo dito anteriormente por você ou por ele. O histórico é a chave para resolver essas referências.
            * **Manutenção do Contexto:** Garanta que sua resposta seja consistente com as informações que você já forneceu nas interações passadas.
 
        """
 
        human_prompt_template = """\
        # Entradas para Análise
 
        * **Nome do Usuário:**
            {userName}
 
        * **Histórico da Conversa:**
            {history}
 
        * **Contexto (Documentos Jurídicos):**
            {context}
 
        * **Pergunta Atual:**
            {question}
 
        ---
 
        # Resposta:
 
        """
 
        chat_prompt = ChatPromptTemplate.from_messages(
            [
                SystemMessagePromptTemplate.from_template(system_prompt_template),
                MessagesPlaceholder(variable_name="history"),
                HumanMessagePromptTemplate.from_template(human_prompt_template),
            ]
        )
 
 
        llm = ChatBedrock(model_id=model_id,
                        client=self.bedrock)
 
        retriever = vector_store.as_retriever(
            search_type="mmr",
            search_kwargs={'k': 4, 'fetch_k': 20}
        )
 
        def format_history(chat_history):
            formatted_messages = []
            for message in chat_history:
                if message.get('role') == 'user':
                    formatted_messages.append(HumanMessage(content=message.get('content')))
                elif message.get('role') == 'Themis' or message.get('role') == 'assistant': # Ajuste 'Themis' se necessário
                    formatted_messages.append(AIMessage(content=message.get('content')))
            return formatted_messages
 
        rag_chain = (
            {
            "context": itemgetter("question") | retriever,
            "question": itemgetter("question"),
            "userName": itemgetter("userName"),
            "history": lambda x: format_history(x["history"])
            }
            | chat_prompt
            | llm
            | StrOutputParser()
        )
 
        response = rag_chain.invoke({
            "question": question,
            "userName": userName,
            "history": history
        })
 
        print(f"Resposta gerada: {response}")
 
        return response