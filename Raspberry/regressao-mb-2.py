
import math
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from sklearn.linear_model import LogisticRegression

# Lê o arquivo/dataset utilizando as colunas (se necessário) informadas
# usando a planilha gerada pelo professor
colunas = ["tdb", "rh", "met", "clo", "vr", "clo_d", "const", "Out_PMV"]
dataset = pd.read_csv("dataset_PMV_Python_Classifica_adaptado.csv", names=colunas, delimiter=",")


#########################################
# dimensões do dataset
# print(dataset.shape)
#
# # tipos de cada atributo
# print(dataset.dtypes)
#
# # primeiras linhas do dataset
# print(dataset.head())

#############################################################################

# Separação em conjuntos de treino e teste
# construção de um modelo preditivo.

array = dataset.values
X = array[:, 0:7].astype(object)  # contém todas as linhas e as colunas de índice 0 a 6 (7º índice não incluso)
Y = array[:, 7]
test_size = 0.30  # aqui 20% do total = 1344 linhas * 0.2 = 268.8
# Nesse caso: 20% = Teste e 80% = Treinamento --> Pode ser valores variados
seed = 7  # → interfere
X_train, X_test, Y_train, Y_test = train_test_split(X, Y, test_size=test_size, random_state=seed)

###################################################################

logistic_regression = LogisticRegression(solver="newton-cg", max_iter=100)
logistic_regression.fit(X_train, Y_train)

# Estimativa da acurácia no conjunto de teste
predictions = logistic_regression.predict(X_test)
print("Accuracy score: ", accuracy_score(Y_test, predictions))

# print("logistic_regression COEF")
# print(logistic_regression.coef_)  # Temos o mesmo modelo!


# import statsmodels.api as sm
# import statsmodels.formula.api as smf
#
# modelo = smf.glm(formula="Out_PMV ~ tdb + rh + met + clo + vr + clo_d", data=dataset, family = sm.families.Binomial()).fit()
# print(modelo.summary())     # INTERFERE NO VALOR FINAL DO PMV(OBS)!!!!


###################################################################################################
# Variáveis para determinar se vai ligar o AC

tdb1 = 26.1
tr1 = tdb1
v1 = 0.1
rh1 = 65
met1 = 1.2
clo1 = 0.57
vr1 = v1 + 0.3*(met1 - 1)
clo_d1 = clo1*(0.6 + 0.4/met1)

###################################################################################################

teste9 = {"tdb": tdb1, "rh": rh1, "met": met1, "clo": clo1, "vr": vr1, "clo_d": clo_d1, "const": 1}
dft = pd.DataFrame(data=teste9, index=[0])
print(dft)
resultado = logistic_regression.predict(dft)
resultado_formatado = ('{:.0f}'.format(resultado[0]))
print("Resultado ML: ", resultado_formatado)

#############################################################################################################

# COEFICIENTES BASEADOS NA TABELA SUMÁRIO GERADA ACIMA

coef_tdb = 3.948  # 2.1189
coef_tr = 0  # não usado 2.1189 --> tirou tr e v pois sempre são iguais
coef_v = 0  # não usado -13.2268
coef_rh = 0.128  # 0.1224
coef_met = -1.246
coef_clo= 30.5
coef_vr = 23.79 # 26.2092     --> (+) 26.870 / (-) 22.486
coef_clo_d = -6.685 # -8.1790  --> (+) -5.5431 / (-) -7.6851
intercept1 = -128

# Equação para comparação

tt22 = intercept1 + coef_tdb*tdb1 + coef_tr*tr1 + coef_v*v1 + coef_rh*rh1 + coef_met*met1 + coef_clo*clo1 \
       + coef_vr*vr1 + coef_clo_d*clo_d1
# print(tt22)
prob_evento = 1/(1 + math.exp(-tt22))
print("Resultado Equação: ", prob_evento)
# if prob_evento <= 0.25:
    # prob_evento = 0
# print(prob_evento)