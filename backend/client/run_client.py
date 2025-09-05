from src.mqtt_handler import MqttHandler
import os
from dotenv import load_dotenv

def run_mqtt():

    load_dotenv()

    broker = str(os.getenv('BROKER'))
    port = 8883
    user = str(os.getenv('USER_BROKER'))
    password = str(os.getenv('PASSWORD_BROKER'))
    topics = str(os.getenv('TOPICS'))
   
    redis_host = 'localhost'
    redis_port = 6379
    redis_db = 0
    redis_password = None
    
    client = MqttHandler(broker, port, user, password, topics)
    client.set_redis_connection(host=redis_host,
                                port=redis_port,
                                db=redis_db,
                                password=redis_password)
    client.run_mqtt_client()


if __name__ == '__main__':
    run_mqtt()