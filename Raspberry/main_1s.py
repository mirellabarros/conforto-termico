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
import math
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from sklearn.linear_model import LogisticRegression

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
v = 0
met = 0
clo = 0

# Variáveis de velocidade de vento fixas
arr_vento = [0, 0, 0, 0]

# Variáveis de controle
arr_pmv = [0, 0, 0, 0]
arr_eq = [0, 0, 0, 0]
arr_ml = [0, 0, 0, 0]

# Variáveis do ar-condicionado para o ESP32
cfg_objetivo = 0


def opcoes_de_sistema():
    print("Quantos sensores serão utilizados?")
    total_sensores = int(input("Quantidade de sensores (1 a 4): "))

    print("-----------------------------------------------------")

    for i in range(total_sensores):

        print(f"Deseja utilizar valores fixos de vento para o Sensor '{i}'?")
        fixar_vento = int(input("1: Sim | 0: Não: "))

        if fixar_vento:
            arr_vento[i] = float(input(f"Valor do vento no Sensor '{i}': "))

        print("-----------------------------------------------------")

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

    return ventilador, id_leitura, total_leituras, total_sensores


def calcula_pmv():
    # calculate relative air speed
    v_r = v_relative(v=v, met=met)
    # calculate dynamic clothing
    clo_d = clo_dynamic(clo=clo, met=met)
    results = pmv_ppd(tdb=tdb, tr=tr, vr=v_r, rh=rh, met=met, clo=clo_d, standard="ASHRAE")
    return results['pmv']


def eq_regressao_logistica():
    # Coeficientes da equação para determinar se o ar-condicionado deve ser ligado ou desligado.
    coeficiente_tdb = 3.948
    coeficiente_tr = 0
    coeficiente_v = 0
    coeficiente_rh = 0.128
    coeficiente_met = -1.246
    coeficiente_clo = 30.5
    coeficiente_vr = 23.79
    coeficiente_clo_d = -6.685
    intercept1 = -128

    vr = v + 0.3 * (met - 1)
    clo_d = clo * (0.6 + 0.4 / met)

    # Equação
    eq = intercept1 + coeficiente_tdb * tdb + coeficiente_tr * tr + coeficiente_v * v + coeficiente_rh * rh \
           + coeficiente_met * met + coeficiente_clo * clo + coeficiente_vr * vr + coeficiente_clo_d * clo_d
    probabilidade = 1 / (1 + math.exp(-eq))

    # Resultado do tipo float
    # Ligar o ar-condicionado caso o valor seja maior que 0.4
    return 1 if probabilidade > 0.4 else 0


