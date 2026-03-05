"""
Models — Python Tutor Chatbot
================================
Armazena o histórico de conversas no banco SQLite.
Isso permite que o chatbot "lembre" do contexto da conversa.
"""

from django.db import models
import uuid


class Conversa(models.Model):
    """
    Representa uma sessão de conversa com o chatbot.
    Cada usuário/aba do browser tem sua própria conversa identificada por session_id.
    """

    # UUID garante IDs únicos sem expor sequência numérica
    session_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        db_index=True,
        verbose_name='ID da Sessão',
        help_text='Identificador único da sessão de conversa',
    )

    iniciada_em = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Iniciada em',
    )

    atualizada_em = models.DateTimeField(
        auto_now=True,
        verbose_name='Última atividade',
    )

    class Meta:
        verbose_name = 'Conversa'
        verbose_name_plural = 'Conversas'
        ordering = ['-atualizada_em']

    def __str__(self):
        return f'Conversa {str(self.session_id)[:8]}... — {self.iniciada_em.strftime("%d/%m/%Y %H:%M")}'


class Mensagem(models.Model):
    """
    Representa uma única mensagem dentro de uma conversa.
    Pode ser do usuário (humano) ou do assistente (IA).
    """

    TIPO_CHOICES = [
        ('humano', 'Humano'),       # Pergunta do usuário
        ('assistente', 'Assistente'),  # Resposta da IA
    ]

    conversa = models.ForeignKey(
        Conversa,
        on_delete=models.CASCADE,   # Ao deletar conversa, apaga todas as mensagens
        related_name='mensagens',
        verbose_name='Conversa',
    )

    tipo = models.CharField(
        max_length=15,
        choices=TIPO_CHOICES,
        verbose_name='Tipo',
        help_text='Quem enviou esta mensagem: humano ou assistente',
    )

    conteudo = models.TextField(
        verbose_name='Conteúdo',
        help_text='Texto da mensagem',
    )

    # Tokens usados nessa interação (útil para monitorar custos)
    tokens_usados = models.IntegerField(
        default=0,
        verbose_name='Tokens usados',
    )

    criado_em = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Enviado em',
    )

    class Meta:
        verbose_name = 'Mensagem'
        verbose_name_plural = 'Mensagens'
        ordering = ['criado_em']    # Ordem cronológica

    def __str__(self):
        return f'[{self.tipo.upper()}] {self.conteudo[:60]}...'
