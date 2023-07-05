from pythermalcomfort.models import pmv_ppd
from pythermalcomfort.utilities import v_relative, clo_dynamic

tdb = 18
tr = 18
rh = 79.1
v = 0.02
met = 1.4
clo = 0.67

# calculate relative air speed
v_r = v_relative(v=v, met=met)
# calculate dynamic clothing
clo_d = clo_dynamic(clo=clo, met=met)
results = pmv_ppd(tdb=tdb, tr=tr, vr=v_r, rh=rh, met=met, clo=clo_d, standard='ASHRAE')
print(results)

# {'pmv': 0.06, 'ppd': 5.1}
print(results["pmv"])
# -0.06

