from ..utils.base_mqtt import MqttClient
import json
from .email_handler import HandleMail
import threading
import logging

# Configurar logging
logger = logging.getLogger(__name__)

class MqttHandler(MqttClient):
    def __init__(self, broker: str, port: int, username: str, password: str, topic: str) -> None:
        super().__init__(broker, port, username, password, topic)
    
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
                dados = json.loads(msg.payload.decode())
                
                # Processar dados no banco de forma síncrona
                self._process_database_data(dados, msg)
                
                # Enviar email de forma assíncrona para não bloquear MQTT
                self._process_email_notification(dados)
            
        except json.JSONDecodeError as e:
            logger.error(f"Erro ao decodificar JSON: {e}")
        except Exception as e:
            logger.error(f"Erro ao processar mensagem MQTT: {e}")

    def _process_database_data(self, dados, msg):
        """Processa os dados para o banco de dados"""
        if dados.get("tipo") == "usina":
            self._save_usina_data(dados)
        else:
            self._save_client_data(dados, msg)

    def _save_usina_data(self, dados):
        """Salva dados da usina"""
        usina_data = dados.get("Data", {}).get("usina", {})
        central_data = dados.get("Data", {}).get("central", {})

       

    def _save_client_data(self, dados, msg):
        """Salva dados do cliente"""
        dados_hospital = dados.get("Data", {})
    

    def _process_email_notification(self, dados):
        """Processa notificação por email de forma assíncrona"""
        def send_notification():
            try:
                HandleMail.enviar(dados)
                logger.info(f"Email enviado para hospital: {dados.get('Hospital', 'Unknown')}")
            except Exception as e:
                logger.error(f"Erro ao enviar email: {e}")
        
        # Executa em thread separada para não bloquear MQTT
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

