import paho.mqtt.client as mqtt

class MqttClient:
    def __init__(self, broker: str, port: int, 
                 username: str, password: str, topic: str) -> None:
        '''
        inicia a instancia da classe com os requisistos para conexao com o broker,
        porem é preciso usar o metodo da classe run_mqtt_client(), para efetuar a conexao
        e começar a receber as mensagens

        Exemplo de uso:
                        client = MqttClient(broker="broker", port=8883, 
                                            username="name", password="pass", 
                                            topic='#')
                        client.run_mqtt_client()
        '''
        self.broker = broker
        self.port = port
        self.username = username
        self.password = password
        self.topic = topic

    def on_connect(self, client, userdata, flags, rc) -> None:
        '''
        metodo padrao de conexao mqtt, a lib paho-mqtt espera essa classe para
        poder começar a conexao
        '''

    def on_message(self, client, userdata, msg) -> None:
        ''' metodo para receber as mensagens
        apartir desse metodo, vamos começar as escritas no banco de dados, substituindo de acordo com
        o nome do hostpital
        '''
        

    def run_mqtt_client(self):
        '''Metodo que inicia o cliente mqtt'''
        client = mqtt.Client()
        client.on_connect = self.on_connect
        client.on_message = self.on_message

        client.username_pw_set(self.username, self.password)
        client.tls_set()

        client.connect(self.broker, self.port, 60)
        client.loop_forever()