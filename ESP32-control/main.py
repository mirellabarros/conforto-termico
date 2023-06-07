# ***************************************
# Pesquisa Conforto Térmico - IFSC SJ
# Cliente MQTT com ESP32, DHT22 e Relé
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
# led_ac = Pin(13, Pin.OUT, value=0)
led_sensor = Pin(12, Pin.OUT, value=0)

rele_ac = Pin(13, Pin.OUT, value=0)
rele_ventilador = Pin(14, Pin.OUT, value=1)

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
topic_sub_ac = 'esp/ac/status'
topic_sub_ventilador = 'esp/ventilador/status'
topic_pub_sensor = 'esp/dht/0'

# Parâmetros de tempo
last_sensor_reading = time() - 30
readings_interval = 30 # intervalo de leitura do sensor
last_ac_start = time() - 105
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


def readChannel(channel):
    adc.setCompareChannels(channel)
    adc.startSingleMeasurement()
    while adc.isBusy():
        pass
    voltage = adc.getResult_V()
    return voltage


def pisca_led():
    agora = time()
    while time() < agora + 1:
        led_sensor.value(not led_sensor.value())
        sleep(.1)
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
      print('Leituras de sensor inválidas.')
  except OSError as e:
    print('Falha ao ler o sensor.')


def sub_cb(topic, msg):
    
    if topic == b'esp/ac/status':
        global last_ac_start
        if (time() - last_ac_start) > ac_interval:
            if msg == b'1':
                rele_ac.value(1)
                print("Ar-condicionado ligado.")
                last_ac_start = time()
            elif msg == b'0':
                rele_ac.value(0)
                last_ac_start = time()
            
            
    if topic == b'esp/ventilador/status':
        if msg == b'1':
            rele_ventilador.value(1)
            print("Ventilador ligado.")
        else:
            rele_ventilador.value(0)
     
     
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
        
        
