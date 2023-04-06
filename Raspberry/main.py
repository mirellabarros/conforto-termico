# *********************************************************
# Pesquisa Conforto Térmico — IFSC SJ
# Script de servidor para cálculo de PMV
# *********************************************************

from pythermalcomfort.models import pmv_ppd
from pythermalcomfort.utilities import v_relative, clo_dynamic
import paho.mqtt.client as mqtt
import random
import mysql.connector
from mysql.connector import Error

# Informações do Servidor MQTT
servidor_mqtt = '10.0.0.50'
porta_mqtt = 1883
usuario_mqtt = 'admin'
senha_mqtt = 'paulvandyk11'
id_mqtt = f'python-mqtt-{random.randint(0, 1000)}'

# Informações do Servidor MySql
servidor_mysql = '10.0.0.50'
usuario_mysql = 'root'
senha_mysql = 'paulvandyk11'
banco_de_dados = 'confterm'

# Tópicos Sensores
topic_sub_sensor0 = 'esp/dht/0'
topic_sub_sensor1 = 'esp/dht/1'
topic_sub_sensor2 = 'esp/dht/2'
topic_sub_sensor3 = 'esp/dht/3'
# o tópico 'esp/pmv/numero do sensor' é gerado em tempo de execução

# Tópicos Configurações
topic_pub_ac = 'esp/ac/status'
topic_pub_ventilador = 'esp/ventilador/status'
topic_pub_pmv = 'rasp/pmv'
topic_sub_met = 'rasp/config/met'
topic_sub_clo = 'rasp/config/clo'
topic_sub_objetivo = 'rasp/config/objetivo'

# Variáveis Pythermalcomfort
tdb = 0
tr = 0
rh = 0
v = 0.1
met = 0
clo = 0

# Variáveis de controle
arr_pmv = [0, 0, 0, 0]

# Variáveis do ar-condicionado para o ESP32
cfg_objetivo = 0


def opcoes_de_sistema():
    print("Deseja utilizar o ventilador?")
    ventilador = int(input("1: Sim | 0: Não: "))

    print("Deseja armazenar as informações no banco de dados?")
    armazenar_dados = int(input("1: Sim | 0: Não: "))

    if armazenar_dados:
        # Campo para o usuário informar um título para o conjunto de leituras
        # Ex.: 'Sala dos professores — Leitura 3'.
        print("Informe um identificador para esta coleta de dados.")
        print("Ex.: 'Sala dos professores - Leitura 3'.")
        dados_tag = input()

        # Campo para o usuário informar uma descrição detalhada para o conjunto de leituras
        # Ex.: 'Uso de ventilador apenas quando AC desligado'.
        print("Insira observações sobre o conjunto de leituras.")
        print("Ex.: 'Uso de ventilador apenas quando AC desligado'.")
        dados_comentarios = input()

        # Campo para limitar quantidade de leituras que serão salvas no banco de dados
        print("Informe a quantidade de leituras que deseja armazenar.")
        print("Digite '0' para salvar leituras ilimitadas.")
        total_leituras = int(input())

        # Salva os parâmetros no banco de dados
        query = f"INSERT INTO pmvdesc (tag, comentarios) VALUES ('{dados_tag}', '{dados_comentarios}')"
        conexao = conexao_banco_de_dados(servidor_mysql, usuario_mysql, senha_mysql, banco_de_dados)
        id_leitura = executa_query(conexao, query)
        conexao.close()

        # Informa o ID do conjunto de leituras para o usuário
        print('*****************************************************')
        print(f'O ID do conjunto de leituras é: {id_leitura}')
        print('*****************************************************')

    else:
        id_leitura = 0
        total_leituras = 0

    return ventilador, id_leitura, total_leituras


def calcula_pmv():
    # calculate relative air speed
    v_r = v_relative(v=v, met=met)
    # calculate dynamic clothing
    clo_d = clo_dynamic(clo=clo, met=met)
    results = pmv_ppd(tdb=tdb, tr=tr, vr=v_r, rh=rh, met=met, clo=clo_d, standard="ASHRAE", units="SI")
    return results['pmv']


def conexao_banco_de_dados(host_name, user_name, user_password, db_name):
    connection = None
    try:
        connection = mysql.connector.connect(
            host=host_name,
            user=user_name,
            passwd=user_password,
            database=db_name
        )
        print("Conexão com o banco de dados realizada com sucesso!")
    except Error as err:
        print(f"Erro: '{err}'")

    return connection


def executa_query(connection, query):
    cursor = connection.cursor()
    try:
        cursor.execute(query)
        connection.commit()
        print("Query executada.")
        return cursor.lastrowid
    except Error as err:
        print(f"Erro: '{err}'")


