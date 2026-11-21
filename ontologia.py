"""Constroi a ontologia OWL 2 de filmes e series e salva em recomendacao_filmes.owl."""
from owlready2 import *

IRI = "http://example.org/recomendacao-filmes.owl#"

def construir(world=None):
    world = world or World()
    onto = world.get_ontology(IRI)
    with onto:
        # ---------------- Classes e hierarquia ----------------
        class ObraAudiovisual(Thing): pass
        class Filme(ObraAudiovisual): pass
        class Serie(ObraAudiovisual): pass
        class Genero(Thing): pass
        class Plataforma(Thing): pass
        class Pessoa(Thing): pass
        class Diretor(Pessoa): pass
        class Usuario(Pessoa): pass
        AllDisjoint([ObraAudiovisual, Genero, Plataforma, Pessoa])
        AllDisjoint([Filme, Serie])

        # ---------------- Propriedades de objeto ----------------
        class temGenero(ObjectProperty):        domain = [ObraAudiovisual]; range = [Genero]
        class temDiretor(ObjectProperty):       domain = [ObraAudiovisual]; range = [Diretor]
        class dirigiu(ObjectProperty):          inverse_property = temDiretor
        class disponivelEm(ObjectProperty):     domain = [ObraAudiovisual]; range = [Plataforma]
        class oferece(ObjectProperty):          inverse_property = disponivelEm
        class assinaPlataforma(ObjectProperty): domain = [Usuario]; range = [Plataforma]
        class assistiu(ObjectProperty):         domain = [Usuario]; range = [ObraAudiovisual]
        class gostouDe(assistiu):               pass          # subpropriedade
        class prefereGenero(ObjectProperty):    domain = [Usuario]; range = [Genero]
        class prefereDiretor(ObjectProperty):   domain = [Usuario]; range = [Diretor]
        class recomendadoPara(ObjectProperty):  domain = [ObraAudiovisual]; range = [Usuario]
        class temRecomendacao(ObjectProperty):  inverse_property = recomendadoPara

        # Cadeias de propriedades: gostar de uma obra gera preferencias
        prefereGenero.property_chain.append(PropertyChain([gostouDe, temGenero]))
        prefereDiretor.property_chain.append(PropertyChain([gostouDe, temDiretor]))

        # ---------------- Propriedades de dados ----------------
        class titulo(DataProperty, FunctionalProperty):        domain = [ObraAudiovisual]; range = [str]
        class nome(DataProperty, FunctionalProperty):          domain = [Pessoa]; range = [str]
        class idade(DataProperty, FunctionalProperty):         domain = [Usuario]; range = [int]
        class idadeMinima(DataProperty, FunctionalProperty):   domain = [ObraAudiovisual]; range = [int]
        class anoLancamento(DataProperty, FunctionalProperty): domain = [ObraAudiovisual]; range = [int]
        class duracaoMin(DataProperty, FunctionalProperty):    domain = [Filme]; range = [int]
        class numTemporadas(DataProperty, FunctionalProperty): domain = [Serie]; range = [int]
        class notaMedia(DataProperty, FunctionalProperty):     domain = [ObraAudiovisual]; range = [float]

        # ---------------- Restricoes (condicoes necessarias) ----------------
        ObraAudiovisual.is_a += [temGenero.some(Genero), disponivelEm.some(Plataforma),
                                 idadeMinima.exactly(1, int)]
        Filme.is_a.append(temDiretor.some(Diretor))
        Serie.is_a.append(numTemporadas.exactly(1, int))

        # ---------------- Classes definidas (classificacao automatica) ----------------
        g = {n: Genero(n) for n in ["FiccaoCientifica", "Acao", "Drama", "Comedia",
                                     "Terror", "Animacao", "Suspense"]}
        AllDifferent(list(g.values()))

        class ObraDeFiccaoCientifica(ObraAudiovisual):
            equivalent_to = [ObraAudiovisual & temGenero.value(g["FiccaoCientifica"])]
        class ObraDeAcao(ObraAudiovisual):
            equivalent_to = [ObraAudiovisual & temGenero.value(g["Acao"])]
        class ObraInfantil(ObraAudiovisual):
            equivalent_to = [ObraAudiovisual & idadeMinima.some(ConstrainedDatatype(int, max_inclusive=10))]
        class ObraAdulta(ObraAudiovisual):
            equivalent_to = [ObraAudiovisual & idadeMinima.some(ConstrainedDatatype(int, min_inclusive=18))]
        class ObraAclamada(ObraAudiovisual):
            equivalent_to = [ObraAudiovisual & notaMedia.some(ConstrainedDatatype(float, min_inclusive=8.0))]
        class Minisserie(Serie):
            equivalent_to = [Serie & numTemporadas.some(ConstrainedDatatype(int, max_inclusive=1))]
        class UsuarioMenorDeIdade(Usuario):
            equivalent_to = [Usuario & idade.some(ConstrainedDatatype(int, max_inclusive=17))]

        # ---------------- Regras SWRL de recomendacao ----------------
        Imp().set_as_rule(
            "Usuario(?u), prefereGenero(?u, ?g), temGenero(?o, ?g), "
            "idade(?u, ?i), idadeMinima(?o, ?m), lessThanOrEqual(?m, ?i), "
            "assinaPlataforma(?u, ?p), disponivelEm(?o, ?p) -> recomendadoPara(?o, ?u)")
        Imp().set_as_rule(
            "Usuario(?u), prefereDiretor(?u, ?d), temDiretor(?o, ?d), "
            "idade(?u, ?i), idadeMinima(?o, ?m), lessThanOrEqual(?m, ?i), "
            "assinaPlataforma(?u, ?p), disponivelEm(?o, ?p) -> recomendadoPara(?o, ?u)")

        # ---------------- Individuos ----------------
        pl = {n: Plataforma(n) for n in ["StreamA", "StreamB", "StreamC"]}
        AllDifferent(list(pl.values()))
        d = {}
        for ident, nm in [("helena_prado", "Helena Prado"), ("rafael_monteiro", "Rafael Monteiro"),
                          ("tomas_albuquerque", "Tomas Albuquerque"), ("beatriz_lemos", "Beatriz Lemos"),
                          ("iara_siqueira", "Iara Siqueira")]:
            d[ident] = Diretor(ident, nome=nm)

        def obra(cls, ident, tit, gens, dire, idmin, ano, nota, plats, **extra):
            return cls(ident, titulo=tit, temGenero=[g[x] for x in gens], temDiretor=[d[dire]],
                       idadeMinima=idmin, anoLancamento=ano, notaMedia=nota,
                       disponivelEm=[pl[x] for x in plats], **extra)

        # Obras declaradas apenas como Filme ou Serie; o resto e inferido
        obra(Filme, "orbita_silenciosa", "Orbita Silenciosa", ["FiccaoCientifica", "Drama"], "helena_prado", 12, 2021, 8.4, ["StreamA"], duracaoMin=128)
        obra(Filme, "protocolo_zero", "Protocolo Zero", ["Acao", "FiccaoCientifica"], "rafael_monteiro", 14, 2023, 7.6, ["StreamA", "StreamB"], duracaoMin=115)
        obra(Filme, "cacada_urbana", "Cacada Urbana", ["Acao", "Suspense"], "rafael_monteiro", 16, 2019, 7.1, ["StreamB"], duracaoMin=102)
        obra(Filme, "ultima_colheita", "A Ultima Colheita", ["Drama"], "helena_prado", 12, 2018, 8.7, ["StreamC"], duracaoMin=140)
        obra(Filme, "risos_de_domingo", "Risos de Domingo", ["Comedia"], "tomas_albuquerque", 0, 2022, 6.9, ["StreamA"], duracaoMin=95)
        obra(Filme, "vale_das_sombras", "O Vale das Sombras", ["Terror"], "beatriz_lemos", 18, 2020, 7.3, ["StreamB"], duracaoMin=98)
        obra(Filme, "pequenos_inventores", "Pequenos Inventores", ["Animacao", "Comedia"], "iara_siqueira", 0, 2024, 8.1, ["StreamA", "StreamC"], duracaoMin=88)
        obra(Filme, "fronteira_vermelha", "Fronteira Vermelha", ["Acao"], "beatriz_lemos", 18, 2021, 7.8, ["StreamC"], duracaoMin=121)
        obra(Serie, "colonia_7", "Colonia 7", ["FiccaoCientifica", "Suspense"], "helena_prado", 14, 2022, 8.5, ["StreamA"], numTemporadas=3)
        obra(Serie, "plantao_noturno", "Plantao Noturno", ["Drama"], "tomas_albuquerque", 16, 2017, 8.2, ["StreamB"], numTemporadas=5)
        obra(Serie, "agentes_do_amanha", "Agentes do Amanha", ["Acao", "FiccaoCientifica"], "rafael_monteiro", 12, 2024, 7.4, ["StreamC"], numTemporadas=1)
        obra(Serie, "turma_do_quintal", "Turma do Quintal", ["Animacao"], "iara_siqueira", 0, 2020, 7.9, ["StreamA"], numTemporadas=4)

        Usuario("ana", nome="Ana", idade=25, prefereGenero=[g["FiccaoCientifica"]],
                assinaPlataforma=[pl["StreamA"], pl["StreamB"]], gostouDe=[onto.orbita_silenciosa])
        Usuario("lucas", nome="Lucas", idade=13, prefereGenero=[g["Acao"]],
                assinaPlataforma=[pl["StreamA"], pl["StreamC"]], gostouDe=[onto.pequenos_inventores])
        Usuario("marina", nome="Marina", idade=40, prefereGenero=[g["Drama"]],
                assinaPlataforma=[pl["StreamB"], pl["StreamC"]], assistiu=[onto.plantao_noturno])
        Usuario("joao", nome="Joao", idade=17, prefereGenero=[g["Terror"], g["Acao"]],
                assinaPlataforma=[pl["StreamB"]])
    return world, onto

if __name__ == "__main__":
    world, onto = construir()
    onto.save(file="recomendacao_filmes.owl", format="rdfxml")
    print("classes:", len(list(onto.classes())),
          "| prop. objeto:", len(list(onto.object_properties())),
          "| prop. dados:", len(list(onto.data_properties())),
          "| individuos:", len(list(onto.individuals())))
