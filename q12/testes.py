"""Testes automatizados do AgendaProf (nao usam LLM real). Execute: python -m unittest testes -v"""
import json
import unittest

from agente import Agente, extrair_horarios, extrair_json
from llm import Roteirizado
from nucleo import criar_tarefa, resolver, validar, explicar, min_para_hhmm
from roteiros import roteiro_demo

INI, FIM = 14 * 60, 18 * 60
DADOS = [
    dict(id="A", nome="Preparar aula de IA", duracao_min=90, prioridade="alta", vence_hoje=True),
    dict(id="B", nome="Corrigir trabalhos", duracao_min=120, prioridade="media", prazo="amanha"),
    dict(id="C", nome="Reuniao de pesquisa", duracao_min=60, prioridade="alta", vence_hoje=True, inicio_fixo="16:00"),
    dict(id="D", nome="Revisar artigo", duracao_min=60, prioridade="baixa", prazo="proxima semana"),
]


def tarefas():
    return {d["id"]: criar_tarefa(d)[0] for d in DADOS}


def acao(f, args=None):
    return json.dumps({"pensamento": "", "acao": {"ferramenta": f, "args": args or {}}})


def resp(texto):
    return json.dumps({"pensamento": "", "resposta": texto})


class TestSolver(unittest.TestCase):
    def test_plano_otimo_do_cenario(self):
        r = resolver(list(tarefas().values()), INI, FIM)
        self.assertEqual({k: min_para_hhmm(v) for k, v in r.plano.items()},
                         {"A": "14:00", "C": "16:00", "D": "17:00"})
        self.assertEqual(r.utilidade, 7)

    def test_incluir_B_e_inviavel(self):
        r = resolver(list(tarefas().values()), INI, FIM, forcar={"B"})
        self.assertIsNone(r.plano)
        self.assertEqual(r.falha["motivo"], "tempo_insuficiente")
        self.assertEqual((r.falha["minutos_necessarios"], r.falha["minutos_disponiveis"]), (270, 240))

    def test_obrigatorias_que_nao_cabem(self):
        extra = dict(id="E", nome="Prova", duracao_min=120, prioridade="alta", vence_hoje=True)
        r = resolver(list(tarefas().values()) + [criar_tarefa(extra)[0]], INI, FIM)
        self.assertIsNone(r.plano)

    def test_replanejar_com_reuniao_as_17h(self):
        t = tarefas()
        t["C"] = criar_tarefa(dict(DADOS[2], inicio_fixo="17:00"))[0]
        r = resolver(list(t.values()), INI, FIM)
        self.assertEqual(r.utilidade, 7)
        self.assertEqual(min_para_hhmm(r.plano["C"]), "17:00")
        self.assertNotIn("B", r.plano)
        self.assertLess(r.plano["A"], r.plano["D"])   # a tarefa urgente vem antes da de baixa prioridade


class TestValidadorEExplicador(unittest.TestCase):
    def test_detecta_violacoes(self):
        t = tarefas()
        v = validar({"A": 14 * 60, "C": 15 * 60}, t, INI, FIM)   # A (14:00-15:30) sobrepoe C; C fora do fixo
        self.assertTrue(any("sobreposicao" in x for x in v))
        self.assertTrue(any("deveria comecar" in x for x in v))
        v2 = validar({"A": 14 * 60}, t, INI, FIM)
        self.assertTrue(any("C vence hoje" in x for x in v2))
        v3 = validar({"A": 17 * 60, "C": 16 * 60}, t, INI, FIM)  # A termina 18:30
        self.assertTrue(any("fora da janela" in x for x in v3))

    def test_explicacoes(self):
        t = tarefas()
        plano = resolver(list(t.values()), INI, FIM).plano
        eb = explicar("B", t, INI, FIM, plano)
        self.assertEqual((eb["status"], eb["motivo"]), ("adiada", "inviavel_com_as_obrigatorias"))
        self.assertTrue(eb["pode_ser_feita_depois"])
        ed = explicar("D", t, INI, FIM, plano)
        self.assertEqual((ed["motivo"], ed["utilidade_sem_ela"]), ("aumenta_a_utilidade", 6))
        self.assertEqual(explicar("A", t, INI, FIM, plano)["motivo"], "obrigatoria_hoje")
        self.assertEqual(explicar("C", t, INI, FIM, plano)["motivo"], "compromisso_fixo")


