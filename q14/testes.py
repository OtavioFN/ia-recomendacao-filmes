"""Testes do grafo de conhecimento e do TransE. Execute: python -m unittest testes -v"""
import unittest
import numpy as np
from rdflib import RDF
from kg import EX, construir, inferir, aplicar_regra_coautoria, recomendar_colaboracoes, nome
import aprendizagem as ap


class TestKG(unittest.TestCase):
    def setUp(self):
        self.g = construir()

    def test_sem_inferencia_nao_ha_pesquisador(self):
        self.assertEqual(list(self.g.subjects(RDF.type, EX.Pesquisador)), [])

    def test_inferencia_rdfs_owl(self):
        aplicar_regra_coautoria(self.g)
        inferir(self.g)
        self.assertEqual(len(list(self.g.subjects(RDF.type, EX.Pesquisador))), 8)       # subClassOf
        self.assertIn((EX.Ana, EX.contribuiPara, EX.P1), self.g)                         # subPropertyOf
        self.assertIn((EX.Bruno, EX.coautorDe, EX.Ana), self.g)                          # simetria
        self.assertIn((EX.Ana, RDF.type, EX.Pessoa), self.g)                             # transitividade de subClassOf

    def test_regra_de_coautoria(self):
        self.assertEqual(aplicar_regra_coautoria(self.g), 16)                            # 8 pares, 2 sentidos
        self.assertNotIn((EX.Ana, EX.coautorDe, EX.Ana), self.g)

    def test_recomendacao_para_ana(self):
        aplicar_regra_coautoria(self.g)
        inferir(self.g)
        r = recomendar_colaboracoes(self.g, "Ana")
        self.assertEqual({nome(c) for _, c, _, _ in r}, {"Carla", "Hugo", "Felipe"})
        self.assertEqual({nome(c) for _, c, _, _ in r[:2]}, {"Carla", "Hugo"})           # os dois com 2 topicos em comum
        self.assertEqual(nome(r[-1][1]), "Felipe")
        self.assertEqual(r[-1][2], [])                                                   # sem topicos em comum


class TestTransE(unittest.TestCase):
    def test_determinismo_e_divisao(self):
        triplas, arts, tops = ap.gerar_grafo()
        treino, valid, teste = ap.dividir(triplas, "pesquisaEm")
        self.assertFalse(set(treino) & (set(valid) | set(teste)))                        # sem vazamento
        ent = {e: i for i, e in enumerate(sorted({x for h, _, t in triplas for x in (h, t)}))}
        rel = {r: i for i, r in enumerate(sorted({r for _, r, _ in triplas}))}
        E1, _ = ap.treinar(treino, ent, rel, epocas=3, semente=1)
        E2, _ = ap.treinar(treino, ent, rel, epocas=3, semente=1)
        self.assertTrue(np.allclose(E1, E2))


if __name__ == "__main__":
    unittest.main()
