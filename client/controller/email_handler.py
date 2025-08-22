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
            host=os.getenv('EMAIL_HOST', 'smtp.gmail.com'),
            port=int(os.getenv('EMAIL_PORT', '587')),
            username=os.getenv('EMAIL_USERNAME', ''),
            password=os.getenv('EMAIL_PASSWORD', ''),
            use_tls=os.getenv('EMAIL_USE_TLS', 'true').lower() == 'true',
            from_email=os.getenv('EMAIL_FROM', ''),
            to_emails=os.getenv('EMAIL_TO', 'danilocrautomacao@gmail.com').split(',')
        )
    
    @staticmethod
    def load_from_file(config_path: str = 'email_config.json') -> EmailConfig:
        """Carrega configurações de arquivo JSON"""
        try:
            config_file = Path(config_path)
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return EmailConfig(**data)
        except Exception as e:
            logger.warning(f"Erro ao carregar config do arquivo: {e}")
        
        return ConfigManager.load_from_env()

class HandleMail:
    # Lock para evitar envio simultâneo de muitos emails
    _email_lock = Lock()
    # Cache para evitar spam de emails (hospital -> último envio)
    _last_email_time: Dict[str, float] = {}
    # Tempo mínimo entre emails para o mesmo hospital (em segundos)
    EMAIL_COOLDOWN = 300  # 5 minutos
    MAX_RETRIES = 3
    RETRY_DELAY = 5  # segundos entre tentativas
    
    # Configuração de email
    _config: Optional[EmailConfig] = None

    @classmethod
    def initialize(cls, config: Optional[EmailConfig] = None):
        """Inicializa a classe com configuração de email"""
        if config:
            cls._config = config
        else:
            cls._config = ConfigManager.load_from_file()
        
        logger.info("HandleMail inicializado com configurações de email")

    @classmethod
    def get_config(cls) -> EmailConfig:
        """Obtém a configuração atual, inicializando se necessário"""
        if cls._config is None:
            cls.initialize()
        return cls._config #type:ignore

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
    def __test_smtp_connection(cls) -> bool:
        """Testa a conectividade SMTP"""
        try:
            config = cls.get_config()
            
            logger.info(f"Testando conexão SMTP com {config.host}:{config.port}")
            
            # Tentar conexão básica
            server = smtplib.SMTP(config.host, config.port, timeout=10)
            if config.use_tls:
                server.starttls()
            
            if config.username and config.password:
                server.login(config.username, config.password)
            
            server.quit()
            
            logger.info("Teste de conexão SMTP: SUCESSO")
            return True
            
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"Erro de autenticação SMTP: {e}")
            return False
        except smtplib.SMTPConnectError as e:
            logger.error(f"Erro de conexão SMTP: {e}")
            return False
        except socket.timeout as e:
            logger.error(f"Timeout na conexão SMTP: {e}")
            return False
        except Exception as e:
            logger.error(f"Erro geral no teste SMTP: {e}")
            return False

    @classmethod
    def __enviar_email_smtp(cls, titulo: str, corpo: str) -> bool:
        """Envia email usando SMTP"""
        try:
            config = cls.get_config()
            
            if not config.username or not config.password:
                logger.error("Credenciais de email não configuradas")
                return False
            
            msg = MIMEMultipart()
            msg['From'] = config.from_email or config.username
            msg['To'] = ', '.join(config.to_emails)
            msg['Subject'] = titulo
            
            msg.attach(MIMEText(corpo, 'plain', 'utf-8'))
            
            server = smtplib.SMTP(config.host, config.port, timeout=15)
            
            if config.use_tls:
                server.starttls()
            
            server.login(config.username, config.password)
            text = msg.as_string()
            server.sendmail(config.from_email or config.username, config.to_emails, text)
            server.quit()
            
            logger.info(f"Email enviado com sucesso: {titulo}")
            return True
            
        except Exception as e:
            logger.error(f"Erro no envio SMTP: {e}")
            return False

    @classmethod
    def __enviar_email_sync(cls, titulo: str, corpo: str) -> bool:
        """Função auxiliar para envio síncrono de email com retry"""
        
        config = cls.get_config()
        
        # Verificar configurações básicas
        if not config.username or not config.host:
            logger.warning("Configurações de email não encontradas")
            return False

        # Tentar múltiplas vezes
        for tentativa in range(cls.MAX_RETRIES):
            try:
                logger.info(f"Tentativa {tentativa + 1} de envio de email: {titulo}")
                
                if cls.__enviar_email_smtp(titulo, corpo):
                    return True
                
                # Se falhar, aguardar antes da próxima tentativa
                if tentativa < cls.MAX_RETRIES - 1:
                    logger.info(f"Aguardando {cls.RETRY_DELAY}s antes da próxima tentativa...")
                    time.sleep(cls.RETRY_DELAY)
                    
            except Exception as e:
                logger.error(f"Erro na tentativa {tentativa + 1}: {e}")
                if tentativa < cls.MAX_RETRIES - 1:
                    time.sleep(cls.RETRY_DELAY)
        
        logger.error(f"Falha em todas as {cls.MAX_RETRIES} tentativas de envio")
        return False

    @classmethod
    def __enviar_email(cls, titulo: str, corpo: str, timeout: int = 30) -> bool:
        """Envia email com timeout usando threading"""
        result: List[bool] = [False]
        exception_info: List[Optional[str]] = [None]
        
        def email_worker():
            try:
                with cls._email_lock:
                    result[0] = cls.__enviar_email_sync(titulo, corpo)
            except Exception as e:
                exception_info[0] = str(e)
                logger.error(f"Erro no worker de email: {e}")
        
        # Criar e iniciar thread
        email_thread = threading.Thread(target=email_worker, daemon=True)
        email_thread.start()
        
        # Aguardar com timeout
        email_thread.join(timeout=timeout)
        
        if email_thread.is_alive():
            logger.error(f"Timeout ao enviar email '{titulo}' após {timeout}s")
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
    def test_email_config(cls) -> bool:
        """Método para testar configuração de email"""
        logger.info("=== TESTE DE CONFIGURAÇÃO DE EMAIL ===")
        
        config = cls.get_config()
        
        # Verificar configurações
        logger.info(f"HOST: {config.host}")
        logger.info(f"PORT: {config.port}")
        logger.info(f"USERNAME: {config.username}")
        logger.info(f"PASSWORD: {'***' if config.password else 'NÃO CONFIGURADO'}")
        logger.info(f"USE_TLS: {config.use_tls}")
        logger.info(f"FROM_EMAIL: {config.from_email}")
        logger.info(f"TO_EMAILS: {config.to_emails}")
        
        # Testar conectividade
        if cls.__test_smtp_connection():
            logger.info("Teste de conectividade: PASSOU")
            
            # Tentar enviar email de teste
            try:
                success = cls.__enviar_email("Teste de Email", "Este é um email de teste do sistema MQTT.")
                logger.info(f"Teste de envio: {'SUCESSO' if success else 'FALHOU'}")
                return success
            except Exception as e:
                logger.error(f"Erro no teste de envio: {e}")
                return False
        else:
            logger.error("Teste de conectividade: FALHOU")
            return False

    @classmethod
    def enviar(cls, dados: Any) -> bool:
        """Envia email de alerta baseado nos dados recebidos"""
        if isinstance(dados, dict):
            try:
                hospital_name = dados.get("Hospital", "Unknown")
                logger.info(f"Processando dados para hospital: {hospital_name}")
                
                # Verificar cooldown para evitar spam
                if not cls._should_send_email(hospital_name):
                    return False
                
                if dados.get("tipo") == "usina":
                    return cls._handle_usina_email(dados)
                else:
                    return cls._handle_hospital_email(dados)
        
            except Exception as e:
                logger.error(f"Erro geral no HandleMail.enviar: {e}")
                return False
        else:
            return cls._send_offline_mail(str(dados))

    @classmethod
    def _handle_usina_email(cls, dados: Dict[str, Any]) -> bool:
        """Processa alertas de usina"""
        usina = dados.get("Data", {}).get("usina", {})
        central = dados.get("Data", {}).get("central", {})

        condicoes_problemas = []
        
        # Verificar cada condição e criar lista de problemas
        purity = cls.__safe_get(usina.get("Purity"), 200)
        if purity < 90.0:
            condicoes_problemas.append(f"Pureza baixa: {purity}%")
        
        product_pressure = cls.__safe_get(usina.get("product_pressure"), 20)
        if product_pressure < 5.0:
            condicoes_problemas.append(f"Pressão do produto baixa: {product_pressure}")
        
        pressure = cls.__safe_get(central.get("pressure"), 20)
        if pressure < 5.0:
            condicoes_problemas.append(f"Pressão central baixa: {pressure}")
        
        dew_point = cls.__safe_get(central.get("dew_point"), -100)
        if dew_point > -45.0:
            condicoes_problemas.append(f"Ponto de orvalho alto: {dew_point}")

        rede = cls.__safe_get(central.get("rede"), 20)
        if rede < 5:
            condicoes_problemas.append(f"Pressão da rede baixa: {rede}")
        
        if cls.__safe_get(central.get("RST"), "Default") == "FALHA":
            condicoes_problemas.append("Falha RST detectada")
        
        if cls.__safe_get(central.get("BE"), "Default") == "FALHA":
            condicoes_problemas.append("Botão de emergência acionado")

        if condicoes_problemas:
            logger.info(f"Problemas detectados na usina {dados['Hospital']}: {condicoes_problemas}")
            corpo = (
                f'ALERTA: Problemas detectados na Usina {dados["Hospital"]}\n\n'
                f'Problemas identificados:\n' + 
                '\n'.join(f'- {problema}' for problema in condicoes_problemas) +
                f'\n\nDados completos da usina:\n{json.dumps(usina, indent=2, ensure_ascii=False)}\n\n'
                f'Dados completos da central:\n{json.dumps(central, indent=2, ensure_ascii=False)}'
            )
            
            return cls.__enviar_email(f'ALERTA Usina {dados["Hospital"]}', corpo)
        
        return False

    @classmethod
    def _handle_hospital_email(cls, dados: Dict[str, Any]) -> bool:
        """Processa alertas de hospital"""
        hospital = dados.get("Data", {})
        
        condicoes_problemas = []
        
        # Verificar cada condição e criar lista de problemas
        pressure = cls.__safe_get(hospital.get("pressure"), 20)
        if pressure < 5:
            condicoes_problemas.append(f"Pressão baixa: {pressure}")
        
        rede = cls.__safe_get(hospital.get("rede"), 20)
        if rede < 5:
            condicoes_problemas.append(f"Pressão da rede baixa: {rede}")
        
        dew_point = cls.__safe_get(hospital.get("dew_point"), -100)
        if dew_point > -45.0:
            condicoes_problemas.append(f"Ponto de orvalho alto: {dew_point}")
        
        if cls.__safe_get(hospital.get("RST"), "Default") == "FALHA":
            condicoes_problemas.append("Falha RST detectada")
        
        if cls.__safe_get(hospital.get("BE"), "Default") == "FALHA":
            condicoes_problemas.append("Botão de emergência acionado")

        if condicoes_problemas:
            logger.info(f"Problemas detectados no hospital {dados['Hospital']}: {condicoes_problemas}")
            corpo = (
                f'ALERTA: Problemas detectados no Hospital {dados["Hospital"]}\n\n'
                f'Problemas identificados:\n' + 
                '\n'.join(f'- {problema}' for problema in condicoes_problemas) +
                f'\n\nDados completos:\n{json.dumps(hospital, indent=2, ensure_ascii=False)}'
            )
            
            return cls.__enviar_email(f'ALERTA Hospital {dados["Hospital"]}', corpo)
        else:
            logger.info(f"Nenhum problema detectado no hospital {dados['Hospital']}")
        
        return False
    
    @classmethod
    def _send_offline_mail(cls, dados: str) -> bool:
        """Envia email para dispositivo offline"""
        titulo = 'ALERTA: Conexão do Dispositivo!'
        return cls.__enviar_email_sync(titulo, dados)

# Exemplo de uso e configuração
if __name__ == "__main__":
    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Exemplo 1: Configuração via variáveis de ambiente
    # Defina as seguintes variáveis de ambiente:
    # EMAIL_HOST, EMAIL_PORT, EMAIL_USERNAME, EMAIL_PASSWORD, EMAIL_TO
    
    # Exemplo 2: Configuração manual
    config = EmailConfig(
        host='smtp.gmail.com',
        port=587,
        username='seu_email@gmail.com',
        password='sua_senha_de_app',
        use_tls=True,
        to_emails=['destinatario@gmail.com']
    )
    
    # Inicializar com configuração
    HandleMail.initialize(config)
    
    # Testar configuração
    HandleMail.test_email_config()
    
    # Exemplo de dados para teste
    dados_teste = {
        "Hospital": "Hospital Teste",
        "tipo": "hospital",
        "Data": {
            "pressure": 3.0,  # Pressão baixa para disparar alerta
            "rede": 15.0,
            "dew_point": -50.0,
            "RST": "OK",
            "BE": "OK"
        }
    }
    
    # Enviar email de teste
    HandleMail.enviar(dados_teste)