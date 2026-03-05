"""Admin — Chatbot"""
from django.contrib import admin
from .models import Conversa, Mensagem


class MensagemInline(admin.TabularInline):
    model = Mensagem
    extra = 0
    readonly_fields = ['tipo', 'conteudo', 'tokens_usados', 'criado_em']


@admin.register(Conversa)
class ConversaAdmin(admin.ModelAdmin):
    list_display = ['session_id', 'iniciada_em', 'atualizada_em', 'total_msgs']
    readonly_fields = ['session_id', 'iniciada_em', 'atualizada_em']
    inlines = [MensagemInline]

    def total_msgs(self, obj):
        return obj.mensagens.count()
    total_msgs.short_description = 'Mensagens'


@admin.register(Mensagem)
class MensagemAdmin(admin.ModelAdmin):
    list_display = ['tipo', 'conteudo_resumido', 'conversa', 'criado_em']
    list_filter = ['tipo']
    readonly_fields = ['criado_em']

    def conteudo_resumido(self, obj):
        return obj.conteudo[:80] + '...' if len(obj.conteudo) > 80 else obj.conteudo
    conteudo_resumido.short_description = 'Conteúdo'
