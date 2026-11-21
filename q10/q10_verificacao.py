import heapq, itertools
E = {("A","B"):4,("A","D"):3,("B","C"):5,("B","E"):2,("C","F"):2,("D","E"):4,
     ("D","G"):6,("E","F"):3,("E","H"):5,("F","I"):4,("G","H"):3,("H","I"):2}
adj={}
for (u,v),c in E.items():
    adj.setdefault(u,{})[v]=c; adj.setdefault(v,{})[u]=c
H={"A":10,"B":8,"C":6,"D":9,"E":6,"F":4,"G":5,"H":2,"I":0}
nb=lambda n: sorted(adj[n])
def path(par,n):
    p=[n]
    while par[n] is not None: n=par[n]; p.append(n)
    return p[::-1]
def cost(p): return sum(adj[a][b] for a,b in zip(p,p[1:]))

def bfs():
    # teste de objetivo na geracao
    par={"A":None}; fr=["A"]; exp=[]
    while fr:
        n=fr.pop(0); exp.append(n)
        for m in nb(n):
            if m not in par:
                par[m]=n
                if m=="I": return exp,path(par,m)
                fr.append(m)
def dfs():
    par={"A":None}; fr=["A"]; exp=[]
    while fr:
        n=fr.pop(); exp.append(n)
        for m in reversed(nb(n)):    # menor ordem alfabetica sai primeiro
            if m not in par:
                par[m]=n
                if m=="I": return exp,path(par,m)
                fr.append(m)
def best(h, trace=True):
    g={"A":0}; par={"A":None}; fr=[(h["A"],"A")]; done=set(); exp=[]; log=[]
    while fr:
        f,n=heapq.heappop(fr)
        if n in done: continue
        if f!=g[n]+h[n]: continue
        done.add(n); exp.append(n)
        log.append((n,g[n],h[n],g[n]+h[n]))
        if n=="I": return exp,path(par,n),log
        for m in nb(n):
            ng=g[n]+adj[n][m]
            if m not in g or ng<g[m]:
                g[m]=ng; par[m]=n; heapq.heappush(fr,(ng+h[m],m))
Z={k:0 for k in H}
for nome,r in [("BFS",bfs()),("DFS",dfs())]:
    print(nome,"expansao:",r[0],"rota:",r[1],"custo",cost(r[1]),"expandidos",len(r[0]))
for nome,h in [("UCS",Z),("A*",H)]:
    e,p,log=best(h)
    print(nome,"expansao:",e,"rota:",p,"custo",cost(p),"expandidos",len(e))
    for l in log: print("   ",l)
# admissibilidade/consistencia
import math
dist={n:math.inf for n in H}; dist["I"]=0; pq=[(0,"I")]
while pq:
    d,n=heapq.heappop(pq)
    if d>dist[n]: continue
    for m,c in adj[n].items():
        if d+c<dist[m]: dist[m]=d+c; heapq.heappush(pq,(d+c,m))
print("h*:",dist)
print("admissivel:",all(H[n]<=dist[n] for n in H))
print("consistente:",all(H[u]<=c+H[v] and H[v]<=c+H[u] for (u,v),c in E.items()))
# traco detalhado do A* e UCS com fronteira
def trace(h):
    g={"A":0}; par={"A":None}; fr=[(h["A"],"A")]; done=set()
    while fr:
        f,n=heapq.heappop(fr)
        if n in done or f!=g[n]+h[n]: continue
        done.add(n)
        print(f"expande {n}: g={g[n]} h={h[n]} f={f}")
        if n=="I": return
        for m in nb(n):
            ng=g[n]+adj[n][m]
            if m not in g or ng<g[m]:
                g[m]=ng; par[m]=n; heapq.heappush(fr,(ng+h[m],m))
        print("   fronteira:",sorted([(ff,x,g[x]) for ff,x in fr if x not in done and ff==g[x]+h[x]]))
print("--- UCS"); trace(Z)
print("--- A*"); trace(H)
# problema modificado
def best2(h):
    s0=("A",False,False)
    def flags(n,d,f): return (n,d or n=="D",f or n=="F")
    g={s0:0}; par={s0:None}; fr=[(h["A"],s0)]; done=set(); exp=[]
    while fr:
        f,s=heapq.heappop(fr)
        if s in done or f!=g[s]+h[s[0]]: continue
        done.add(s); exp.append(s)
        if s[0]=="I" and s[1] and s[2]:
            p=[]; x=s
            while x: p.append(x); x=par[x]
            return exp,p[::-1],g[s]
        for m in nb(s[0]):
            t=flags(m,s[1],s[2]); ng=g[s]+adj[s[0]][m]
            if t not in g or ng<g[t]:
                g[t]=ng; par[t]=s; heapq.heappush(fr,(ng+h[m],t))
for nome,h in [("UCS",Z),("A*",H)]:
    e,p,c=best2(h)
    print("MOD",nome,"custo",c,"expandidos",len(e)); print("  rota",[x[0] for x in p]); print("  estados",[(x[0],int(x[1]),int(x[2])) for x in p])
def sp(a,b):
    d={n:math.inf for n in H}; d[a]=0; pq=[(0,a)]
    while pq:
        x,n=heapq.heappop(pq)
        if x>d[n]: continue
        for m,c in adj[n].items():
            if x+c<d[m]: d[m]=x+c; heapq.heappush(pq,(x+c,m))
    return d[b]
print("ordem D->F:",sp("A","D"),sp("D","F"),sp("F","I"),"=",sp("A","D")+sp("D","F")+sp("F","I"))
print("ordem F->D:",sp("A","F"),sp("F","D"),sp("D","I"),"=",sp("A","F")+sp("F","D")+sp("D","I"))
