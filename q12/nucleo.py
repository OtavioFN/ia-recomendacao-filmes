"""Nucleo simbolico do AgendaProf: modelo de dados, solver, validador e explicador.

Tudo aqui e deterministico e nao usa LLM. O agente (agente.py) chama estas funcoes
como ferramentas; o LLM so interpreta o pedido e redige a resposta.
"""
import math
import unicodedata
from dataclasses import dataclass

PASSO = 15                                   # grade de 15 minutos
UTIL = {"alta": 3, "media": 2, "baixa": 1}   # utilidade por prioridade


def hhmm_para_min(s):
    h, m = s.strip().split(":")
    h, m = int(h), int(m)
    if not (0 <= h <= 23 and 0 <= m <= 59):
        raise ValueError(f"horario invalido: {s!r} (use HH:MM)")
    return h * 60 + m


def min_para_hhmm(m):
    return f"{m // 60:02d}:{m % 60:02d}"


def _sem_acento(s):
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


@dataclass
class Tarefa:
    id: str
    nome: str
    duracao_min: int
    prioridade: str            # alta | media | baixa
    vence_hoje: bool = False   # tarefas que vencem hoje sao obrigatorias
    prazo: str = ""            # texto livre ("amanha", "proxima semana")
    inicio_fixo: str = None    # "HH:MM" para compromissos fixos

    @property
    def utilidade(self):
        return UTIL[self.prioridade]


def criar_tarefa(d):
    """Valida os dados enviados pelo LLM e cria a Tarefa. Devolve (tarefa, avisos)."""
    avisos = []
    for campo in ("id", "nome", "duracao_min", "prioridade"):
        if d.get(campo) in (None, ""):
            raise ValueError(f"campo obrigatorio ausente: {campo!r}"
                             " (pergunte ao usuario em vez de supor)")
    prio = _sem_acento(str(d["prioridade"]).strip().lower())
    if prio not in UTIL:
        raise ValueError(f"prioridade invalida: {d['prioridade']!r} (use alta, media ou baixa)")
    try:
        dur = int(d["duracao_min"])
    except (TypeError, ValueError):
        raise ValueError(f"duracao_min invalida: {d['duracao_min']!r}")
    if dur <= 0:
        raise ValueError("duracao_min deve ser positiva")
    if dur % PASSO:
        arred = math.ceil(dur / PASSO) * PASSO
        avisos.append(f"duracao de {d['id']} arredondada de {dur} para {arred} min (grade de {PASSO} min)")
        dur = arred
    fixo = d.get("inicio_fixo")
    if fixo:
        hhmm_para_min(fixo)  # valida o formato
    t = Tarefa(id=str(d["id"]).strip(), nome=str(d["nome"]).strip(), duracao_min=dur,
               prioridade=prio, vence_hoje=bool(d.get("vence_hoje", False)),
               prazo=str(d.get("prazo") or ""), inicio_fixo=fixo or None)
    return t, avisos


@dataclass
class Resultado:
    plano: dict          # id -> minuto de inicio (None se nao ha plano viavel)
    utilidade: int
    falha: dict = None   # diagnostico quando nao ha plano


def resolver(tarefas, ini, fim, forcar=(), proibir=()):
    """Busca exaustiva com poda (branch and bound) pelo plano de maior utilidade.

    Restricoes: tarefas dentro da janela [ini, fim], sem sobreposicao, sem divisao,
    inicio fixo respeitado, tarefas que vencem hoje (ou em `forcar`) obrigatorias.
    Desempate: minimizar a soma (inicio x utilidade), isto e, tarefas mais importantes
    comecam primeiro. Adequado para ate ~10 tarefas.
    """
    n = (fim - ini) // PASSO
    cand = [t for t in tarefas if t.id not in proibir]
    obrig = {t.id for t in cand if t.vence_hoje} | (set(forcar) - set(proibir))
    posicoes = {}
    for t in cand:
        d = t.duracao_min // PASSO
        if t.inicio_fixo:
            delta = hhmm_para_min(t.inicio_fixo) - ini
            s = delta // PASSO
            ok = delta % PASSO == 0 and s >= 0 and s + d <= n
            posicoes[t.id] = [s] if ok else []
        else:
            posicoes[t.id] = list(range(0, n - d + 1))
    ordem = sorted(cand, key=lambda t: (t.inicio_fixo is None, t.id not in obrig, -t.utilidade))
    resto = [0] * (len(ordem) + 1)
    for i in range(len(ordem) - 1, -1, -1):
        resto[i] = resto[i + 1] + ordem[i].utilidade
    melhor = {"chave": None, "plano": None}

    def rec(i, ocup, plano, util, soma):
        if i == len(ordem):
            if obrig <= set(plano):
                chave = (util, -soma)
                if melhor["chave"] is None or chave > melhor["chave"]:
                    melhor["chave"], melhor["plano"] = chave, dict(plano)
            return
        if melhor["chave"] is not None and util + resto[i] < melhor["chave"][0]:
            return
        t = ordem[i]
        d = t.duracao_min // PASSO
        for s in posicoes[t.id]:
            m = ((1 << d) - 1) << s
            if not ocup & m:
                plano[t.id] = s
                rec(i + 1, ocup | m, plano, util + t.utilidade, soma + s * t.utilidade)
                del plano[t.id]
        if t.id not in obrig:
            rec(i + 1, ocup, plano, util, soma)

    rec(0, 0, {}, 0, 0)
    if melhor["plano"] is None:
        return Resultado(None, 0, _diagnostico([t for t in cand if t.id in obrig], posicoes, ini, fim))
    return Resultado({k: ini + v * PASSO for k, v in melhor["plano"].items()}, melhor["chave"][0])


