from controller.mqtt_handler import MqttHandler
import os
from dotenv import load_dotenv

def run_mqtt():

    load_dotenv()

    broker = str(os.getenv('BROKER'))
    port = 8883
    user = str(os.getenv('USER_BROKER'))
    password = str(os.getenv('PASSWORD_BROKER'))
    topics = str(os.getenv('TOPICS'))
   
    client = MqttHandler(broker, port, user, password, topics)
    client.run_mqtt_client()