"""
Views — Python Tutor Chatbot
================================
Endpoints da API REST do chatbot.

Arquitetura das views:
  - ChatbotView: Endpoint principal — recebe pergunta, retorna resposta da IA
  - HistoricoView: Retorna o histórico de uma conversa
  - LimparConversaView: Limpa o histórico de uma conversa
  - ChatInterfaceView: Serve o frontend HTML do chatbot
"""

import logging
from django.shortcuts import render
from django.conf import settings
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import Conversa, Mensagem
from .serializers import PerguntaSerializer, ConversaSerializer
from .langchain_service import obter_resposta

logger = logging.getLogger(__name__)


class ChatInterfaceView(APIView):
    """
    GET /
    Serve a interface HTML do chatbot.
    """

    def get(self, request):
        return render(request, 'chatbot/index.html')


class ChatbotView(APIView):
    """
    POST /api/chat/
    Endpoint principal do chatbot.

    Recebe a pergunta do usuário, consulta a IA via LangChain,
    salva a conversa no banco e retorna a resposta.

    Body (JSON):
      {
        "session_id": "uuid-opcional",   # Se omitido, cria nova conversa
        "pergunta": "Como criar uma lista em Python?"
      }

    Response (JSON):
      {
        "session_id": "uuid-da-sessao",
        "pergunta": "Como criar uma lista em Python?",
        "resposta": "Em Python, você pode criar uma lista...",
        "sucesso": true,
        "erro": null
      }
    """

    def post(self, request):
        # 1. Valida os dados recebidos com o serializer
        serializer = PerguntaSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'erro': serializer.errors, 'sucesso': False},
                status=status.HTTP_400_BAD_REQUEST
            )

        dados = serializer.validated_data
        pergunta = dados['pergunta']
        session_id = dados.get('session_id')

        # 2. Obtém ou cria a sessão de conversa
        #    get_or_create retorna (objeto, criado_agora: bool)
        if session_id:
            conversa, _ = Conversa.objects.get_or_create(session_id=session_id)
        else:
            # Cria nova conversa com UUID automático
            conversa = Conversa.objects.create()

        # 3. Carrega o histórico da conversa para dar contexto à IA
        #    Ordenado por data de criação (cronológico)
        historico = conversa.mensagens.all().order_by('criado_em')

        logger.info(f'Sessão {conversa.session_id} — Pergunta: {pergunta[:50]}...')

        # 4. Chama o serviço LangChain para obter a resposta da IA
        resultado = obter_resposta(pergunta=pergunta, historico_db=historico)

        # 5. Salva a pergunta do usuário no banco (independente do resultado)
        Mensagem.objects.create(
            conversa=conversa,
            tipo='humano',
            conteudo=pergunta,
        )

        # 6. Se a IA respondeu com sucesso, salva a resposta também
        if resultado['sucesso']:
            Mensagem.objects.create(
                conversa=conversa,
                tipo='assistente',
                conteudo=resultado['resposta'],
            )

        # 7. Monta e retorna a resposta da API
        return Response(
            {
                'session_id': str(conversa.session_id),
                'pergunta': pergunta,
                'resposta': resultado['resposta'],
                'sucesso': resultado['sucesso'],
                'erro': resultado['erro'],
            },
            status=status.HTTP_200_OK if resultado['sucesso'] else status.HTTP_503_SERVICE_UNAVAILABLE
        )


class HistoricoView(APIView):
    """
    GET /api/historico/<session_id>/
    Retorna o histórico completo de uma conversa.

    Útil para recarregar a conversa ao abrir o chatbot novamente.
    """

    def get(self, request, session_id):
        try:
            conversa = Conversa.objects.get(session_id=session_id)
        except Conversa.DoesNotExist:
            return Response(
                {'erro': 'Conversa não encontrada.'},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = ConversaSerializer(conversa)
        return Response(serializer.data)


class LimparConversaView(APIView):
    """
    DELETE /api/historico/<session_id>/
    Apaga todas as mensagens de uma conversa (limpa o histórico).
    A conversa em si é mantida, apenas as mensagens são removidas.
    """

    def delete(self, request, session_id):
        try:
            conversa = Conversa.objects.get(session_id=session_id)
        except Conversa.DoesNotExist:
            return Response(
                {'erro': 'Conversa não encontrada.'},
                status=status.HTTP_404_NOT_FOUND
            )

        total = conversa.mensagens.count()
        conversa.mensagens.all().delete()

        return Response(
            {
                'mensagem': f'Histórico limpo com sucesso. {total} mensagens removidas.',
                'session_id': str(session_id),
            },
            status=status.HTTP_200_OK
        )


class StatusView(APIView):
    """
    GET /api/status/
    Verifica o status da API e configurações.
    Útil para diagnóstico antes de usar o chatbot.
    """

    def get(self, request):
        api_key_ok = bool(
            settings.OPENAI_API_KEY and
            settings.OPENAI_API_KEY != 'sk-sua-chave-aqui'
        )

        return Response({
            'status': 'online',
            'api_key_configurada': api_key_ok,
            'modelo': settings.OPENAI_MODEL,
            'langsmith_ativo': settings.LANGCHAIN_TRACING_V2,
            'total_conversas': Conversa.objects.count(),
            'total_mensagens': Mensagem.objects.count(),
            'aviso': None if api_key_ok else (
                'Configure OPENAI_API_KEY no arquivo .env para usar o chatbot'
            ),
        })
