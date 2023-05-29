# ***************************************
# Pesquisa Conforto Térmico - IFSC SJ
# Cliente MQTT com ESP32, DHT22 e Relé
# ***************************************

import time
from umqttsimple import MQTTClient
import ubinascii
import machine
import micropython
import network
import esp
import dht
esp.osdebug(None)
import gc
gc.collect()

sensor = dht.DHT22(machine.Pin(4))
led_wifi = machine.Pin(5, machine.Pin.OUT, value=0)
led_ac = machine.Pin(13, machine.Pin.OUT, value=0)
led_sensor = machine.Pin(12, machine.Pin.OUT, value=0)
rele = machine.Pin(14, machine.Pin.OUT, value=1)

# Informações da Rede Wi-FI
ssid = 'Conforto-Termico'
password = 'master1466'

# Informações do Servidor MQTT
mqtt_server = '10.0.0.50'
mqtt_user = 'admin'
mqtt_password = 'paulvandyk11'
client_id = ubinascii.hexlify(machine.unique_id())

# Tópicos
topic_sub_ac = 'esp/ac/status'
topic_sub_ventilador = 'esp/ventilador/status'
topic_pub_sensor = 'esp/dht/0'

# Parâmetros de tempo
last_sensor_reading = 0 
readings_interval = 30 # intervalo de leitura do sensor
last_ac_start = 0
ac_interval = 120 # tempo mínimo para manter o A/C ligado

# Conexão à rede wi-fi
station = network.WLAN(network.STA_IF)
station.active(True)
station.connect(ssid, password)

while station.isconnected() == False:
    pass

led_wifi.value(1)
print('Conexão realizada com sucesso!')
print(station.ifconfig())


def pisca_led():
    agora = time.time()
    while time.time() < agora + 1:
        led_sensor.value(not led_sensor.value())
        time.sleep(.1)
    led_sensor.value(0)


def read_sensor():
  try:
    sensor.measure()
    temp = sensor.temperature()
    hum = sensor.humidity()
    if (isinstance(temp, float) and isinstance(hum, float)) or (isinstance(temp, int) and isinstance(hum, int)):
      temp = (b'{0:3.1f}'.format(temp))
      hum =  (b'{0:3.1f}'.format(hum))
      pisca_led()
      return temp, hum
    else:
      return('Leituras de sensor inválidas.')
  except OSError as e:
    return('Falha ao ler o sensor.')

def sub_cb(topic, msg):
    
    if topic == b'esp/ac/status':
        global last_ac_start
        if msg == b'1' and (time.time() - last_ac_start) > ac_interval:
            led_ac.value(1)
            last_ac_start = time.time()
            print("Ar-condicionado ligado.")
        elif msg == b"0":
            led_ac.value(0)
            
    if topic == b'esp/ventilador/status':
        if msg == b'1':
            rele.value(1)
            print("Ventilador ligado.")
        else:
            rele.value(0)
        
def connect_and_subscribe():
    global client_id, mqtt_server, topic_sub_ac, topic_sub_ventilador
    client = MQTTClient(client_id, mqtt_server, user=mqtt_user, password=mqtt_password)
    client.set_callback(sub_cb)
    client.connect()
    client.subscribe(topic_sub_ac)
    client.subscribe(topic_sub_ventilador)
    print(f"Conectado ao servidor {mqtt_server} MQTT broker.")
    print(f"Inscrito nos tópicos: {topic_sub_ac}, {topic_sub_ventilador}")
    return client
    
def restart_and_reconnect():
    print('Falha ao conectar-se no MQTT broker. Reconectando...')
    time.sleep(20)
    machine.reset()
    
try:
    client = connect_and_subscribe()
except OSError as e:
    restart_and_reconnect()
    led_wifi.value(0)
while True:
    try:
        client.check_msg()
        
        if (time.time() - last_sensor_reading) > readings_interval:            
            temp, hum = read_sensor()
            dados = temp + ";" + hum
            client.publish(topic_pub_sensor, dados)
            print(f"Temperatura: {temp} | Umidade: {hum}")
            client.publish(topic_pub_sensor, dados)
            last_sensor_reading = time.time()
    except OSError as e:
        restart_and_reconnect()
        led_wifi.value(0)
        

