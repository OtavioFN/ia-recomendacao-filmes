# Questao 15 - raciocinio OWL 2 no Protege com o HermiT

Ontologia de filmes e series (a da Questao 9, sem as regras SWRL) acrescida de cinco classes
definidas, para demonstrar raciocinio de logica de descricao no Protege.

## Por que sem as regras SWRL?

As regras de recomendacao da Questao 9 usam funcoes embutidas do SWRL (`lessThanOrEqual`). O
HermiT, o raciocinador que acompanha o Protege, nao as suporta e se recusa a carregar a ontologia
(erro "built-in atoms are not supported yet"). Esta versao remove as duas regras.

## Arquivos

| Arquivo | Conteudo |
|---|---|
| `ontologia_q15.py` | Constroi a ontologia (usa `ontologia.py` da pasta acima) e salva os dois `.owl` |
| `recomendacao_filmes_q15.owl` | Ontologia consistente: abra no Protege e inicie o HermiT |
| `recomendacao_filmes_inconsistente.owl` | Mesma ontologia + `obra_invalida` (Filme e Serie): o HermiT acusa inconsistencia |
| `verificar_q15.py` | Verifica os resultados esperados com o HermiT via Owlready2 |
| `saida_verificacao.txt` | Saida da verificacao |

## Como rodar

Python 3.12, Java e `pip install owlready2==0.48`.

```bash
cd q15
python ontologia_q15.py      # gera os dois arquivos .owl
python verificar_q15.py      # imprime o que o HermiT infere
```

No Protege: File > Open, escolha o `.owl`, menu Reasoner > HermiT > Start reasoner. Troque a
visao da hierarquia de "Asserted" para "Inferred" para ver a taxonomia inferida.
