import boto3
from uuid import uuid4
import requests
import json

class Trasncribe:
    def __init__(self):
        self.transcribe = boto3.client('transcribe')


    def audio_transcripition(self, s3_audio_url):
        try:
            job_name = Trasncribe.get_job_name()
            response = self.transcribe.start_transcription_job(
            TranscriptionJobName = job_name,
            LanguageCode = 'pt-BR',
            MediaFormat = 'ogg',
            Media = {'MediaFileUri':  s3_audio_url}
            )
            return job_name
        except Exception as e:
            print(f'erro na trancrição do audio {e}')
    
    def wait_trancripition(self, job_name):
        try:
            while True:
                response = self.transcribe.get_transcription_job(
                    TranscriptionJobName = job_name 
                )

                job_status = response['TranscriptionJob']['TranscriptionJobStatus']

                if job_status in ['COMPLETED', 'FAILED']:
                    print(f'status {job_status}')

                    if job_status == 'COMPLETED':
                        print('Transcrição realizada com Sucesso')
                        url = response['TranscriptionJob']['Transcript']['TranscriptFileUri']
                        
                        return url
                    
                    else:
                        print('Falha na transcrição') 
                        return
        except Exception as e:
            print(f'Erro ao receber a trancrição {e}')

    

    def get_job_name():
        num = uuid4().hex
        return f'job_name_{num}'
    

    def download_transcription(self, transcription_url):
        try:
            response = requests.get(transcription_url)
            data = response.json()
            return data['results']['transcripts'][0]['transcript']
        except requests.RequestException as e:
            print(f'Falha no dowlload da transcrição: {e}')