def ml_regressao_logistica():
    vr = v + 0.3 * (met - 1)
    clo_d = clo * (0.6 + 0.4 / met)
    dados = {"tdb": tdb, "rh": rh, "met": met, "clo": clo, "vr": vr, "clo_d": clo_d, "const": 1}
    dft = pd.DataFrame(data=dados, index=[0])
    resultado = logistic_regression.predict(dft)
    resultado_formatado = ('{:.0f}'.format(resultado[0]))
    return resultado_formatado


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

    global met, clo, cfg_objetivo, tdb, tr, rh, v, total_pmv, media_pmv, id_conjunto_leitura, \
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
            temp, hum, vel = dados_sensor.split(";")

            topico = msg.topic.split("/")
            id_sensor = topico[2]

            if arr_vento[int(id_sensor)]:
                v = arr_vento[int(id_sensor)]
            else:
                v = round(float(vel), 2)

            tdb = round(float(temp), 2)
            tr = round(float(temp), 2)
            rh = round(float(hum), 2)

            arr_pmv[int(id_sensor)] = calcula_pmv()
            arr_eq[int(id_sensor)] = eq_regressao_logistica()
            arr_ml[int(id_sensor)] = ml_regressao_logistica()

            topic_pub_esp_pmv = 'esp/pmv/' + id_sensor

            # Reinicia a variável para calcular novamente o PMV médio na próxima passagem
            total_pmv = 0

            # Calcula o PMV médio atual (média aritmética simples)
            for i in range(qtd_sensores):
                total_pmv += arr_pmv[i]
            media_pmv = total_pmv / qtd_sensores

            # Determina se o ar-condicionar deverá ser ligado ou desligado
            status_ar_condicionado = liga_ac(media_pmv, cfg_objetivo)

            # Grava as leituras dos sensores no banco de dados
            if id_conjunto_leitura:

                if qtd_leituras_restantes != 0:

                    query = f"INSERT INTO pmvsensor (idpmvdesc, sensor, pmv, tdb, tr, rh, vel, met, clo, ac, " \
                            f"equacao, ml) VALUES ({id_conjunto_leitura}, {id_sensor}, {arr_pmv[int(id_sensor)]}, " \
                            f"{tdb}, {tr}, {rh}, {vel}, {met}, {clo}, {status_ar_condicionado}, " \
                            f"{arr_eq[int(id_sensor)]}, {arr_ml[int(id_sensor)]})"
                    conexao = conexao_banco_de_dados(servidor_mysql, usuario_mysql, senha_mysql, banco_de_dados)
                    executa_query(conexao, query)
                    conexao.close()

                    qtd_leituras_restantes -= 1
                    print("Leituras restantes:", qtd_leituras_restantes)

                elif qtd_leituras == 0:
                    query = f"INSERT INTO pmvsensor (idpmvdesc, sensor, pmv, tdb, tr, rh, vel, met, clo, ac, " \
                            f"equacao, ml) VALUES ({id_conjunto_leitura}, {id_sensor}, {arr_pmv[int(id_sensor)]}, " \
                            f"{tdb}, {tr}, {rh}, {vel}, {met}, {clo}, {status_ar_condicionado}, " \
                            f"{arr_eq[int(id_sensor)]}, {arr_ml[int(id_sensor)]})"
                    conexao = conexao_banco_de_dados(servidor_mysql, usuario_mysql, senha_mysql, banco_de_dados)
                    executa_query(conexao, query)
                    conexao.close()

            for i in range(qtd_sensores):
                print("PMV no Sensor {0:1d}: {1:3.2f} - Equação: {0:1d} - ML: {0:1d}".format(i, arr_pmv[i],
                                                                                             arr_eq[i], arr_ml[i]))

            print("PMV médio atual: {0:3.2f}".format(media_pmv))
            print("PMV alvo: {0:3.2f}".format(0.5 + cfg_objetivo))
            print("Status AC: ", "Ligado" if status_ar_condicionado == 1 else "Desligado")

            client.publish(topic_pub_esp_pmv, '{:.2f}'.format(arr_pmv[int(id_sensor)]))
            client.publish(topic_pub_pmv, '{:.2f}'.format(media_pmv))
            client.publish(topic_pub_ac, status_ar_condicionado)
    else:
        print("MET e CLO não informados.")


# Blocking call that processes network traffic, dispatches callbacks and
# handles reconnecting.
# Other loop*() functions are available that give a threaded interface and a
# manual interface.
print("*****************************************************")
print("Instituto Federal de Santa Catarina - Campus São José")
print("Pesquisa: Conforto Térmico")
print("*****************************************************")
# Inicia o programa realizando a conexão com o servidor MQTT
print("Iniciando conexão com o servidor MQTT...")
client = mqtt.Client(id_mqtt)
client.username_pw_set(usuario_mqtt, senha_mqtt)
client.on_connect = on_connect
client.on_message = on_message
client.connect(servidor_mqtt, porta_mqtt, 60)

#############################################################################
# Prepara o arquivo CSV para o machine learning
# Lê o arquivo/dataset utilizando as colunas (se necessário) informadas
print("Lendo o dataset para regressão logística...")
colunas = ["tdb", "rh", "met", "clo", "vr", "clo_d", "const", "Out_PMV"]
dataset = pd.read_csv("dataset_PMV_Python_Classifica_adaptado.csv", names=colunas, delimiter=",")

array = dataset.values
X = array[:, 0:7].astype(object)  # contém todas as linhas e as colunas de índice 0 a 6 (7º índice não incluso)
Y = array[:, 7]
test_size = 0.30  # aqui 20% do total = 1344 linhas * 0.2 = 268.8
# Nesse caso: 20% = Teste e 80% = Treinamento --> Pode ser valores variados
seed = 7  # → interfere
X_train, X_test, Y_train, Y_test = train_test_split(X, Y, test_size=test_size, random_state=seed)

logistic_regression = LogisticRegression(solver="newton-cg", max_iter=100)
logistic_regression.fit(X_train, Y_train)
# Estimativa da acurácia no conjunto de teste
predictions = logistic_regression.predict(X_test)
print("Acurácia no conjunto de teste: ", accuracy_score(Y_test, predictions))
print("*****************************************************")
#############################################################################
# Inicia as opções do sistema
usar_ventilador, id_conjunto_leitura, qtd_leituras, qtd_sensores = opcoes_de_sistema()
qtd_leituras_restantes = qtd_leituras
#############################################################################
# Entra em loop
client.publish(topic_pub_ventilador, usar_ventilador, qos=1, retain=True)
client.loop_forever()