class TestEntrada(unittest.TestCase):
    def test_normaliza_e_arredonda(self):
        t, av = criar_tarefa(dict(id="X", nome="x", duracao_min=50, prioridade="Média"))
        self.assertEqual((t.prioridade, t.duracao_min), ("media", 60))
        self.assertTrue(av)

    def test_campo_ausente_gera_erro(self):
        with self.assertRaises(ValueError):
            criar_tarefa(dict(id="X", nome="x", prioridade="alta"))   # sem duracao

    def test_extracao(self):
        self.assertEqual(extrair_horarios("das 14h as 15h30, reuniao 16:00; leva 1h30 e 90 min"),
                         {14 * 60, 15 * 60 + 30, 16 * 60})
        self.assertEqual(extrair_json('texto ```json {"a": 1} ```'), {"a": 1})
        self.assertIsNone(extrair_json("sem json"))


class TestAgente(unittest.TestCase):
    def novo(self, respostas):
        return Agente(Roteirizado(respostas))

    def preparo(self):
        return [acao("definir_janela", {"inicio": "14:00", "fim": "18:00"}),
                acao("registrar_tarefas", {"tarefas": DADOS}), acao("planejar")]

    def test_fluxo_completo_do_roteiro(self):
        ag = self.novo(roteiro_demo())
        r1 = ag.turno("Preciso preparar a aula, corrigir trabalhos e ir a reuniao de pesquisa. Tenho das 14h as 18h.")
        self.assertEqual(r1.avisos, [])
        self.assertIn("14:00-15:30: Preparar aula de IA", r1.texto)
        self.assertIn("Adiei B", r1.texto)
        r2 = ag.turno("A reuniao passou para as 17h.")
        self.assertEqual(r2.avisos, [])
        self.assertIn("17:00-18:00: Reuniao de pesquisa", r2.texto)

    def test_trava_plano_sem_validacao(self):
        ag = self.novo(self.preparo() + [resp("Plano pronto."),            # recusada: sem validar
                                         acao("validar_plano"), acao("explicar_tarefa", {"id": "B"}),
                                         resp("Plano: A 14:00-15:30, C 16:00-17:00, D 17:00-18:00. B fica para amanha.")])
        r = ag.turno("organize minha tarde, das 14h as 18h")
        self.assertTrue(any("nao foi validado" in a for a in r.avisos))
        self.assertIn("B fica para amanha", r.texto)

    def test_trava_tarefa_adiada_sem_explicacao(self):
        ag = self.novo(self.preparo() + [acao("validar_plano"), resp("Plano pronto."),
                                         acao("explicar_tarefa", {"id": "B"}), resp("Plano de 14:00 a 18:00. B vai para amanha.")])
        r = ag.turno("organize minha tarde")
        self.assertTrue(any("explicar_tarefa" in a for a in r.avisos))

    def test_trava_horario_inventado(self):
        ag = self.novo(self.preparo() + [acao("validar_plano"), acao("explicar_tarefa", {"id": "B"}),
                                         resp("Faca B amanha as 9h."),
                                         resp("Faca B amanha; hoje o plano vai das 14:00 as 18:00.")])
        r = ag.turno("organize minha tarde")
        self.assertTrue(any("9:00" in a or "09:00" in a for a in r.avisos))
        self.assertIn("14:00", r.texto)

    def test_resposta_insistente_e_entregue_com_ressalva(self):
        ag = self.novo(self.preparo() + [acao("validar_plano"), acao("explicar_tarefa", {"id": "B"})]
                       + [resp("Faca B amanha as 9h.")] * 3)
        r = ag.turno("organize minha tarde")
        self.assertTrue(any("COM RESSALVA" in a for a in r.avisos))

    def test_json_invalido_e_recuperado(self):
        ag = self.novo(["isto nao e json", resp("Ola! Quais sao suas tarefas?")])
        r = ag.turno("oi")
        self.assertEqual(r.texto, "Ola! Quais sao suas tarefas?")

    def test_erro_de_ferramenta_volta_ao_modelo(self):
        ag = self.novo([acao("planejar"), resp("Qual e a sua janela de horario?")])
        r = ag.turno("planeje")
        self.assertFalse(r.trace[0]["resultado"]["ok"])
        self.assertIn("janela", r.trace[0]["resultado"]["erro"])

    def test_mudanca_invalida_o_plano(self):
        ag = self.novo(self.preparo() + [acao("validar_plano"), acao("remover_tarefa", {"id": "D"}),
                                         resp("Removi D; preciso replanejar.")])
        r = ag.turno("organize; depois remova D")
        self.assertIsNone(ag.plano)
        self.assertEqual(r.avisos, [])


if __name__ == "__main__":
    unittest.main()
