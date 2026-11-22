"""Roteiro de demonstracao para o modo `--provedor simulado` (NAO e um LLM).

Reproduz o fluxo do agente no cenario da Questao 11: planejar a tarde do professor e,
depois, replanejar quando a reuniao muda de horario.
"""
import json


def _acao(ferramenta, args, pensamento):
    return json.dumps({"pensamento": pensamento, "acao": {"ferramenta": ferramenta, "args": args}},
                      ensure_ascii=False)


def _obs_do_turno(msgs):
    obs = []
    for m in reversed(msgs):
        if m["role"] == "user" and not m["content"].startswith(("OBSERVACAO:", "SISTEMA:")):
            break
        if m["role"] == "user" and m["content"].startswith("OBSERVACAO:"):
            obs.append(json.loads(m["content"][len("OBSERVACAO:"):]))
    return list(reversed(obs))


def _resposta(msgs):
    obs = _obs_do_turno(msgs)
    plano = next(o for o in reversed(obs) if "plano" in o)
    linhas = ["Proponho este plano (voce decide se aceita):"]
    linhas += [f"- {p['inicio']}-{p['fim']}: {p['nome']}" for p in plano["plano"]]
    for o in obs:
        if o.get("status") == "adiada" and o.get("motivo") == "inviavel_com_as_obrigatorias":
            d = o["detalhe"]
            linhas.append(f"Adiei {o['tarefa']}: com as tarefas que vencem hoje ela exigiria "
                          f"{d['minutos_necessarios']} min e a janela tem {d['minutos_disponiveis']} min. "
                          f"O prazo e {o['prazo']}, entao ainda da tempo.")
    return json.dumps({"pensamento": "plano validado e adiadas explicadas",
                       "resposta": "\n".join(linhas)}, ensure_ascii=False)


def roteiro_demo():
    A = dict(id="A", nome="Preparar aula de IA", duracao_min=90, prioridade="alta", vence_hoje=True, prazo="hoje")
    B = dict(id="B", nome="Corrigir trabalhos", duracao_min=120, prioridade="media", vence_hoje=False, prazo="amanha")
    C = dict(id="C", nome="Reuniao de pesquisa", duracao_min=60, prioridade="alta", vence_hoje=True,
             prazo="hoje", inicio_fixo="16:00")
    D = dict(id="D", nome="Revisar artigo", duracao_min=60, prioridade="baixa", vence_hoje=False,
             prazo="proxima semana")
    C17 = dict(C, inicio_fixo="17:00")
    return [
        _acao("definir_janela", {"inicio": "14:00", "fim": "18:00"}, "o usuario tem 14h-18h"),
        _acao("registrar_tarefas", {"tarefas": [A, B, C, D]}, "extrair tarefas, prioridades e prazos"),
        _acao("planejar", {}, "calcular o plano com o solver"),
        _acao("validar_plano", {}, "verificar o plano antes de apresentar"),
        _acao("explicar_tarefa", {"id": "B"}, "B ficou fora do plano: buscar evidencia"),
        _resposta,
        _acao("registrar_tarefas", {"tarefas": [C17]}, "a reuniao passou para as 17h"),
        _acao("planejar", {}, "replanejar"),
        _acao("validar_plano", {}, "verificar de novo"),
        _acao("explicar_tarefa", {"id": "B"}, "B continua adiada: buscar evidencia"),
        _resposta,
    ]
