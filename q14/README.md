# Grafo de conhecimento academico em Python (Questao 14)

Grafo de conhecimento (RDF) de colaboracao cientifica, com inferencia simbolica e aprendizagem
de embeddings. Todos os dados sao ficticios ou sinteticos. A ferramenta usada e o Python
(`rdflib`, `owlrl`, `numpy`); o Neo4j nao foi utilizado.

## Arquivos

| Arquivo | Conteudo |
|---|---|
| `kg.py` | Grafo RDF (8 pesquisadores, 8 artigos), inferencia RDFS/OWL RL, regra SPARQL CONSTRUCT, consultas SPARQL e recomendacao de colaboracoes por caminhos |
| `aprendizagem.py` | TransE em numpy sobre um grafo sintetico (120 pesquisadores, 400 artigos), com validacao, baselines e 5 sementes |
| `testes.py` | 5 testes automatizados |
| `saida_kg.txt`, `saida_pesquisaEm.txt`, `saida_escreveu.txt` | Saidas das execucoes usadas no relatorio |

## Como rodar

Testado com Python 3.12.

```bash
pip install -r requirements.txt
python kg.py                          # inferencia, consultas e recomendacao
python aprendizagem.py pesquisaEm     # prever o tema principal de cada pesquisador
python aprendizagem.py escreveu       # prever a autoria de artigos (tarefa mais dificil)
python -m unittest testes -v
```

Cada execucao de `aprendizagem.py` leva alguns segundos. As sementes sao fixas, entao os
resultados se repetem.

## Observacoes

- Os dados da parte de aprendizagem sao gerados por um programa, com comunidades tematicas bem
  separadas. Os resultados mostram o mecanismo, nao o desempenho em dados reais.
- O ajuste de hiperparametros usa apenas o conjunto de validacao; o teste so e usado no final.
