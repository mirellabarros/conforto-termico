# ***************************************
# Pesquisa Conforto Térmico - IFSC SJ
# Teste de Cliente MQTT com ESP32 e DHT22
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
led_sensor = machine.Pin(18, machine.Pin.OUT, value=0)

# Informações da Rede Wi-FI
ssid = 'MirellaLarissa_24Ghz'
password = 'morumtri2020'

# Informações do Servidor MQTT
mqtt_server = '192.168.50.58'
mqtt_user = 'admin'
mqtt_password = 'paulvandyk11'
client_id = ubinascii.hexlify(machine.unique_id())

# Tópicos
topic_sub = 'esp/ac/status'
topic_pub_sensor1 = 'esp/dht/3'

# Parâmetros de tempo
last_sensor_reading = 0 
readings_interval = 30 # intervalo de leitura do sensor

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
    while time.time() < agora + 2:
        led_sensor.value(not led_sensor.value())
        time.sleep(.1)
    led_sensor.value(0)


def read_sensor():
  try:
    sensor.measure()
    temp = sensor.temperature()
    hum = sensor.humidity()
    if (isinstance(temp, float) and isinstance(hum, float)) or (isinstance(temp, int) and isinstance(hum, int)):
      temp = ("{0:3.1f}".format(temp))
      hum =  ("{0:3.1f}".format(hum))
      pisca_led()
      return temp, hum
    else:
      return('Leituras de sensor inválidas.')
  except OSError as e:
    return('Falha ao ler o sensor.')
        
def connect_and_subscribe():
    global client_id, mqtt_server, topic_sub
    client = MQTTClient(client_id, mqtt_server, user=mqtt_user, password=mqtt_password)
    client.connect()
    print(f'Conectado ao servidor {mqtt_server} MQTT broker')
    return client
    
def restart_and_reconnect():
    print('Falha ao se conectrar ao MQTT broker. Reconectando...')
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
            client.publish(topic_pub_sensor1, dados)
            print(f"Temperatura: {temp} | Umidade: {hum}")
            last_sensor_reading = time.time()
    except OSError as e:
        restart_and_reconnect()
        led_wifi.value(0)

