"""
URLs — Chatbot
================
Define todas as rotas da aplicação chatbot.
"""

from django.urls import path
from . import views

urlpatterns = [
    # Interface visual do chatbot
    path('', views.ChatInterfaceView.as_view(), name='chat-interface'),

    # API REST
    path('api/chat/', views.ChatbotView.as_view(), name='chat'),
    path('api/historico/<uuid:session_id>/', views.HistoricoView.as_view(), name='historico'),
    path('api/historico/<uuid:session_id>/limpar/', views.LimparConversaView.as_view(), name='limpar'),
    path('api/status/', views.StatusView.as_view(), name='status'),
]
