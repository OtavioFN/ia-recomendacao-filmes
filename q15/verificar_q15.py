"""Verifica, com o HermiT (via Owlready2), os resultados de raciocinio esperados no Protege."""
import warnings
warnings.filterwarnings("ignore")
from owlready2 import (sync_reasoner_hermit, ThingClass, ConstrainedDatatype, Thing,
                       OwlReadyInconsistentOntologyError)
from ontologia_q15 import construir_q15


def nomes(xs):
    return sorted(x.name for x in xs)


def main():
    world, onto = construir_q15()
    with onto:
        # consultas DL do roteiro, como classes temporarias para o raciocinador responder
        consultas = {
            "Filme and ObraAclamada": onto.Filme & onto.ObraAclamada,
            "ObraDeFiccaoCientifica and (disponivelEm value StreamA)":
                onto.ObraDeFiccaoCientifica & onto.disponivelEm.value(onto.StreamA),
            "Usuario and (prefereGenero value Drama)": onto.Usuario & onto.prefereGenero.value(onto.Drama),
            "ObraAudiovisual and (disponivelEm value StreamA) and (idadeMinima some xsd:integer[<= 13])":
                onto.ObraAudiovisual & onto.disponivelEm.value(onto.StreamA)
                & onto.idadeMinima.some(ConstrainedDatatype(int, max_inclusive=13)),
        }
        temp = {}
        for i, (txt, expr) in enumerate(consultas.items()):
            c = type(f"Consulta{i}", (Thing,), {"namespace": onto})
            c.equivalent_to = [expr]
            temp[txt] = c
        tipos_antes = {o.name: {c.name for c in o.is_a if isinstance(c, ThingClass)}
                       for o in list(onto.individuals())}
        sync_reasoner_hermit(world, infer_property_values=True, debug=0)

    print("== ontologia consistente? SIM (o raciocinador terminou sem erro)")
    print("== classes insatisfativeis (equivalentes a owl:Nothing):", nomes(world.inconsistent_classes()))
    print("== ObraInfantil e subclasse de ObraAcessivelAMenores?",
          onto.ObraAcessivelAMenores in onto.ObraInfantil.ancestors())
    print("== ObraAdulta e subclasse de ObraAcessivelAMenores?",
          onto.ObraAcessivelAMenores in onto.ObraAdulta.ancestors())
    print("== superclasses inferidas de FilmeInfantilAclamado:",
          nomes(c for c in onto.FilmeInfantilAclamado.ancestors() if c.name not in ("Thing", "FilmeInfantilAclamado")))
    print("== instancias de FilmeInfantilAclamado:", nomes(onto.FilmeInfantilAclamado.instances()))
    print("== instancias de UsuarioDeFiccaoCientifica:", nomes(onto.UsuarioDeFiccaoCientifica.instances()))
    print("== instancias de DiretorDeObraAclamada:", nomes(onto.DiretorDeObraAclamada.instances()))
    print("== instancias de ObraAcessivelAMenores:", nomes(onto.ObraAcessivelAMenores.instances()))
    print("== tipos inferidos (alem dos declarados):")
    for o in sorted(onto.individuals(), key=lambda x: x.name):
        if o.name in tipos_antes and tipos_antes[o.name]:
            inf = sorted(c.name for c in o.is_a if isinstance(c, ThingClass) and c.name not in tipos_antes[o.name]
                         and not c.name.startswith("Consulta"))
            if inf:
                print(f"     {o.name:<22} {inf}")
    print("== prefereGenero de ana (cadeia de propriedades):", nomes(onto.ana.prefereGenero))
    print("== consultas DL (resultado esperado no separador DL Query):")
    for txt, c in temp.items():
        print(f"     {txt}\n        -> {nomes(c.instances())}")

    print("\n== ontologia INCONSISTENTE:")
    world2, onto2 = construir_q15(inconsistente=True)
    try:
        with onto2:
            sync_reasoner_hermit(world2, debug=0)
        print("   consistente (inesperado)")
    except OwlReadyInconsistentOntologyError:
        print("   o HermiT acusa inconsistencia (obra_invalida e Filme e Serie, que sao disjuntas)")


if __name__ == "__main__":
    main()
