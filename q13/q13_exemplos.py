"""Exemplos numericos do ensaio sobre Transformers (Questao 13). Valores ilustrativos, sem treinamento."""
import numpy as np
np.set_printoptions(precision=3, suppress=True)

def softmax(x, eixo=-1):
    e = np.exp(x - np.max(x, axis=eixo, keepdims=True))
    return e / e.sum(axis=eixo, keepdims=True)

# ---------- 1. Atencao do video (query 1 0; chaves 1 0 e 0 1; valores 2 0 e 0 2) ----------
q = np.array([1., 0.]); K = np.array([[1., 0.], [0., 1.]]); V = np.array([[2., 0.], [0., 2.]])
dk = 2
s = K @ q; s_esc = s / np.sqrt(dk); w = softmax(s_esc); out = w @ V
print("1) scores", s, "| escalonados", s_esc, "| pesos", w, "| saida", out)
print("   e^0.7071 =", np.exp(0.7071), "soma =", np.exp(0.7071) + 1)
print("   sem escalonar:", softmax(s))

# ---------- 2. Posicao sinusoidal (d_model = 4, posicoes 0, 1, 2) ----------
def pe(pos, d=4):
    v = np.zeros(d)
    for i in range(d // 2):
        ang = pos / (10000 ** (2 * i / d))
        v[2 * i], v[2 * i + 1] = np.sin(ang), np.cos(ang)
    return v
print("2) PE:"); [print("  pos", p, pe(p)) for p in range(3)]

# ---------- 3. Encoder: auto-atencao em "I love India" (d=2, W_Q=W_K=W_V=I) ----------
X = np.array([[1., 0.], [0., 1.], [1., 1.]])   # I, love, India (ilustrativo)
S = X @ X.T / np.sqrt(2)
A_enc = softmax(S); Z = A_enc @ X
print("3) scores/sqrt(d):\n", S, "\n   pesos encoder:\n", A_enc, "\n   saida Z:\n", Z)

# ---------- 4. Decoder: mascara causal ----------
mask = np.triu(np.ones((3, 3), dtype=bool), k=1)
Sm = np.where(mask, -np.inf, S)
A_dec = softmax(Sm); Zd = A_dec @ X
print("4) pesos decoder (mascarado):\n", A_dec, "\n   saida:\n", Zd)

# ---------- 5. Atencao cruzada no primeiro passo do decoder ----------
h0 = np.array([1., 0.5])                       # estado do decoder em <s> (ilustrativo)
Wc = softmax(Z @ h0 / np.sqrt(2)); ctx = Wc @ Z
print("5) pesos cruzados sobre (I, love, India):", Wc, "| contexto", ctx)

# ---------- 6. Camada final: logits -> probabilidades ----------
h = h0 + ctx                                   # conexao residual simples
Wout = np.array([[1.0, 0.2, 0.1, -0.5], [0.8, 0.1, 0.3, 0.0]])   # vocabulario: amo, la, India, </s>
logits = h @ Wout; p = softmax(logits)
print("6) h =", h, "| logits", logits, "| probs", p, "| soma", p.sum())

# ---------- figuras: mapas de atencao ----------
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
fig, ax = plt.subplots(1, 2, figsize=(7.4, 3.2))
nomes = ["I", "love", "India"]
for a, M, t in zip(ax, [A_enc, A_dec], ["Encoder (bidirecional)", "Decoder (máscara causal)"]):
    im = a.imshow(M, vmin=0, vmax=1, cmap="Blues")
    a.set_xticks(range(3)); a.set_xticklabels(nomes); a.set_yticks(range(3)); a.set_yticklabels(nomes)
    a.set_xlabel("token consultado (chave)"); a.set_ylabel("token que consulta (query)"); a.set_title(t, fontsize=10)
    for i in range(3):
        for j in range(3):
            a.text(j, i, f"{M[i, j]:.2f}", ha="center", va="center", color="white" if M[i, j] > .55 else "black", fontsize=10)
plt.tight_layout(); plt.savefig("q13_mapas_atencao.png", dpi=200)
print("figura salva")
