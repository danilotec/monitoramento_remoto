import logging
import time
import threading
import smtplib
import socket
import json
import os
from threading import Lock
from typing import Optional, List, Dict, Any
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

@dataclass
class EmailConfig:
    """Configuração de email"""
    host: str = 'smtp.gmail.com'
    port: int = 587
    username: str = ''
    password: str = ''
    use_tls: bool = True
    from_email: str = ''
    to_emails: List[str] = None #type:ignore
    
    def __post_init__(self):
        if self.to_emails is None:
            self.to_emails = ['danilocrautomacao@gmail.com']
        
        if not self.from_email:
            self.from_email = self.username

class ConfigManager:
    """Gerenciador de configurações"""
    
    @staticmethod
    def load_from_env() -> EmailConfig:
        """Carrega configurações das variáveis de ambiente"""
        return EmailConfig(
            host=os.getenv('SMTP_SERVER', 'smtp.gmail.com'),
            port=int(os.getenv('SMTP_PORT', '587')),
            username=os.getenv('SMTP_USERNAME', ''),
            password=os.getenv('SMTP_PASSWORD', ''),
            use_tls=os.getenv('SMTP_USE_TLS', 'true').lower() == 'true',
            from_email=os.getenv('EMAIL_FROM', ''),
            to_emails=os.getenv('EMAIL_TO', 'danilocrautomacao@gmail.com').split(',')
        )
    
    @staticmethod
    def load_from_file(settings_path: str = 'email_config.json') -> EmailConfig:
        """Carrega configurações de arquivo JSON"""
        try:
            settings_file = Path(settings_path)
            if settings_file.exists():
                with open(settings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return EmailConfig(**data)
        except Exception as e:
            logger.warning(f"Erro ao carregar config do arquivo: {e}")
        
        return ConfigManager.load_from_env()

class HandleMail:
    _email_lock = Lock()
    _last_email_time: Dict[str, float] = {}
    EMAIL_COOLDOWN = 300  # 5 minutos
    MAX_RETRIES = 3
    RETRY_DELAY = 5  # segundos entre tentativas
    
    _settings: Optional[EmailConfig] = None

    @classmethod
    def initialize(cls, settings: Optional[EmailConfig] = None):
        """Inicializa a classe com configuração de email"""
        if settings:
            cls._settings = settings
        else:
            cls._settings = ConfigManager.load_from_file()
        
        logger.info("HandleMail inicializado com configurações de email")

    @classmethod
    def get_settings(cls) -> EmailConfig:
        """Obtém a configuração atual, inicializando se necessário"""
        if cls._settings is None:
            cls.initialize()
        return cls._settings #type:ignore

    @classmethod
    def send(cls, data: Any) -> bool:
        """Envia email de alerta baseado nos dados recebidos"""
        if isinstance(data, dict):
            try:
                hospital_name = data.get("Hospital", "Unknown")
                logger.info(f"Processando dados para hospital: {hospital_name}")
                
                if not cls._should_send_email(hospital_name):
                    return False
                
                if data.get("tipo") == "usina":
                    return cls._handle_usina_email(data)
                else:
                    return cls._handle_hospital_email(data)
        
            except Exception as e:
                logger.error(f"Erro geral no HandleMail.enviar: {e}")
                return False
        else:
            return cls._send_offline_mail(str(data))

    @staticmethod
    def __safe_get(value: Any, default: Any) -> Any:
        """Retorna 'default' se value for None ou não numérico."""
        if value is None:
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default

    @classmethod
    def _send_offline_mail(cls, data: str) -> bool:
        """Envia email para dispositivo offline"""
        title = 'ALERTA: Conexão do Dispositivo!'
        return cls.__send_email_sync(title, data)

    @classmethod
    def __send_email_smtp(cls, title: str, body: str) -> bool:
        """Envia email usando SMTP"""
        try:
            settings = cls.get_settings()
            
            if not settings.username or not settings.password:
                logger.error("Credenciais de email não configuradas")
                return False
            
            msg = MIMEMultipart()
            msg['From'] = settings.from_email or settings.username
            msg['To'] = ', '.join(settings.to_emails)
            msg['Subject'] = title
            
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            server = smtplib.SMTP(settings.host, settings.port, timeout=15)
            
            if settings.use_tls:
                server.starttls()
            
            server.login(settings.username, settings.password)
            text = msg.as_string()
            server.sendmail(settings.from_email or settings.username, settings.to_emails, text)
            server.quit()
            
            logger.info(f"Email enviado com sucesso: {title}")
            return True
            
        except Exception as e:
            logger.error(f"Erro no envio SMTP: {e}")
            return False

    @classmethod
    def __send_email_sync(cls, title: str, body: str) -> bool:
        """Função auxiliar para envio síncrono de email com retry"""
        
        settings = cls.get_settings()
        
        if not settings.username or not settings.host:
            logger.warning("Configurações de email não encontradas")
            return False

        for attempt in range(cls.MAX_RETRIES):
            try:
                logger.info(f"Tentativa {attempt + 1} de envio de email: {title}")
                
                if cls.__send_email_smtp(title, body):
                    return True
                
                if attempt < cls.MAX_RETRIES - 1:
                    logger.info(f"Aguardando {cls.RETRY_DELAY}s antes da próxima tentativa...")
                    time.sleep(cls.RETRY_DELAY)
                    
            except Exception as e:
                logger.error(f"Erro na tentativa {attempt + 1}: {e}")
                if attempt < cls.MAX_RETRIES - 1:
                    time.sleep(cls.RETRY_DELAY)
        
        logger.error(f"Falha em todas as {cls.MAX_RETRIES} tentativas de envio")
        return False

    @classmethod
    def __send_email(cls, title: str, body: str, timeout: int = 30) -> bool:
        """Envia email com timeout usando threading"""
        result: List[bool] = [False]
        exception_info: List[Optional[str]] = [None]
        
        def email_worker():
            try:
                with cls._email_lock:
                    result[0] = cls.__send_email_sync(title, body)
            except Exception as e:
                exception_info[0] = str(e)
                logger.error(f"Erro no worker de email: {e}")
        
        email_thread = threading.Thread(target=email_worker, daemon=True)
        email_thread.start()
        
        email_thread.join(timeout=timeout)
        
        if email_thread.is_alive():
            logger.error(f"Timeout ao enviar email '{title}' após {timeout}s")
            return False
        
        if exception_info[0]:
            logger.error(f"Erro ao enviar email: {exception_info[0]}")
            return False
            
        return result[0]

    @classmethod
    def _should_send_email(cls, hospital_name: str) -> bool:
        """Verifica se deve enviar email baseado no cooldown"""
        current_time = time.time()
        last_time = cls._last_email_time.get(hospital_name, 0)
        
        if current_time - last_time > cls.EMAIL_COOLDOWN:
            cls._last_email_time[hospital_name] = current_time
            return True
        
        logger.info(f"Email bloqueado por cooldown para {hospital_name} (últimos {(current_time - last_time):.0f}s)")
        return False


    @classmethod
    def _handle_usina_email(cls, data: Dict[str, Any]) -> bool:
        """Processa alertas de usina"""
        psa = data.get("Data", {}).get("usina", {})
        central = data.get("Data", {}).get("central", {})

        fault_conditions = []
        
        purity = cls.__safe_get(psa.get("Purity"), 200)
        if purity < 90.0:
            fault_conditions.append(f"Pureza baixa: {purity}%")
        
        product_pressure = cls.__safe_get(psa.get("product_pressure"), 20)
        if product_pressure < 5.0:
            fault_conditions.append(f"Pressão do produto baixa: {product_pressure}")
        
        pressure = cls.__safe_get(central.get("pressure"), 20)
        if pressure < 5.0:
            fault_conditions.append(f"Pressão central baixa: {pressure}")
        
        dew_point = cls.__safe_get(central.get("dew_point"), -100)
        if dew_point > -45.0:
            fault_conditions.append(f"Ponto de orvalho alto: {dew_point}")

        pipeline = cls.__safe_get(central.get("rede"), 20)
        if pipeline < 5:
            fault_conditions.append(f"Pressão da rede baixa: {pipeline}")
        
        if cls.__safe_get(central.get("RST"), "Default") == "FALHA":
            fault_conditions.append("Falha RST detectada")
        
        if cls.__safe_get(central.get("BE"), "Default") == "FALHA":
            fault_conditions.append("Botão de emergência acionado")

        if fault_conditions:
            logger.info(f"Problemas detectados na usina {data['Hospital']}: {fault_conditions}")
            body = (
                f'ALERTA: Problemas detectados na Usina {data["Hospital"]}\n\n'
                f'Problemas identificados:\n' + 
                '\n'.join(f'- {problema}' for problema in fault_conditions) +
                f'\n\nDados completos da usina:\n{json.dumps(psa, indent=2, ensure_ascii=False)}\n\n'
                f'Dados completos da central:\n{json.dumps(central, indent=2, ensure_ascii=False)}'
            )
            
            return cls.__send_email(f'ALERTA Usina {data["Hospital"]}', body)
        
        return False

    @classmethod
    def _handle_hospital_email(cls, data: Dict[str, Any]) -> bool:
        """Processa alertas de hospital"""
        hospital = data.get("Data", {})
        
        fault_conditons = []
        
        pressure = cls.__safe_get(hospital.get("pressure"), 20)
        if pressure < 5:
            fault_conditons.append(f"Pressão baixa: {pressure}")
        
        pipeline = cls.__safe_get(hospital.get("rede"), 20)
        if pipeline < 5:
            fault_conditons.append(f"Pressão da rede baixa: {pipeline}")
        
        dew_point = cls.__safe_get(hospital.get("dew_point"), -100)
        if dew_point > -45.0:
            fault_conditons.append(f"Ponto de orvalho alto: {dew_point}")
        
        if cls.__safe_get(hospital.get("RST"), "Default") == "FALHA":
            fault_conditons.append("Falha RST detectada")
        
        if cls.__safe_get(hospital.get("BE"), "Default") == "FALHA":
            fault_conditons.append("Botão de emergência acionado")

        if fault_conditons:
            logger.info(f"Problemas detectados no hospital {data['Hospital']}: {fault_conditons}")
            body = (
                f'ALERTA: Problemas detectados no Hospital {data["Hospital"]}\n\n'
                f'Problemas identificados:\n' + 
                '\n'.join(f'- {problema}' for problema in fault_conditons) +
                f'\n\nDados completos:\n{json.dumps(hospital, indent=2, ensure_ascii=False)}'
            )
            
            return cls.__send_email(f'ALERTA Hospital {data["Hospital"]}', body)
        else:
            logger.info(f"Nenhum problema detectado no hospital {data['Hospital']}")
        
        return False
    
