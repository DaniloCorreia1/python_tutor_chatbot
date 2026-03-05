"""
LangChain Service — Coração da Inteligência Artificial
=======================================================
Este módulo encapsula toda a lógica de IA:
  - Configuração do modelo GPT via LangChain
  - Gerenciamento do histórico de conversação (memória)
  - Prompt engineering especializado em Python
  - Integração com LangSmith para rastreamento

Arquitetura utilizada:
  ChatPromptTemplate → ChatOpenAI → StrOutputParser
  (Prompt)             (Modelo)      (Saída limpa)
"""

import logging
from django.conf import settings

# LangChain — componentes principais
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.output_parsers import StrOutputParser

logger = logging.getLogger(__name__)


# ============================================================
# PROMPT SYSTEM — Define a personalidade e regras do chatbot
# ============================================================

SYSTEM_PROMPT = """Você é o **PyTutor**, um assistente especialista em Python com mais de 10 anos de experiência.

Sua missão é ensinar Python de forma clara, didática e empolgante para programadores de todos os níveis.

## Suas Diretrizes:

**Ao responder:**
- Sempre forneça exemplos de código práticos e funcionais
- Use blocos de código com a linguagem especificada: ```python
- Explique o "porquê" além do "como"
- Adapte a complexidade ao nível da pergunta
- Mencione boas práticas e possíveis armadilhas (pitfalls)
- Se relevante, cite a documentação oficial do Python

**Formato das respostas:**
- Use Markdown para formatar (títulos, listas, código)
- Seja conciso mas completo — nem curto demais, nem longo demais
- Divida respostas complexas em seções claras

**Escopo:**
- Foque em Python e seu ecossistema (pip, virtualenv, bibliotecas populares)
- Para perguntas fora de Python, redirecione gentilmente: "Sou especialista em Python, mas posso te ajudar com..."
- Nunca invente funcionalidades que não existem no Python

**Tom:**
- Amigável, paciente e encorajador
- Use analogias do mundo real para conceitos difíceis
- Celebre o progresso do aprendiz

Responda sempre em português do Brasil."""


def criar_chain():
    """
    Cria e retorna a chain LangChain para o chatbot.

    Uma "chain" no LangChain é uma sequência de componentes conectados:
    Prompt → LLM → Parser de saída

    Returns:
        chain: Objeto RunnableSequence pronto para receber inputs
    """
    # 1. Configura o modelo de linguagem (LLM)
    #    ChatOpenAI é o wrapper do LangChain para a API da OpenAI
    llm = ChatOpenAI(
        model=settings.OPENAI_MODEL,
        temperature=settings.OPENAI_TEMPERATURE,
        max_tokens=settings.OPENAI_MAX_TOKENS,
        api_key=settings.OPENAI_API_KEY,
        # streaming=True  # Ative para respostas em tempo real (streaming)
    )

    # 2. Cria o template de prompt com suporte a histórico
    #    MessagesPlaceholder injeta o histórico de mensagens automaticamente
    prompt = ChatPromptTemplate.from_messages([
        ('system', SYSTEM_PROMPT),              # Instrução base do sistema
        MessagesPlaceholder('historico'),        # Histórico da conversa
        ('human', '{pergunta}'),                 # Pergunta atual do usuário
    ])

    # 3. Parser de saída — converte o objeto AIMessage em string simples
    parser = StrOutputParser()

    # 4. Conecta tudo com o operador pipe (|) — sintaxe LCEL do LangChain
    #    LCEL = LangChain Expression Language
    chain = prompt | llm | parser

    return chain


def construir_historico(mensagens_db):
    """
    Converte as mensagens do banco de dados para o formato do LangChain.

    O LangChain usa objetos HumanMessage e AIMessage para representar
    o histórico. Precisamos converter nossas mensagens do Django para esse formato.

    Args:
        mensagens_db: QuerySet de objetos Mensagem do banco de dados

    Returns:
        list: Lista de HumanMessage e AIMessage para o LangChain
    """
    historico = []
    for msg in mensagens_db:
        if msg.tipo == 'humano':
            historico.append(HumanMessage(content=msg.conteudo))
        else:
            historico.append(AIMessage(content=msg.conteudo))
    return historico


def obter_resposta(pergunta: str, historico_db=None) -> dict:
    """
    Função principal: envia a pergunta para a IA e retorna a resposta.

    Fluxo completo:
    1. Carrega histórico do banco → converte para formato LangChain
    2. Monta o prompt com system + histórico + pergunta atual
    3. Envia para a API da OpenAI via LangChain
    4. Retorna a resposta formatada

    Args:
        pergunta (str): Pergunta do usuário
        historico_db: QuerySet com mensagens anteriores da conversa

    Returns:
        dict: {
            'resposta': str — texto da resposta da IA,
            'sucesso': bool — True se OK, False se erro,
            'erro': str — mensagem de erro (se houver)
        }
    """

    # Validação básica da pergunta
    if not pergunta or not pergunta.strip():
        return {
            'resposta': '',
            'sucesso': False,
            'erro': 'A pergunta não pode ser vazia.',
        }

    # Verifica se a chave da OpenAI está configurada
    if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY == 'sk-sua-chave-aqui':
        return {
            'resposta': '',
            'sucesso': False,
            'erro': (
                'Chave da API OpenAI não configurada. '
                'Adicione OPENAI_API_KEY no arquivo .env'
            ),
        }

    try:
        # Cria a chain LangChain
        chain = criar_chain()

        # Converte histórico do banco para formato LangChain
        # Limita ao número configurado em settings.CHAT_HISTORY_LIMIT
        historico_msgs = []
        if historico_db is not None:
            limite = settings.CHAT_HISTORY_LIMIT
            # Pega as últimas N mensagens para não exceder o context window
            msgs_recentes = list(historico_db)[-limite:]
            historico_msgs = construir_historico(msgs_recentes)

        logger.info(f'Enviando pergunta para OpenAI. Histórico: {len(historico_msgs)} msgs')

        # Invoca a chain com os inputs necessários
        # O LangChain monta o prompt final e chama a API automaticamente
        resposta = chain.invoke({
            'historico': historico_msgs,
            'pergunta': pergunta.strip(),
        })

        logger.info('Resposta recebida com sucesso da OpenAI')

        return {
            'resposta': resposta,
            'sucesso': True,
            'erro': None,
        }

    except Exception as e:
        # Captura qualquer erro (API key inválida, timeout, etc.)
        logger.error(f'Erro ao chamar OpenAI: {str(e)}')
        return {
            'resposta': '',
            'sucesso': False,
            'erro': f'Erro ao comunicar com a IA: {str(e)}',
        }
