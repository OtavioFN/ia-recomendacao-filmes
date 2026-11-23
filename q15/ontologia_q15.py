"""Questao 15: ontologia OWL 2 de filmes e series para demonstrar raciocinio no Protege (HermiT).

Base: ontologia da Questao 9 (ontologia.py, pasta acima), SEM as duas regras SWRL, porque o HermiT
nao suporta as funcoes embutidas do SWRL (lessThanOrEqual) e se recusa a carregar a ontologia.
Acrescenta classes definidas para evidenciar o raciocinio de logica de descricao.

Gera dois arquivos:
  recomendacao_filmes_q15.owl            ontologia consistente
  recomendacao_filmes_inconsistente.owl  mesma ontologia + um individuo que a torna inconsistente
Dependencia: pip install owlready2==0.48 (e Java para o raciocinador)
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from owlready2 import Thing, ConstrainedDatatype, destroy_entity   # noqa: E402
from ontologia import construir                                      # noqa: E402  (Questao 9)


def construir_q15(inconsistente=False):
    world, onto = construir()
    for regra in list(onto.rules()):          # remove as regras SWRL (HermiT nao as suporta)
        destroy_entity(regra)
    with onto:
        # 1) classe definida a partir de OUTRAS classes definidas (ObraInfantil, ObraAclamada)
        class FilmeInfantilAclamado(Thing):
            equivalent_to = [onto.Filme & onto.ObraInfantil & onto.ObraAclamada]

        # 2) cadeia de propriedades (gostouDe o temGenero -> prefereGenero) + restricao de valor
        class UsuarioDeFiccaoCientifica(Thing):
            equivalent_to = [onto.Usuario & onto.prefereGenero.value(onto.FiccaoCientifica)]

        # 3) propriedade inversa (dirigiu) + restricao existencial sobre classe inferida
        class DiretorDeObraAclamada(Thing):
            equivalent_to = [onto.Diretor & onto.dirigiu.some(onto.ObraAclamada)]

        # 4) faixa de valores: ObraInfantil (<= 10) deve ficar abaixo desta (<= 17) na taxonomia
        class ObraAcessivelAMenores(Thing):
            equivalent_to = [onto.ObraAudiovisual & onto.idadeMinima.some(
                ConstrainedDatatype(int, max_inclusive=17))]

        # 5) classe insatisfativel: Filme e Serie sao disjuntas
        class FilmeESerie(Thing):
            equivalent_to = [onto.Filme & onto.Serie]

        if inconsistente:                          # individuo que e Filme e Serie ao mesmo tempo
            erro = onto.Filme("obra_invalida", titulo="Obra Invalida", idadeMinima=10)
            erro.is_a.append(onto.Serie)
    return world, onto


if __name__ == "__main__":
    aqui = os.path.dirname(os.path.abspath(__file__))
    for inc, nome in [(False, "recomendacao_filmes_q15.owl"), (True, "recomendacao_filmes_inconsistente.owl")]:
        _, onto = construir_q15(inc)
        onto.save(file=os.path.join(aqui, nome), format="rdfxml")
        print("salvo:", nome)
