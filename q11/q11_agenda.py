"""Agente classico para o cenario do professor (Questao 11): CSP + otimizacao por busca exaustiva."""
from itertools import product

PASSO = 15                       # minutos por posicao da grade
INICIO, FIM = 14 * 60, 18 * 60   # janela disponivel: 14h-18h
UTIL = {"Alta": 3, "Media": 2, "Baixa": 1}      # utilidade por prioridade

# nome: (duracao, prioridade, prazo_vence_hoje, inicio_fixo)
TAREFAS = {
    "A": (90,  "Alta",  True,  None),           # preparar aula de IA
    "B": (120, "Media", False, None),           # corrigir trabalhos (prazo: amanha)
    "C": (60,  "Alta",  True,  16 * 60),        # reuniao de pesquisa (16h-17h, fixa)
    "D": (60,  "Baixa", False, None),           # revisar artigo (prazo: proxima semana)
}
hhmm = lambda m: f"{m // 60:02d}h{m % 60:02d}"

def sem_sobreposicao(plano):
    ocup = sorted((ini, ini + TAREFAS[t][0]) for t, ini in plano.items())
    return all(a[1] <= b[0] for a, b in zip(ocup, ocup[1:]))

def gerar():
    """Gera todos os planos viaveis: cada tarefa ou fica fora (adiada) ou recebe um inicio."""
    posicoes = range(INICIO, FIM + 1, PASSO)
    opcoes = {}
    for t, (dur, _, _, fixo) in TAREFAS.items():
        ini = [fixo] if fixo is not None else [p for p in posicoes if p + dur <= FIM]
        opcoes[t] = [None] + ini                # None = nao executada hoje
    for escolha in product(*opcoes.values()):
        plano = {t: i for t, i in zip(TAREFAS, escolha) if i is not None}
        if "C" in plano and sem_sobreposicao(plano):   # compromisso fixo e obrigatorio
            yield plano

def utilidade(plano):  return sum(UTIL[TAREFAS[t][1]] for t in plano)
def respeita_prazos(plano):   # tarefas que vencem hoje precisam ser feitas hoje
    return all(t in plano for t, (_, _, hoje, _) in TAREFAS.items() if hoje)

planos = list(gerar())
validos = [p for p in planos if respeita_prazos(p)]
print(f"planos viaveis (sem sobreposicao, C fixa): {len(planos)}")
print(f"... que tambem cumprem os prazos de hoje (A e C): {len(validos)}")

# conjuntos de tarefas possiveis hoje
conjuntos = {}
for p in planos:
    conjuntos.setdefault(frozenset(p), 0)
    conjuntos[frozenset(p)] += 1
print("\nConjuntos de tarefas executaveis hoje (todos incluem C):")
for c in sorted(conjuntos, key=lambda s: (-utilidade(dict.fromkeys(s)), sorted(s))):
    ok = all(t in c for t, (_, _, hoje, _) in TAREFAS.items() if hoje)
    print(f"  {''.join(sorted(c)):<4} utilidade={utilidade(dict.fromkeys(c))}  prazos de hoje cumpridos: {'sim' if ok else 'NAO'}")

melhor = max(utilidade(p) for p in validos)
otimos = [p for p in validos if utilidade(p) == melhor]
print(f"\nutilidade maxima = {melhor}; planos otimos = {len(otimos)}")
# desempate: executar o mais cedo possivel (soma dos inicios minima)
canon = min(otimos, key=lambda p: sum(p.values()))
print("plano escolhido (desempate: mais cedo possivel):")
for t, ini in sorted(canon.items(), key=lambda x: x[1]):
    dur = TAREFAS[t][0]
    print(f"  {hhmm(ini)}-{hhmm(ini+dur)}  {t} ({dur} min, prioridade {TAREFAS[t][1]})")
print("adiadas:", sorted(set(TAREFAS) - set(canon)))
ocup = sum(TAREFAS[t][0] for t in canon)
print(f"minutos ocupados: {ocup} de {FIM-INICIO}; livres: {FIM-INICIO-ocup}")
print("variantes otimas com A em:", sorted({hhmm(p['A']) for p in otimos}))
