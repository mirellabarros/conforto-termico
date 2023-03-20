# *********************************************************
# Pesquisa Conforto Térmico — IFSC SJ
# Script para gerar gráficos de sensores
# *********************************************************

import matplotlib.pyplot as plt
import mysql.connector
from mysql.connector import Error
import pandas as pd

# Informações do Servidor MySql
servidor_mysql = '192.168.50.58'
usuario_mysql = 'root'
senha_mysql = 'paulvandyk11'
banco_de_dados = 'confterm'


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


def executa_query(connection, q):
    cursor = connection.cursor()
    result = None
    try:
        cursor.execute(q)
        result = cursor.fetchall()
        return result
    except Error as err:
        print(f"Error: '{err}'")


# Gera a lista conforme a quantidade de sensores
qtd_sensores = 4
sensores = [[[], []] for _ in range(qtd_sensores)]

print("*****************************************************")
print("Instituto Federal de Santa Catarina - Campus São José")
print("Pesquisa: Conforto Térmico - Plotar Gráfico")
print("*****************************************************")

# Realiza a conexão com o banco de dados
conexao = conexao_banco_de_dados(servidor_mysql, usuario_mysql, senha_mysql, banco_de_dados)

query = """SELECT p.idpmvdesc, p.datahora, p.tag, sensores.coletas FROM pmvdesc 
as p, (SELECT idpmvdesc, COUNT(idpmvdesc) as coletas FROM pmvsensor GROUP BY idpmvdesc) as sensores
WHERE p.idpmvdesc = sensores.idpmvdesc ORDER BY idpmvdesc DESC LIMIT 5;"""

resultados = executa_query(conexao, query)
from_db = []

for resultado in resultados:
    resultado = list(resultado)
    from_db.append(resultado)
columns = ["ID", "Data", "Tag", "Coletas"]
df = pd.DataFrame(from_db, columns=columns)
df = df.set_index("ID")
df["Data"] = df['Data'].dt.strftime('%d/%m/%Y %H:%M')

print("Últimas coletas realizadas:")
print(df)
leitura = int(input("Informe o ID da coleta: "))

plt.figure(figsize=(12, 8))
# Laço para a coleta de dados
s = 0
while s < qtd_sensores:

    query = f"""SELECT datahora, pmv FROM pmvsensor WHERE sensor = {s} and idpmvdesc = {leitura}"""
    resultados = executa_query(conexao, query)

    for i in resultados:
        sensores[s][0].append(i[0])
        sensores[s][1].append(i[1])

    sensores[s][0] = pd.to_datetime(sensores[s][0])
    plt.plot(sensores[s][0], sensores[s][1], label=f"Sensor {s}", linewidth=1, markersize=2, marker='o')
    s += 1

# Encerra a conexão com o banco de dados
conexao.close()

# Plota o gráfico
plt.title('Gráfico de PMV')
plt.xlabel('Período')
plt.ylabel('PMV')
plt.grid(True, color='#f1f1f1')
plt.legend(loc='best')
plt.gcf().autofmt_xdate()
plt.show()
