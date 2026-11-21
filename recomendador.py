"""Sistema de recomendacao: raciocina sobre a ontologia com Pellet e explica as recomendacoes."""
# Requer: owlready2==0.48 e Java (a versao 0.51 do Owlready2 traz um Pellet que exige Java 25)
import sys
from owlready2 import *
from ontologia import construir

def ler_perfil(onto):
    """Recebe o perfil de um novo usuario e o insere na ontologia."""
    print("Generos:", ", ".join(g.name for g in onto.Genero.instances()))
    print("Plataformas:", ", ".join(p.name for p in onto.Plataforma.instances()))
    print("Obras:", ", ".join(o.name for o in onto.ObraAudiovisual.instances()))
    lista = lambda txt: [onto[x.strip()] for x in input(txt).split(",") if x.strip()]
    with onto:
        u = onto.Usuario("novo_usuario", nome=input("Nome: ").strip(),
                         idade=int(input("Idade: ")))
        u.prefereGenero = lista("Generos preferidos: ")
        u.assinaPlataforma = lista("Plataformas assinadas: ")
        u.gostouDe = lista("Obras de que gostou (opcional): ")
    return "novo_usuario"

def raciocinar(novo=False):
    world, onto = construir()
    nome_novo = ler_perfil(onto) if novo else None
    # guarda os fatos declarados antes do raciocinio, para separar declarado de inferido
    declarado = {u.name: {"generos": {g.name for g in u.prefereGenero},
                          "diretores": {d.name for d in u.prefereDiretor}}
                 for u in onto.Usuario.instances()}
    tipos_decl = {o.name: {c.name for c in o.is_a if isinstance(c, ThingClass)}
                  for o in onto.ObraAudiovisual.instances()}
    with onto:
        sync_reasoner_pellet(world, infer_property_values=True,
                             infer_data_property_values=True, debug=0)
    return world, onto, declarado, tipos_decl, nome_novo

def recomendar(onto, declarado, nome_usuario):
    u = onto[nome_usuario]
    print(f"\n=== Recomendacoes para {u.nome} ({u.idade} anos) ===")
    print("Assina:", ", ".join(p.name for p in u.assinaPlataforma))
    for tipo, chave, valores in [("Generos", "generos", u.prefereGenero),
                                 ("Diretores", "diretores", u.prefereDiretor)]:
        itens = [f"{getattr(v, 'nome', None) or v.name} ({'declarado' if v.name in declarado[u.name][chave] else 'inferido'})"
                 for v in valores]
        print(f"{tipo} preferidos:", ", ".join(itens) or "nenhum")
    assistidas = set(u.assistiu)
    candidatas = [o for o in u.temRecomendacao if o not in assistidas]   # filtro de mundo fechado
    ranking = []
    for o in candidatas:
        gens = set(o.temGenero) & set(u.prefereGenero)
        dirs = set(o.temDiretor) & set(u.prefereDiretor)
        score = 2 * len(gens) + 2 * len(dirs) + o.notaMedia / 10
        ranking.append((score, o, gens, dirs))
    ranking.sort(key=lambda x: -x[0])
    for score, o, gens, dirs in ranking:
        plats = [p.name for p in o.disponivelEm if p in u.assinaPlataforma]
        print(f"  [{score:.2f}] {o.titulo} ({"Serie" if isinstance(o, onto.Serie) else "Filme"}, {o.anoLancamento}, nota {o.notaMedia})")
        motivos = []
        if gens: motivos.append("genero " + ", ".join(g.name for g in gens))
        if dirs: motivos.append("diretor(a) " + ", ".join(d.nome for d in dirs))
        print(f"      por que: {'; '.join(motivos)}; idade minima {o.idadeMinima} <= {u.idade}; em {', '.join(plats)}")
    if not ranking:
        print("  nenhuma recomendacao")
    # explicacao das obras do perfil que NAO foram recomendadas
    for o in onto.ObraAudiovisual.instances():
        if o in u.temRecomendacao or o in assistidas:
            continue
        if not (set(o.temGenero) & set(u.prefereGenero) or set(o.temDiretor) & set(u.prefereDiretor)):
            continue
        motivos = []
        if o.idadeMinima > u.idade: motivos.append(f"idade minima {o.idadeMinima} > {u.idade}")
        if not set(o.disponivelEm) & set(u.assinaPlataforma):
            motivos.append("indisponivel nas plataformas assinadas")
        print(f"  descartada: {o.titulo} ({'; '.join(motivos)})")
    ja = [o.titulo for o in u.temRecomendacao if o in assistidas]
    if ja: print("  (ja assistidas, omitidas:", ", ".join(ja) + ")")

def consulta_sparql(world):
    print("\n=== Consulta SPARQL: obras aclamadas de ficcao cientifica e suas plataformas ===")
    q = """
    PREFIX : <http://example.org/recomendacao-filmes.owl#>
    SELECT ?titulo ?nota ?plat WHERE {
        ?o a :ObraDeFiccaoCientifica , :ObraAclamada ;
           :titulo ?titulo ; :notaMedia ?nota ; :disponivelEm ?p .
        BIND(STRAFTER(STR(?p), "#") AS ?plat)
    } ORDER BY DESC(?nota)"""
    for linha in world.sparql(q):
        print("  ", linha)

def verificar_consistencia():
    print("\n=== Verificacao de consistencia ===")
    world, onto = construir()
    with onto:
        sync_reasoner_pellet(world, debug=0)
    print("Ontologia original: consistente")
    world, onto = construir()
    with onto:
        erro = onto.Filme("obra_invalida", titulo="Obra Invalida", idadeMinima=10)
        erro.is_a.append(onto.Serie)               # Filme e Serie sao disjuntas
    try:
        with onto:
            sync_reasoner_pellet(world, debug=0)
        print("Ontologia com erro: consistente (inesperado)")
    except OwlReadyInconsistentOntologyError:
        print("Ontologia com 'obra_invalida' (Filme e Serie ao mesmo tempo): INCONSISTENTE")

if __name__ == "__main__":
    novo = "--novo" in sys.argv
    world, onto, declarado, tipos_decl, nome_novo = raciocinar(novo)
    if novo:
        recomendar(onto, declarado, nome_novo)
        sys.exit()
    print("=== Classificacao automatica das obras ===")
    for o in sorted(onto.ObraAudiovisual.instances(), key=lambda x: x.name):
        inferidos = sorted(c.name for c in o.is_a if isinstance(c, ThingClass)
                           and c.name not in tipos_decl[o.name])
        print(f"{o.titulo:<22} declarado: {', '.join(sorted(tipos_decl[o.name])):<7} inferido: {', '.join(inferidos) or '-'}")
    print("\n=== Usuarios classificados ===")
    print("UsuarioMenorDeIdade:", ", ".join(u.nome for u in onto.UsuarioMenorDeIdade.instances()))
    print("\n=== Relacao inversa inferida (dirigiu) ===")
    for d in onto.Diretor.instances():
        print(f"{d.nome}: {', '.join(o.titulo for o in d.dirigiu)}")
    consulta_sparql(world)
    for nome in (sys.argv[1:] or ["ana", "lucas", "marina", "joao"]):
        recomendar(onto, declarado, nome)
    verificar_consistencia()