def _diagnostico(obrigatorias, posicoes, ini, fim):
    total = sum(t.duracao_min for t in obrigatorias)
    for t in obrigatorias:
        if not posicoes[t.id]:
            return {"motivo": "obrigatoria_sem_horario_valido", "tarefa": t.id,
                    "detalhe": "inicio fixo fora da janela ou da grade"}
    if total > fim - ini:
        return {"motivo": "tempo_insuficiente", "minutos_necessarios": total,
                "minutos_disponiveis": fim - ini,
                "tarefas": [t.id for t in obrigatorias]}
    return {"motivo": "sem_arranjo_continuo", "minutos_necessarios": total,
            "minutos_disponiveis": fim - ini, "tarefas": [t.id for t in obrigatorias]}


def validar(plano, tarefas, ini, fim):
    """Verificador independente do solver: devolve a lista de violacoes (vazia = valido)."""
    viol = []
    blocos = []
    for tid, a in plano.items():
        t = tarefas.get(tid)
        if t is None:
            viol.append(f"tarefa desconhecida no plano: {tid}")
            continue
        b = a + t.duracao_min
        if a < ini or b > fim:
            viol.append(f"{tid} ({min_para_hhmm(a)}-{min_para_hhmm(b)}) fora da janela "
                        f"{min_para_hhmm(ini)}-{min_para_hhmm(fim)}")
        if t.inicio_fixo and a != hhmm_para_min(t.inicio_fixo):
            viol.append(f"{tid} deveria comecar as {t.inicio_fixo}, mas comeca as {min_para_hhmm(a)}")
        blocos.append((a, b, tid))
    blocos.sort()
    for (a1, b1, t1), (a2, b2, t2) in zip(blocos, blocos[1:]):
        if a2 < b1:
            viol.append(f"sobreposicao entre {t1} e {t2}")
    for t in tarefas.values():
        if t.vence_hoje and t.id not in plano:
            viol.append(f"{t.id} vence hoje e nao esta no plano")
    return viol


def explicar(tid, tarefas, ini, fim, plano):
    """Explicacao com evidencia: compara o plano otimo com o contrafactual da tarefa."""
    lista = list(tarefas.values())
    t = tarefas[tid]
    base = resolver(lista, ini, fim)
    if tid in plano:
        sem = resolver(lista, ini, fim, proibir={tid})
        motivo = ("compromisso_fixo" if t.inicio_fixo else
                  "obrigatoria_hoje" if t.vence_hoje else "aumenta_a_utilidade")
        return {"ok": True, "tarefa": tid, "status": "agendada",
                "inicio": min_para_hhmm(plano[tid]), "fim": min_para_hhmm(plano[tid] + t.duracao_min),
                "motivo": motivo, "utilidade_do_plano": base.utilidade,
                "utilidade_sem_ela": sem.utilidade if sem.plano is not None else None,
                "pode_ser_adiada": not t.vence_hoje}
    com = resolver(lista, ini, fim, forcar={tid})
    ev = {"ok": True, "tarefa": tid, "status": "adiada", "prazo": t.prazo,
          "pode_ser_feita_depois": not t.vence_hoje, "utilidade_do_plano": base.utilidade}
    if com.plano is None:
        ev["motivo"] = "inviavel_com_as_obrigatorias"
        ev["detalhe"] = com.falha
    else:
        ev["utilidade_se_incluida"] = com.utilidade
        ev["tarefas_que_sairiam"] = sorted(set(plano) - set(com.plano))
        ev["motivo"] = "menor_utilidade" if com.utilidade < base.utilidade else "empate_de_utilidade"
    return ev
