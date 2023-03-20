import matplotlib.pyplot as plt
from sqlalchemy import create_engine, text
import pandas as pd

# Informações do Servidor MySql
servidor_mysql = '192.168.50.58'
usuario_mysql = 'root'
senha_mysql = 'paulvandyk11'
banco_de_dados = 'confterm'

leitura = 16
query0 = f"""SELECT datahora, pmv as sensor0 FROM pmvsensor WHERE sensor = 0 and idpmvdesc = {leitura}"""
query1 = f"""SELECT datahora, pmv as sensor1 FROM pmvsensor WHERE sensor = 1 and idpmvdesc = {leitura}"""
query2 = f"""SELECT datahora, pmv as sensor2 FROM pmvsensor WHERE sensor = 2 and idpmvdesc = {leitura}"""
query3 = f"""SELECT datahora, pmv as sensor3 FROM pmvsensor WHERE sensor = 3 and idpmvdesc = {leitura}"""

engine = create_engine(f'mysql+pymysql://{usuario_mysql}:{senha_mysql}@{servidor_mysql}/{banco_de_dados}')

with engine.begin() as conn:
    df0 = pd.read_sql_query(sql=text(query0), con=conn, parse_dates=['datahora'])
    # df1 = pd.read_sql_query(sql=text(query1), con=conn, parse_dates=['datahora'])
    df2 = pd.read_sql_query(sql=text(query2), con=conn, parse_dates=['datahora'])
    df3 = pd.read_sql_query(sql=text(query3), con=conn, parse_dates=['datahora'])

m = pd.merge(df0, df2, how='outer')
df = pd.merge(m, df3, how='outer')
df = df.sort_values(by=['datahora'])
df = df.set_index('datahora')

print(df)
df.plot(marker='o')

plt.title('Titulo do meu Gráfico')
plt.xlabel('Tempo')
plt.ylabel('PMV')

plt.show()
