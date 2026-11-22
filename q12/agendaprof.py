"""AgendaProf: assistente de agenda para professores (interface em linguagem natural, no terminal).

Uso:  python agendaprof.py --provedor anthropic|openai|simulado
Comandos: /estado (mostra tarefas e janela), /sair
"""
import argparse
import json
import os
import time

from agente import Agente
from llm import criar_llm


def resumo(obj, limite=170):
    s = json.dumps(obj, ensure_ascii=False)
    return s if len(s) <= limite else s[:limite] + "..."


def main():
    ap = argparse.ArgumentParser(description="AgendaProf")
    ap.add_argument("--provedor", choices=["anthropic", "openai", "simulado"], default="anthropic")
    ap.add_argument("--modelo", help="nome do modelo (ou use a variavel AGENDAPROF_MODELO)")
    ap.add_argument("--sem-evidencias", action="store_true", help="oculta as chamadas de ferramenta")
    args = ap.parse_args()

    os.makedirs("logs", exist_ok=True)
    caminho_log = time.strftime("logs/sessao-%Y%m%d-%H%M%S.jsonl")
    with open(caminho_log, "w", encoding="utf-8") as log:
        agente = Agente(criar_llm(args.provedor, args.modelo), log=log)
        print("AgendaProf - descreva suas atividades e o tempo que voce tem. (/estado, /sair)")
        if args.provedor == "simulado":
            print("[MODO SIMULADO: respostas pre-definidas para teste; nao e um LLM]")
        print(f"[registro da sessao: {caminho_log}]")
        while True:
            try:
                texto = input("\nVoce: ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if texto in ("/sair", "sair"):
                break
            if not texto:
                continue
            if texto == "/estado":
                print(resumo(agente.f_listar_estado(), 2000))
                continue
            r = agente.turno(texto)
            if not args.sem_evidencias:
                for e in r.trace:
                    print(f"  [ferramenta] {e['ferramenta']} -> {resumo(e['resultado'])}")
            print("\nAgendaProf:", r.texto)
            for a in r.avisos:
                print("  [aviso]", a)


if __name__ == "__main__":
    main()
