"""
Serializers — Python Tutor Chatbot
=====================================
Camada de validação e transformação de dados da API.
"""

from rest_framework import serializers
from .models import Conversa, Mensagem


class MensagemSerializer(serializers.ModelSerializer):
    """Serializer para exibir mensagens individuais."""

    class Meta:
        model = Mensagem
        fields = ['id', 'tipo', 'conteudo', 'tokens_usados', 'criado_em']
        read_only_fields = fields


class PerguntaSerializer(serializers.Serializer):
    """
    Serializer para validar a pergunta enviada pelo usuário.
    Não é um ModelSerializer pois não corresponde a um model específico.
    """

    # session_id identifica a conversa — enviado pelo frontend
    session_id = serializers.UUIDField(
        required=False,
        allow_null=True,
        help_text='UUID da sessão. Se não informado, uma nova conversa é criada.',
    )

    pergunta = serializers.CharField(
        max_length=2000,
        min_length=3,
        trim_whitespace=True,
        help_text='Pergunta sobre Python para o chatbot responder.',
        error_messages={
            'min_length': 'A pergunta deve ter pelo menos 3 caracteres.',
            'max_length': 'A pergunta não pode ter mais de 2000 caracteres.',
        }
    )

    def validate_pergunta(self, value):
        """Validação extra: bloqueia perguntas que são só espaços ou pontuação."""
        if not any(c.isalnum() for c in value):
            raise serializers.ValidationError(
                'A pergunta deve conter pelo menos um caractere alfanumérico.'
            )
        return value


class RespostaSerializer(serializers.Serializer):
    """
    Serializer para a resposta do chatbot.
    Define o formato JSON retornado pela API.
    """
    session_id = serializers.UUIDField()
    pergunta = serializers.CharField()
    resposta = serializers.CharField()
    sucesso = serializers.BooleanField()
    erro = serializers.CharField(allow_null=True)


class ConversaSerializer(serializers.ModelSerializer):
    """Serializer para exibir uma conversa com todo o seu histórico."""

    mensagens = MensagemSerializer(many=True, read_only=True)
    total_mensagens = serializers.SerializerMethodField()

    class Meta:
        model = Conversa
        fields = ['session_id', 'iniciada_em', 'atualizada_em', 'total_mensagens', 'mensagens']

    def get_total_mensagens(self, obj):
        """Retorna o total de mensagens na conversa."""
        return obj.mensagens.count()
