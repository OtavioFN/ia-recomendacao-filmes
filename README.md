# Sistema de recomendação de filmes e séries baseado em ontologia OWL 2

Questão 9 da Lista 2 de Inteligência Artificial (UFAL, 2026.2, Prof. Evandro Costa).

A ontologia representa obras, gêneros, diretores, plataformas e usuários.
O reasoner Pellet classifica indivíduos, infere preferências por cadeias de
propriedades e executa regras SWRL de recomendação. O sistema explica cada
recomendação.

## Arquivos

| Arquivo | Descrição |
|---|---|
| `ontologia.py` | Constrói a ontologia (15 classes, 12 propriedades de objeto, 8 de dados, 31 indivíduos, 2 regras SWRL) e a salva em `recomendacao_filmes.owl`. |
| `recomendador.py` | Roda o Pellet, mostra classificação, relações inferidas, consulta SPARQL, recomendações explicadas e teste de consistência. |
| `recomendacao_filmes.owl` | Ontologia gerada (RDF/XML), abrível no Protégé. |

## Requisitos

- Python 3.12 ou superior (o `recomendador.py` usa f-strings com aspas aninhadas)
- Java instalado (o Pellet roda na JVM)
- Owlready2 **0.48**: a versão 0.51 traz um Pellet que exige Java 25

```bash
pip install -r requirements.txt
```

## Como executar

```bash
python ontologia.py                 # gera recomendacao_filmes.owl
python recomendador.py              # demonstração completa
python recomendador.py ana          # recomendações só para um usuário
python recomendador.py --novo       # cadastra um novo usuário pelo terminal
```

A execução completa leva alguns minutos, porque o Pellet é chamado
várias vezes.

## Abrir no Protégé

Abra `recomendacao_filmes.owl` e ative o reasoner Pellet. O HermiT não
executa as funções embutidas do SWRL (`lessThanOrEqual`), então as regras de
recomendação só disparam no Pellet.
