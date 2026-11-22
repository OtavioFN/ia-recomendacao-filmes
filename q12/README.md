# AgendaProf - agente de agenda para professores (Questao 12)

Assistente em linguagem natural que organiza as atividades de um professor em uma janela
de tempo. O LLM interpreta o pedido e redige a resposta; o planejamento, a verificacao e a
explicacao sao feitos por codigo deterministico (arquitetura hibrida da Questao 11).

## Arquivos

| Arquivo | Funcao |
|---|---|
| `nucleo.py` | Modelo de dados, solver (busca com poda), validador independente e explicador |
| `agente.py` | Laco do agente (protocolo JSON), ferramentas e travas de verificacao |
| `llm.py` | Provedores: Anthropic, API compativel com OpenAI e `Roteirizado` (para testes) |
| `roteiros.py` | Roteiro do modo simulado (nao e um LLM) |
| `agendaprof.py` | Interface de terminal |
| `testes.py` | 17 testes automatizados (nao usam LLM real) |

## Como rodar

Testado com Python 3.12. Os testes e o modo simulado nao precisam de chave de API:

```bash
python -m unittest testes -v
python agendaprof.py --provedor simulado
```

Com um LLM real, instale o pacote do provedor e configure a chave:

```bash
# Anthropic
pip install anthropic
export ANTHROPIC_API_KEY="sua-chave"          # Windows (Git Bash): export ...
python agendaprof.py --provedor anthropic     # modelo padrao: claude-haiku-5-5
python agendaprof.py --provedor anthropic --modelo NOME_DO_MODELO

# Qualquer servico compativel com a API da OpenAI (inclui Ollama local)
pip install openai
export AGENDAPROF_BASE_URL="https://.../v1"
export AGENDAPROF_MODELO="nome-do-modelo"
export AGENDAPROF_API_KEY="sua-chave"
python agendaprof.py --provedor openai
```

Exemplo de pedido:

> Preciso preparar uma aula de IA (90 min), corrigir trabalhos (2 horas) e ir a uma reuniao
> de pesquisa de 1 hora as 16h. Tenho das 14h as 18h. A aula e urgente; os trabalhos so
> precisam ficar prontos ate amanha. Tambem queria revisar um artigo (1 hora), mas fica para a
> semana que vem.

Comandos: `/estado` mostra a janela e as tarefas interpretadas; `/sair` encerra.
Cada sessao grava um registro em `logs/` (um evento JSON por linha).

## Observacoes

- O agente apenas propoe o plano; nao altera nenhum calendario.
- Os dados digitados sao enviados ao provedor de LLM escolhido.
- O solver faz busca exata e serve para ate cerca de 10 tarefas.
