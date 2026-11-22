"""Grafo de conhecimento academico (fictico): representacao RDF, inferencia e recomendacao.

Dependencias: pip install rdflib owlrl
"""
from rdflib import Graph, Namespace, RDF, RDFS, OWL, Literal
import owlrl

EX = Namespace("http://example.org/kg#")


def construir():
    g = Graph()
    g.bind("ex", EX)
    # ------------------------- esquema (T-Box leve) -------------------------
    for sub, sup in [(EX.Professor, EX.Pesquisador), (EX.Estudante, EX.Pesquisador),
                     (EX.Pesquisador, EX.Pessoa)]:
        g.add((sub, RDFS.subClassOf, sup))
    g.add((EX.escreveu, RDFS.subPropertyOf, EX.contribuiPara))      # escrever e uma forma de contribuir
    g.add((EX.escreveu, RDFS.domain, EX.Pesquisador))
    g.add((EX.escreveu, RDFS.range, EX.Artigo))
    g.add((EX.coautorDe, RDF.type, OWL.SymmetricProperty))
    g.add((EX.afiliadoA, RDFS.domain, EX.Pesquisador))
    g.add((EX.afiliadoA, RDFS.range, EX.Instituicao))
    # ------------------------- fatos (A-Box) -------------------------
    pesquisadores = {  # nome: (classe, instituicao)
        "Ana": ("Professor", "UFAL"), "Bruno": ("Estudante", "UFAL"), "Gabi": ("Estudante", "UFAL"),
        "Carla": ("Professor", "UFPE"), "Davi": ("Estudante", "UFPE"), "Hugo": ("Professor", "UFPE"),
        "Elisa": ("Professor", "USP"), "Felipe": ("Estudante", "USP")}
    for nome, (cls, inst) in pesquisadores.items():
        g.add((EX[nome], RDF.type, EX[cls]))
        g.add((EX[nome], RDFS.label, Literal(nome)))
        g.add((EX[nome], EX.afiliadoA, EX[inst]))
    artigos = {  # id: (autores, topicos)
        "P1": (["Ana", "Bruno"], ["AprendizadoDeMaquina", "VisaoComputacional"]),
        "P2": (["Bruno", "Carla"], ["VisaoComputacional"]),
        "P3": (["Carla", "Davi"], ["AprendizadoDeMaquina"]),
        "P4": (["Ana", "Gabi"], ["Robotica"]),
        "P5": (["Elisa", "Felipe"], ["RedesDeComputadores", "IoT"]),
        "P6": (["Davi", "Hugo"], ["AprendizadoDeMaquina", "Robotica"]),
        "P7": (["Felipe", "Gabi"], ["IoT"]),
        "P8": (["Gabi", "Hugo"], ["Robotica"])}
    for aid, (autores, topicos) in artigos.items():
        g.add((EX[aid], RDF.type, EX.Artigo))
        for a in autores:
            g.add((EX[a], EX.escreveu, EX[aid]))
        for t in topicos:
            g.add((EX[aid], EX.trata, EX[t]))
    return g


def inferir(g):
    """Fecho dedutivo: RDFS + OWL RL (subclasses, subpropriedades, dominio/imagem, simetria)."""
    antes = len(g)
    owlrl.DeductiveClosure(owlrl.OWLRL_Semantics).expand(g)
    return antes, len(g)


REGRA_COAUTORIA = """
PREFIX ex: <http://example.org/kg#>
CONSTRUCT { ?a ex:coautorDe ?b }
WHERE { ?a ex:escreveu ?p . ?b ex:escreveu ?p . FILTER(?a != ?b) }"""


def aplicar_regra_coautoria(g):
    """Regra SPARQL CONSTRUCT: quem escreve o mesmo artigo e coautor (a simetria vem do OWL RL)."""
    novos = 0
    for triplo in g.query(REGRA_COAUTORIA):
        if triplo not in g:
            g.add(triplo)
            novos += 1
    return novos


def nome(no):
    return str(no).split("#")[-1]


def consulta(g, q):
    return [tuple(nome(c) if hasattr(c, "n3") and str(c).startswith(str(EX)) else (c.toPython() if c is not None else None)
                  for c in linha) for linha in g.query(q)]


