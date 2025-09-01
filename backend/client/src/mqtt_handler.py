from .utils.base_mqtt import MqttClient
import json
from .email_handler import HandleMail
import redis
import threading
import logging
from .django_handler import sync_hospital

logger = logging.getLogger(__name__)

class MqttHandler(MqttClient):
    def __init__(self, broker: str, port: int, username: str, password: str, topic: str) -> None:
        super().__init__(broker, port, username, password, topic)
        self.data_base = redis.Redis(decode_responses=True)
    
    def on_connect(self, client, userdata, flags, rc) -> None:
        if rc == 0:
            client.subscribe(self.topic)
            logger.info(f"Conectado e inscrito no tópico: {self.topic}")
        else:
            logger.error(f"Falha na conexão: {rc}")

    def on_message(self, client, userdata, msg) -> None:
        """
        Processa a mensagem MQTT e escreve no banco de dados.
        Se 'tipo' == 'usina', grava na tabela OxygenGenerator.
        Caso contrário, grava na tabela ClientData.
        """
        try:
            if msg.topic == "desconnection/topic":
                self._process_email_notification(msg.payload.decode())
            else:
                data = json.loads(msg.payload.decode())
                self._process_database_data(data)
                self._process_email_notification(data)
            
        except json.JSONDecodeError as e:
            logger.error(f"Erro ao decodificar JSON: {e}")
        except Exception as e:
            logger.error(f"Erro ao processar mensagem MQTT: {e}")

    def _process_database_data(self, data_clients):
        """Processa os dados para o banco de dados"""
        if data_clients.get("tipo") == "usina":
            self._save_usina_data(data_clients)
        else:
            self._save_client_data(data_clients)

    def _save_redis(self, data_clients, type):
        try:
            hospital = data_clients.get('Hospital')
            data = data_clients.get('Data')
            data_json = json.dumps(data)

            self.data_base.hset(type, key=hospital, value=data_json)

            sync_hospital(hospital)

        except Exception as e:
            raise Exception(f'Falha ao adcionar {type} ao Redis | erro: {e}')

    def _save_usina_data(self, data):
        """Salva dados da usina"""
        return self._save_redis(data, 'Usina')

    def _save_client_data(self, data):
        """Salva dados do cliente"""
        return self._save_redis(data, 'Central')
        
    def _process_email_notification(self, data):
        """Processa notificação por email de forma assíncrona pra não bloquear o MQTT"""
        def send_notification():
            try:
                HandleMail.send(data)
                logger.info(f"Email enviado para hospital: {data.get('Hospital', 'Unknown')}")
            except Exception as e:
                logger.error(f"Erro ao enviar email: {e}")

        email_thread = threading.Thread(target=send_notification, daemon=True)
        email_thread.start()
    
    def safe_str(self, value):
        return "" if value is None else str(value)

    def safe_float(self, value):
        try:
            return float(value)
        except (ValueError, TypeError):
            return 0
            
    def run_mqtt_client(self):
        return super().run_mqtt_client()