def salva_leitura(id_leitura, id_sensor, pmv, tdb, tr, rh, vel, met, clo, ac, servidor_mysql, usuario_mysql,
                  senha_mysql, banco_de_dados):
    query = f"INSERT INTO pmvsensor (idpmvdesc, sensor, pmv, tdb, tr, rh, vel, met, clo, ac) " \
            f"VALUES ({id_leitura}, {id_sensor}, {pmv}, {tdb}, {tr}, {rh}, {vel}, {met}, {clo}, {ac})"
    conexao = conexao_banco_de_dados(servidor_mysql, usuario_mysql, senha_mysql, banco_de_dados)
    executa_query(conexao, query)
    conexao.close()


def liga_ac(pmv, n):
    if pmv > (0.5 + n):
        return 1
    else:
        return 0


# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Conectado ao MQTT Broker!")
    else:
        print("Falha na conexão. Código %d\n", rc)

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    client.subscribe([(topic_sub_met, 2), (topic_sub_clo, 2), (topic_sub_objetivo, 2), (topic_sub_sensor0, 1),
                      (topic_sub_sensor1, 1), (topic_sub_sensor2, 1), (topic_sub_sensor3, 1)])


# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    print(f'Informação `{msg.payload.decode()}` recebida de `{msg.topic}`')

    global met, clo, cfg_objetivo, tdb, tr, rh, total_pmv, media_pmv, media_pmv, id_conjunto_leitura, \
        qtd_leituras, qtd_leituras_restantes

    if topic_sub_met in msg.topic:
        met = float(msg.payload.decode())

    if topic_sub_clo in msg.topic:
        clo = float(msg.payload.decode())

    if topic_sub_objetivo in msg.topic:
        cfg_objetivo = float(msg.payload.decode())

    if met != 0 and clo != 0:

        if 'esp/dht' in msg.topic:

            dados_sensor = msg.payload.decode()
            temp, hum = dados_sensor.split(";")

            tdb = round(float(temp), 2)
            tr = round(float(temp), 2)
            rh = round(float(hum), 2)

            topico = msg.topic.split("/")
            id_sensor = topico[2]
            arr_pmv[int(id_sensor)] = calcula_pmv()
            topic_pub_esp_pmv = 'esp/pmv/' + id_sensor

            # Reinicia a variável para calcular novamente o PMV médio na próxima passagem
            total_pmv = 0

            # Calcula o PMV médio atual (média aritmética simples)
            for pmv in arr_pmv:
                total_pmv += pmv
            media_pmv = total_pmv / len(arr_pmv)

            # Determina se o ar-condicionar deverá ser ligado ou desligado
            status_ar_condicionado = liga_ac(media_pmv, cfg_objetivo)

            # Grava as leituras dos sensores no banco de dados
            if id_conjunto_leitura:

                if qtd_leituras_restantes != 0:
                    salva_leitura(id_conjunto_leitura, id_sensor, arr_pmv[int(id_sensor)], tdb, tr, rh, v, met,
                                  clo, status_ar_condicionado, servidor_mysql, usuario_mysql, senha_mysql,
                                  banco_de_dados)
                    qtd_leituras_restantes -= 1
                    print("Leituras restantes:", qtd_leituras_restantes)

                elif qtd_leituras == 0:
                    salva_leitura(id_conjunto_leitura, id_sensor, arr_pmv[int(id_sensor)], tdb, tr, rh, v, met,
                                  clo, status_ar_condicionado, servidor_mysql, usuario_mysql, senha_mysql,
                                  banco_de_dados)

            c = 0
            for valor in arr_pmv:
                print("PMV no Sensor {0:1d}: {1:3.2f}".format(c, valor))
                c += 1

            print("PMV médio atual: {0:3.2f}".format(media_pmv))
            print("PMV alvo: {0:3.2f}".format(0.5 + cfg_objetivo))
            print("Status AC: ", "Ligado" if status_ar_condicionado == 1 else "Desligado")

            client.publish(topic_pub_esp_pmv, '{:.2f}'.format(arr_pmv[int(id_sensor)]))
            client.publish(topic_pub_pmv, '{:.2f}'.format(media_pmv))
            client.publish(topic_pub_ac, status_ar_condicionado)
    else:
        print("MET e CLO não informados.")


client = mqtt.Client(id_mqtt)
client.username_pw_set(usuario_mqtt, senha_mqtt)
client.on_connect = on_connect
client.on_message = on_message
client.connect(servidor_mqtt, porta_mqtt, 60)

# Blocking call that processes network traffic, dispatches callbacks and
# handles reconnecting.
# Other loop*() functions are available that give a threaded interface and a
# manual interface.
print("*****************************************************")
print("Instituto Federal de Santa Catarina - Campus São José")
print("Pesquisa: Conforto Térmico")
print("*****************************************************")
usar_ventilador, id_conjunto_leitura, qtd_leituras = opcoes_de_sistema()
qtd_leituras_restantes = qtd_leituras
client.publish(topic_pub_ventilador, usar_ventilador, qos=1, retain=True)
client.loop_forever()
