"""Aprendizagem em grafos de conhecimento: TransE (Bordes et al., 2013) para prever ligacoes ausentes.

Os dados sao SINTETICOS (gerados com sementes fixas): pesquisadores em comunidades tematicas.
Duas tarefas de completamento (parte das triplas e escondida):
  pesquisaEm : prever o tema principal de um pesquisador   (python aprendizagem.py pesquisaEm)
  escreveu   : prever quais artigos um pesquisador escreveu (python aprendizagem.py escreveu)
Metricas: MRR e Hits@k com ranqueamento filtrado. Dependencia: numpy.
"""
import itertools
import numpy as np

# ------------------------------------------------------------------ dados sinteticos
def gerar_grafo(semente=0, n_com=8, por_com=15, n_art=400):
    rng = np.random.default_rng(semente)
    pesq = [f"pesq{i}" for i in range(n_com * por_com)]
    com_de = {p: i // por_com for i, p in enumerate(pesq)}
    topicos = [f"topico{c}" for c in range(n_com)]
    venues = [f"venue{c}_{k}" for c in range(n_com) for k in range(2)]
    insts = [f"inst{k}" for k in range(8)]
    triplas, autores_de = [], {}
    for p in pesq:
        triplas.append((p, "pesquisaEm", topicos[com_de[p]]))   # tema principal = tema da comunidade
    for p in pesq:                                         # afiliacao: 70% segue a comunidade
        inst = insts[com_de[p] % 8] if rng.random() < 0.7 else insts[rng.integers(8)]
        triplas.append((p, "afiliadoA", inst))
    for k in range(n_art):
        art, c = f"art{k}", rng.integers(n_com)
        n_aut = rng.integers(2, 4)
        aut = set()
        while len(aut) < n_aut:                            # 85% dos autores vem da mesma comunidade
            c_aut = c if rng.random() < 0.85 else rng.integers(n_com)
            aut.add(pesq[c_aut * por_com + rng.integers(por_com)])
        autores_de[art] = sorted(aut)
        for a in aut:
            triplas.append((a, "escreveu", art))
        triplas.append((art, "trata", topicos[c]))
        if rng.random() < 0.3:
            triplas.append((art, "trata", topicos[rng.integers(n_com)]))
        triplas.append((art, "publicadoEm", venues[c * 2 + rng.integers(2)] if rng.random() < 0.8
                        else venues[rng.integers(len(venues))]))
    return sorted(set(triplas)), [f"art{k}" for k in range(n_art)], topicos


def dividir(triplas, relacao, semente=0, p_valid=0.10, p_teste=0.25):
    """Esconde triplas da `relacao` (valid/teste). Para `escreveu`, mantem cada artigo e pesquisador
    com >= 1 tripla dessa relacao no treino."""
    rng = np.random.default_rng(semente)
    alvo = [t for t in triplas if t[1] == relacao]
    rng.shuffle(alvo)
    n_art, n_pes = {}, {}
    for h, _, t in alvo:
        n_art[t] = n_art.get(t, 0) + 1
        n_pes[h] = n_pes.get(h, 0) + 1
    valid, teste = [], []
    n_v, n_t = int(p_valid * len(alvo)), int(p_teste * len(alvo))
    for h, r, t in alvo:
        if len(valid) + len(teste) >= n_v + n_t:
            break
        if relacao == "escreveu" and not (n_art[t] > 1 and n_pes[h] > 1):
            continue
        (valid if len(valid) < n_v else teste).append((h, r, t))
        n_art[t] -= 1
        n_pes[h] -= 1
    escondidas = set(valid) | set(teste)
    return [t for t in triplas if t not in escondidas], valid, teste


# ------------------------------------------------------------------ TransE
def treinar(treino, ent, rel, dim=32, margem=1.0, lr=0.03, epocas=200, lote=128, semente=0):
    rng = np.random.default_rng(semente)
    idx = np.array([(ent[h], rel[r], ent[t]) for h, r, t in treino])
    E = rng.uniform(-6 / np.sqrt(dim), 6 / np.sqrt(dim), (len(ent), dim))
    R = rng.uniform(-6 / np.sqrt(dim), 6 / np.sqrt(dim), (len(rel), dim))
    R /= np.linalg.norm(R, axis=1, keepdims=True)
    for _ in range(epocas):
        E /= np.linalg.norm(E, axis=1, keepdims=True)       # restricao de norma unitaria
        perm = rng.permutation(len(idx))
        for i in range(0, len(idx), lote):
            b = idx[perm[i:i + lote]]
            h, r, t = b[:, 0], b[:, 1], b[:, 2]
            troca_cab = rng.random(len(b)) < 0.5
            nh = np.where(troca_cab, rng.integers(0, len(ent), len(b)), h)
            nt = np.where(~troca_cab, rng.integers(0, len(ent), len(b)), t)
            pos, neg = E[h] + R[r] - E[t], E[nh] + R[r] - E[nt]
            dpos, dneg = (pos ** 2).sum(1), (neg ** 2).sum(1)
            ativo = (margem + dpos - dneg) > 0              # perda de margem: max(0, m + d(+) - d(-))
            if not ativo.any():
                continue
            gp, gn = 2 * pos[ativo], 2 * neg[ativo]
            np.add.at(E, h[ativo], -lr * gp); np.add.at(E, t[ativo], lr * gp)
            np.add.at(R, r[ativo], -lr * (gp - gn))
            np.add.at(E, nh[ativo], lr * gn); np.add.at(E, nt[ativo], -lr * gn)
    return E, R


# ------------------------------------------------------------------ avaliacao (ranqueamento filtrado)
def metricas(ranks):
    ranks = np.array(ranks)
    return {"MRR": float((1 / ranks).mean()), "Hits@1": float((ranks <= 1).mean()),
            "Hits@3": float((ranks <= 3).mean()), "Hits@10": float((ranks <= 10).mean())}


def avaliar(pontuar, alvos, conhecidas, candidatos):
    """pontuar(h, lista_de_candidatos) -> pontuacoes (maior = melhor). Empates contam como rank medio."""
    ranks = []
    for h, _, t in alvos:
        outros = [c for c in candidatos if c == t or c not in conhecidas[h]]   # filtra tails verdadeiros
        s = pontuar(h, outros)
        s_alvo = s[outros.index(t)]
        ranks.append(1 + (s > s_alvo).sum() + 0.5 * ((s == s_alvo).sum() - 1))
    return metricas(ranks)


def main(relacao="pesquisaEm"):
    triplas, artigos, topicos_lista = gerar_grafo()
    candidatos = topicos_lista if relacao == "pesquisaEm" else artigos
    treino, valid, teste = dividir(triplas, relacao)
    ent = {e: i for i, e in enumerate(sorted({x for h, _, t in triplas for x in (h, t)}))}
    rel = {r: i for i, r in enumerate(sorted({r for _, r, _ in triplas}))}
    conhecidas = {}
    for h, r, t in triplas:                                  # tudo que e verdadeiro (para o filtro)
        if r == relacao:
            conhecidas.setdefault(h, set()).add(t)
    print(f"tarefa: prever `{relacao}` | entidades: {len(ent)} | relacoes: {len(rel)} | triplas: {len(triplas)} "
          f"(treino {len(treino)}, validacao {len(valid)}, teste {len(teste)}) | candidatos: {len(candidatos)}")

    def pontuador(E, R):
        return lambda h, cs: -(((E[ent[h]] + R[rel[relacao]] - E[[ent[c] for c in cs]]) ** 2).sum(1))

    # ---- ajuste de hiperparametros na VALIDACAO (o teste nao e usado aqui)
    melhor = None
    for lr, ep in itertools.product([0.01, 0.03, 0.1], [100, 200]):
        E, R = treinar(treino, ent, rel, lr=lr, epocas=ep)
        m = avaliar(pontuador(E, R), valid, conhecidas, candidatos)["MRR"]
        print(f"  validacao: lr={lr}, epocas={ep} -> MRR {m:.3f}")
        if melhor is None or m > melhor[0]:
            melhor = (m, lr, ep)
    _, lr, ep = melhor
    print(f"hiperparametros escolhidos: lr={lr}, epocas={ep}")

    # ---- baselines (usam somente o treino)
    topicos_art, esc_treino = {}, {}
    for h, r, t in treino:
        if r == "escreveu":
            esc_treino.setdefault(h, []).append(t)
        if r == "trata":
            topicos_art.setdefault(h, []).append(t)
    if relacao == "pesquisaEm":      # caminho pesquisador -escreveu-> artigo -trata-> topico (frequencia)
        def base_caminhos(h, cs):
            cont = {}
            for a in esc_treino.get(h, []):
                for tp in topicos_art.get(a, []):
                    cont[tp] = cont.get(tp, 0) + 1
            return np.array([cont.get(c, 0) for c in cs], dtype=float)
        nome_caminho = "caminhos (topicos dos artigos)"
    else:                            # artigos que compartilham topico com os que o pesquisador ja escreveu
        def base_caminhos(h, cs):
            meus = {tp for a in esc_treino.get(h, []) for tp in topicos_art.get(a, [])}
            return np.array([len(meus & set(topicos_art.get(c, []))) for c in cs], dtype=float)
        nome_caminho = "topicos em comum (caminhos)"
    rng = np.random.default_rng(123)
    base_alea = lambda h, cs: rng.random(len(cs))

    resultados = {"aleatorio": avaliar(base_alea, teste, conhecidas, candidatos),
                  nome_caminho: avaliar(base_caminhos, teste, conhecidas, candidatos)}
    runs = []
    for sem in range(5):                                    # 5 inicializacoes diferentes
        E, R = treinar(treino, ent, rel, lr=lr, epocas=ep, semente=sem)
        runs.append(avaliar(pontuador(E, R), teste, conhecidas, candidatos))
    print(f"\nTESTE (ranqueamento filtrado, `{relacao}`):")
    print(f"  {'metodo':<32}{'MRR':>8}{'Hits@1':>9}{'Hits@3':>9}{'Hits@10':>9}")
    for nome_, m in resultados.items():
        print(f"  {nome_:<32}{m['MRR']:>8.3f}{m['Hits@1']:>9.3f}{m['Hits@3']:>9.3f}{m['Hits@10']:>9.3f}")
    med = {k: np.mean([r[k] for r in runs]) for k in runs[0]}
    dp = {k: np.std([r[k] for r in runs]) for k in runs[0]}
    print(f"  {'TransE (media de 5 sementes)':<32}{med['MRR']:>8.3f}{med['Hits@1']:>9.3f}{med['Hits@3']:>9.3f}{med['Hits@10']:>9.3f}")
    print(f"  {'  desvio padrao':<32}{dp['MRR']:>8.3f}{dp['Hits@1']:>9.3f}{dp['Hits@3']:>9.3f}{dp['Hits@10']:>9.3f}")


if __name__ == "__main__":
    import sys
    main(sys.argv[1] if len(sys.argv) > 1 else "pesquisaEm")
