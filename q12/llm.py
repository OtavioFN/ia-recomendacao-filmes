"""Provedores de LLM do AgendaProf. O agente depende apenas de `completar(sistema, mensagens)`."""
import os


class LLM:
    def completar(self, sistema, mensagens):
        raise NotImplementedError


class Anthropic(LLM):
    """API da Anthropic. Requer: pip install anthropic e a variavel ANTHROPIC_API_KEY."""
    def __init__(self, modelo=None):
        import anthropic
        self.cliente = anthropic.Anthropic()
        self.modelo = modelo or os.getenv("AGENDAPROF_MODELO", "claude-haiku-5-5")

    def completar(self, sistema, mensagens):
        r = self.cliente.messages.create(model=self.modelo, max_tokens=1024,
                                         system=sistema, messages=mensagens)
        return "".join(b.text for b in r.content if b.type == "text")


class OpenAICompat(LLM):
    """Qualquer servico com API compativel com a da OpenAI (inclui servidores locais, como Ollama).
    Requer: pip install openai e as variaveis AGENDAPROF_BASE_URL, AGENDAPROF_MODELO e AGENDAPROF_API_KEY."""
    def __init__(self, modelo=None):
        from openai import OpenAI
        self.cliente = OpenAI(base_url=os.environ["AGENDAPROF_BASE_URL"],
                              api_key=os.getenv("AGENDAPROF_API_KEY", "sem-chave"))
        self.modelo = modelo or os.environ["AGENDAPROF_MODELO"]

    def completar(self, sistema, mensagens):
        msgs = [{"role": "system", "content": sistema}] + mensagens
        r = self.cliente.chat.completions.create(model=self.modelo, messages=msgs, temperature=0)
        return r.choices[0].message.content


class Roteirizado(LLM):
    """NAO e um LLM: devolve respostas pre-definidas, na ordem. Serve para testes e demonstracao
    do fluxo do agente sem chave de API. Cada item e um texto ou uma funcao(mensagens) -> texto."""
    def __init__(self, respostas):
        self.respostas, self.i = list(respostas), 0

    def completar(self, sistema, mensagens):
        if self.i >= len(self.respostas):
            raise RuntimeError("roteiro esgotado")
        r = self.respostas[self.i]
        self.i += 1
        return r(mensagens) if callable(r) else r


def criar_llm(provedor, modelo=None):
    if provedor == "anthropic":
        return Anthropic(modelo)
    if provedor == "openai":
        return OpenAICompat(modelo)
    if provedor == "simulado":
        from roteiros import roteiro_demo
        return Roteirizado(roteiro_demo())
    raise ValueError(f"provedor desconhecido: {provedor}")
