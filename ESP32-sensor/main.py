# ***************************************
# Pesquisa Conforto Térmico - IFSC SJ
# Teste de Cliente MQTT com ESP32 e DHT22
# ***************************************

from time import sleep, time
from umqttsimple import MQTTClient
import ubinascii
from machine import Pin, SoftI2C, reset, unique_id
import micropython
import network
import esp
import dht
esp.osdebug(None)
import gc
gc.collect()
from ADS1115 import *

sensor = dht.DHT22(Pin(4))
led_wifi = Pin(5, Pin.OUT, value=0)
led_sensor = Pin(18, Pin.OUT, value=0)

# ADS1115
ADS1115_ADDRESS = 0x49

i2c = SoftI2C(scl=Pin(22), sda=Pin(21), freq=40000)
adc = ADS1115(ADS1115_ADDRESS, i2c=i2c)

adc.setVoltageRange_mV(ADS1115_RANGE_4096)
adc.setCompareChannels(ADS1115_COMP_0_GND)
adc.setMeasureMode(ADS1115_SINGLE)

# Informações da Rede Wi-FI
ssid = 'Conforto-Termico'
password = 'master1466'

# Informações do Servidor MQTT
mqtt_server = '10.0.0.50'
mqtt_user = 'admin'
mqtt_password = 'paulvandyk11'
client_id = ubinascii.hexlify(unique_id())

# Tópicos
topic_sub = 'esp/ac/status'
topic_pub_sensor = 'esp/dht/1'

# Parâmetros de tempo
last_sensor_reading = time() - 30
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


def readChannel(channel):
    adc.setCompareChannels(channel)
    adc.startSingleMeasurement()
    while adc.isBusy():
        pass
    voltage = adc.getResult_V()
    return voltage


def pisca_led():
    agora = time()
    while time() < agora + 2:
        led_sensor.value(not led_sensor.value())
        sleep(.1)
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
      print('Leituras de sensor inválidas.')
  except OSError as e:
    print('Falha ao ler o sensor.')


def connect_and_subscribe():
    global client_id, mqtt_server, topic_sub
    client = MQTTClient(client_id, mqtt_server, user=mqtt_user, password=mqtt_password)
    client.connect()
    print(f'Conectado ao servidor {mqtt_server} MQTT broker')
    return client


def restart_and_reconnect():
    print('Falha ao se conectrar ao MQTT broker. Reconectando...')
    sleep(20)
    reset()


try:
    client = connect_and_subscribe()
except OSError as e:
    restart_and_reconnect()
    led_wifi.value(0)
while True:
    try:
        client.check_msg()
        
        if (time() - last_sensor_reading) > readings_interval:            
            temp, hum = read_sensor()
            kimo = readChannel(ADS1115_COMP_3_GND)
            kimo = ("{:<4.2f}".format(kimo))
            dados = temp + ";" + hum + ";" + kimo
            client.publish(topic_pub_sensor, dados)
            print(f"Temperatura: {temp} | Umidade: {hum} | Vento: {kimo}")
            
            last_sensor_reading = time()
            
    except OSError as e:
        restart_and_reconnect()
        led_wifi.value(0)