PREFIXO = "PREFIX ex: <http://example.org/kg#>\nPREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\n"


def recomendar_colaboracoes(g, pessoa):
    """Inferencia por caminhos: nao coautores a 2 saltos, ordenados por topicos em comum."""
    p = EX[pessoa]
    topicos = lambda x: {t for a in g.objects(x, EX.escreveu) for t in g.objects(a, EX.trata)}
    coautores = lambda x: {y for y in g.objects(x, EX.coautorDe) if y != x}
    diretos = coautores(p)
    meus_topicos = topicos(p)
    candidatos = {}
    for ponte in diretos:
        for c in coautores(ponte):
            if c != p and c not in diretos:
                candidatos.setdefault(c, set()).add(ponte)
    ranking = []
    for c, pontes in candidatos.items():
        comuns = meus_topicos & topicos(c)
        ranking.append((len(comuns) * 2 + len(pontes), c, sorted(nome(t) for t in comuns), sorted(nome(b) for b in pontes)))
    return sorted(ranking, key=lambda x: (-x[0], nome(x[1])))


CONSULTAS = {
    "autores e instituicoes em Aprendizado de Maquina": """
        SELECT DISTINCT ?autor ?inst WHERE {
            ?p ex:trata ex:AprendizadoDeMaquina . ?a ex:escreveu ?p .
            ?a rdfs:label ?autor . ?a ex:afiliadoA ?i . BIND(STRAFTER(STR(?i), "#") AS ?inst) } ORDER BY ?autor""",
    "instancias de Pesquisador (exige inferencia de subclasses)": """
        SELECT ?nome WHERE { ?x a ex:Pesquisador . ?x rdfs:label ?nome } ORDER BY ?nome""",
    "nao coautores a 2 saltos de Ana (caminho de propriedades)": """
        SELECT DISTINCT ?nome WHERE {
            ex:Ana ex:coautorDe/ex:coautorDe ?x . ?x rdfs:label ?nome .
            FILTER(?x != ex:Ana) FILTER NOT EXISTS { ex:Ana ex:coautorDe ?x } } ORDER BY ?nome""",
    "especialistas (>= 2 artigos no mesmo topico)": """
        SELECT ?nome ?topico (COUNT(DISTINCT ?p) AS ?n) WHERE {
            ?a ex:escreveu ?p . ?p ex:trata ?t . ?a rdfs:label ?nome . BIND(STRAFTER(STR(?t), "#") AS ?topico) }
        GROUP BY ?nome ?topico HAVING (COUNT(DISTINCT ?p) >= 2) ORDER BY ?topico ?nome""",
}


def executar(g, titulo, q):
    linhas = [tuple(str(c.toPython()) if c is not None else None for c in r) for r in g.query(PREFIXO + q)]
    print(f"  {titulo}: {linhas}")


if __name__ == "__main__":
    g = construir()
    print(f"triplas declaradas: {len(g)}")
    print("\nConsultas ANTES da inferencia:")
    executar(g, "instancias de Pesquisador", CONSULTAS["instancias de Pesquisador (exige inferencia de subclasses)"])
    print("\nregra CONSTRUCT (coautoria): novas triplas coautorDe =", aplicar_regra_coautoria(g))
    a, d = inferir(g)
    print(f"fecho OWL RL: {a} -> {d} triplas (inclui triplas triviais do proprio OWL RL)")
    print("Ana e Pessoa?", (EX.Ana, RDF.type, EX.Pessoa) in g, "| Ana contribuiPara P1?", (EX.Ana, EX.contribuiPara, EX.P1) in g,
          "| Bruno coautorDe Ana (simetria)?", (EX.Bruno, EX.coautorDe, EX.Ana) in g)
    print("\nConsultas DEPOIS da inferencia:")
    for titulo, q in CONSULTAS.items():
        executar(g, titulo, q)
    print("\nrecomendacao de colaboracoes para Ana:")
    for score, c, comuns, pontes in recomendar_colaboracoes(g, "Ana"):
        print(f"  {nome(c)}: score {score}, topicos em comum {comuns}, via {pontes}")
