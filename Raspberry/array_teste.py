import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

tabela_1 = pd.DataFrame({
    'data': ['2023-02-23 22:33:43', '2023-02-23 22:34:43', '2023-02-23 22:35:43', '2023-02-23 22:36:43'],
    's1': [0.5, 0.7, 0.6, 0.8]})

tabela_2 = pd.DataFrame({
    'data': ['2023-02-23 22:32:23', '2023-02-23 22:33:23', '2023-02-23 22:34:59', '2023-02-23 22:35:58',
             '2023-02-23 22:36:52'],
    's2': [0.5, 0.6, 0.5, 0.4, 0.6]})

m = pd.merge(tabela_1, tabela_2, how='outer')
# Converte as datas para Datetime
m['data'] = pd.to_datetime(m['data'])
df = m.sort_values(by='data')
df = df.set_index('data')

print(df)

fig, axs = plt.subplots(figsize=(12, 6))
df.plot(ax='s1')
axs.set_title("Gráfico de PMV")
axs.set_ylabel("PMV")
axs.set_xlabel("Tempo")
plt.show()
