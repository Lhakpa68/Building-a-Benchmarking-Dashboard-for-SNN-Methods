import json, math, sqlite3, statistics as st
import numpy as np
from scipy import stats
S={k:json.load(open(f"summary_{k}.json")) for k in ("C1","C2","A","S")}
C1=S["C1"]; B=sorted(C1["times"]); Ns=["100","500","1000","5000","10000"]
db=sqlite3.connect("c1.db")
def runs(b,task,n,phase="simulate"):
    fw,bk=b.split("/")
    return [r for r in db.execute("select runtime_s,cpu_pct,peak_rss_mb,energy_j from runs where framework=? and backend=? and task=? and network_size=? and phase=? order by run_index",(fw,bk,task,n,phase))]
F={}
inf={x["b"]:x for x in C1["inference"]}
F["inf"]=inf
CTRL={"reference/vectorised","reference/scalar"}; CD={"brian2/cpp_standalone"}
fw_rows=[b for b in B if b not in CTRL|CD]
fastest_fw=min(fw_rows,key=lambda b:inf[b]["med"])
slowest_fw=max(fw_rows,key=lambda b:inf[b]["med"])
F["fastest_fw"]=fastest_fw; F["slowest_fw"]=slowest_fw
F["spread_fw"]=inf[slowest_fw]["med"]/inf[fastest_fw]["med"]
F["spread_all"]=inf["brian2/cpp_standalone"]["med"]/inf[fastest_fw]["med"]
# Table 4.2 vs fastest framework config, d = (other - base)/pooled sd, Holm over all 55 pairs
pw={(p["a"],p["b"]):p for p in C1["pairwise"]}
def pair(a,b):
    return pw.get((a,b)) or pw.get((b,a))
t42=[]
base=[r[0] for r in runs(fastest_fw,"inference",100)]
for b in sorted(B,key=lambda b:inf[b]["med"]):
    if b==fastest_fw: continue
    x=[r[0] for r in runs(b,"inference",100)]
    sp=math.sqrt(((len(x)-1)*np.var(x,ddof=1)+(len(base)-1)*np.var(base,ddof=1))/(len(x)+len(base)-2))
    d=(np.mean(x)-np.mean(base))/sp
    p=pair(b,fastest_fw)
    t42.append(dict(b=b,ratio=inf[b]["med"]/inf[fastest_fw]["med"],d=d,p=p["p_holm"],sep=p["p_holm"]<0.05))
F["t42"]=t42
F["pairs_sep"]=C1["pairs_separated"]; F["pairs_ns"]=C1["pairs_not_separated"]
F["shapiro_reject"]=[b for b,p in C1["shapiro"].items() if p<0.05]
F["cv_range_all"]=(min(inf[b]["cv"] for b in B),max(inf[b]["cv"] for b in B))
F["cv_min_b"]=min(B,key=lambda b:inf[b]["cv"]); F["cv_max_b"]=max(B,key=lambda b:inf[b]["cv"])
F["cv_fw"]=(min(fw_rows+list(CD),key=lambda b:inf[b]["cv"]),max(fw_rows+list(CD),key=lambda b:inf[b]["cv"]))
print(json.dumps(F,indent=0,default=float)[:6000])
json.dump(F,open("facts.json","w"),default=float)
