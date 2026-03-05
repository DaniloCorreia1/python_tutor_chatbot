"""
Testes Unitários — Python Tutor Chatbot
=========================================
Testa todos os endpoints e a lógica do chatbot.

Estratégia de mock: como a IA (OpenAI) é um serviço externo pago,
usamos unittest.mock para simular as respostas sem fazer chamadas reais.
Isso torna os testes rápidos, gratuitos e confiáveis.

Para rodar: python manage.py test chatbot -v 2
"""

from unittest.mock import patch, MagicMock
from django.test import TestCase, override_settings
from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from .models import Conversa, Mensagem
from .langchain_service import obter_resposta, construir_historico
from langchain_core.messages import HumanMessage, AIMessage


# ============================================================
# CONFIGURAÇÕES DE TESTE
# ============================================================
# Sobrescreve settings para os testes — não precisa de API key real
TEST_SETTINGS = {
    'OPENAI_API_KEY': 'sk-test-fake-key-for-testing',
    'OPENAI_MODEL': 'gpt-4o-mini',
    'OPENAI_TEMPERATURE': 0.7,
    'OPENAI_MAX_TOKENS': 1500,
    'CHAT_HISTORY_LIMIT': 10,
    'LANGCHAIN_TRACING_V2': False,
}


# ============================================================
# TESTES DO MODELO
# ============================================================

class ModeloTest(TestCase):
    """Testa os models Conversa e Mensagem."""

    def test_criar_conversa_gera_uuid(self):
        """Uma nova conversa deve ter um UUID único gerado automaticamente."""
        conversa = Conversa.objects.create()
        self.assertIsNotNone(conversa.session_id)

    def test_duas_conversas_tem_uuids_diferentes(self):
        """Cada conversa deve ter um UUID único."""
        c1 = Conversa.objects.create()
        c2 = Conversa.objects.create()
        self.assertNotEqual(c1.session_id, c2.session_id)

    def test_str_conversa(self):
        """__str__ da Conversa deve conter parte do UUID."""
        conversa = Conversa.objects.create()
        self.assertIn(str(conversa.session_id)[:8], str(conversa))

    def test_criar_mensagem_humano(self):
        """Deve criar mensagem do tipo 'humano' corretamente."""
        conversa = Conversa.objects.create()
        msg = Mensagem.objects.create(
            conversa=conversa,
            tipo='humano',
            conteudo='Como criar uma lista?',
        )
        self.assertEqual(msg.tipo, 'humano')
        self.assertEqual(msg.conteudo, 'Como criar uma lista?')

    def test_criar_mensagem_assistente(self):
        """Deve criar mensagem do tipo 'assistente' corretamente."""
        conversa = Conversa.objects.create()
        msg = Mensagem.objects.create(
            conversa=conversa,
            tipo='assistente',
            conteudo='Você pode criar uma lista assim: lista = []',
        )
        self.assertEqual(msg.tipo, 'assistente')

    def test_deletar_conversa_deleta_mensagens(self):
        """Ao deletar uma conversa, suas mensagens devem ser deletadas (CASCADE)."""
        conversa = Conversa.objects.create()
        Mensagem.objects.create(conversa=conversa, tipo='humano', conteudo='Oi')
        Mensagem.objects.create(conversa=conversa, tipo='assistente', conteudo='Olá!')

        conversa.delete()
        self.assertEqual(Mensagem.objects.count(), 0)

    def test_mensagens_ordenadas_por_data(self):
        """Mensagens devem ser retornadas em ordem cronológica."""
        conversa = Conversa.objects.create()
        m1 = Mensagem.objects.create(conversa=conversa, tipo='humano', conteudo='P1')
        m2 = Mensagem.objects.create(conversa=conversa, tipo='assistente', conteudo='R1')
        m3 = Mensagem.objects.create(conversa=conversa, tipo='humano', conteudo='P2')

        msgs = list(conversa.mensagens.all())
        self.assertEqual(msgs[0], m1)
        self.assertEqual(msgs[1], m2)
        self.assertEqual(msgs[2], m3)


# ============================================================
# TESTES DO LANGCHAIN SERVICE
# ============================================================

class LangChainServiceTest(TestCase):
    """Testa a lógica do serviço LangChain sem chamar a API real."""

    def test_construir_historico_vazio(self):
        """Histórico vazio deve retornar lista vazia."""
        conversa = Conversa.objects.create()
        historico = construir_historico(conversa.mensagens.all())
        self.assertEqual(historico, [])

    def test_construir_historico_com_mensagens(self):
        """Deve converter mensagens do banco para objetos LangChain."""
        conversa = Conversa.objects.create()
        Mensagem.objects.create(conversa=conversa, tipo='humano', conteudo='Pergunta')
        Mensagem.objects.create(conversa=conversa, tipo='assistente', conteudo='Resposta')

        historico = construir_historico(conversa.mensagens.all())

        self.assertEqual(len(historico), 2)
        self.assertIsInstance(historico[0], HumanMessage)
        self.assertIsInstance(historico[1], AIMessage)
        self.assertEqual(historico[0].content, 'Pergunta')
        self.assertEqual(historico[1].content, 'Resposta')

    @override_settings(**TEST_SETTINGS)
    def test_obter_resposta_pergunta_vazia(self):
        """Pergunta vazia deve retornar erro sem chamar a API."""
        resultado = obter_resposta('')
        self.assertFalse(resultado['sucesso'])
        self.assertIn('vazia', resultado['erro'].lower())

    @override_settings(OPENAI_API_KEY='sk-sua-chave-aqui')
    def test_obter_resposta_sem_api_key(self):
        """Sem API key configurada, deve retornar erro informativo."""
        resultado = obter_resposta('Como criar uma lista?')
        self.assertFalse(resultado['sucesso'])
        self.assertIn('API', resultado['erro'])

    @override_settings(**TEST_SETTINGS)
    @patch('chatbot.langchain_service.criar_chain')
    def test_obter_resposta_com_sucesso(self, mock_criar_chain):
        """
        Simula uma resposta bem-sucedida da IA.
        O mock evita chamadas reais à API da OpenAI.
        """
        # Configura o mock para retornar uma resposta simulada
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = 'Em Python, você cria uma lista assim: lista = [1, 2, 3]'
        mock_criar_chain.return_value = mock_chain

        resultado = obter_resposta('Como criar uma lista?')

        self.assertTrue(resultado['sucesso'])
        self.assertIsNone(resultado['erro'])
        self.assertIn('lista', resultado['resposta'])

        # Verifica que a chain foi chamada com os parâmetros corretos
        mock_chain.invoke.assert_called_once()
        args = mock_chain.invoke.call_args[0][0]
        self.assertIn('pergunta', args)
        self.assertEqual(args['pergunta'], 'Como criar uma lista?')

    @override_settings(**TEST_SETTINGS)
    @patch('chatbot.langchain_service.criar_chain')
    def test_obter_resposta_com_erro_da_api(self, mock_criar_chain):
        """Quando a API retorna erro, deve capturar e retornar mensagem amigável."""
        mock_chain = MagicMock()
        mock_chain.invoke.side_effect = Exception('Connection timeout')
        mock_criar_chain.return_value = mock_chain

        resultado = obter_resposta('Pergunta qualquer')

        self.assertFalse(resultado['sucesso'])
        self.assertIn('Erro', resultado['erro'])


# ============================================================
# TESTES DO ENDPOINT /api/chat/
# ============================================================

class ChatEndpointTest(APITestCase):
    """Testa o endpoint principal POST /api/chat/"""

    def setUp(self):
        self.client = APIClient()
        self.url = '/api/chat/'

    def test_post_sem_pergunta_retorna_400(self):
        """POST sem o campo 'pergunta' deve retornar 400."""
        res = self.client.post(self.url, {}, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_com_pergunta_muito_curta_retorna_400(self):
        """POST com pergunta de 1-2 caracteres deve retornar 400."""
        res = self.client.post(self.url, {'pergunta': 'oi'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_com_pergunta_muito_longa_retorna_400(self):
        """POST com pergunta > 2000 caracteres deve retornar 400."""
        res = self.client.post(self.url, {'pergunta': 'x' * 2001}, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    @override_settings(**TEST_SETTINGS)
    @patch('chatbot.views.obter_resposta')
    def test_post_cria_nova_conversa_se_sem_session(self, mock_resposta):
        """POST sem session_id deve criar uma nova conversa automaticamente."""
        mock_resposta.return_value = {
            'resposta': 'Resposta simulada da IA',
            'sucesso': True,
            'erro': None,
        }
        res = self.client.post(self.url, {'pergunta': 'Como usar Python?'}, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('session_id', res.data)
        self.assertEqual(Conversa.objects.count(), 1)

    @override_settings(**TEST_SETTINGS)
    @patch('chatbot.views.obter_resposta')
    def test_post_salva_mensagens_no_banco(self, mock_resposta):
        """Após o POST, a pergunta e a resposta devem estar no banco."""
        mock_resposta.return_value = {
            'resposta': 'Listas são criadas com colchetes: []',
            'sucesso': True,
            'erro': None,
        }
        res = self.client.post(
            self.url,
            {'pergunta': 'Como criar uma lista em Python?'},
            format='json'
        )

        self.assertEqual(Mensagem.objects.count(), 2)
        msgs = list(Mensagem.objects.all())
        self.assertEqual(msgs[0].tipo, 'humano')
        self.assertEqual(msgs[1].tipo, 'assistente')

    @override_settings(**TEST_SETTINGS)
    @patch('chatbot.views.obter_resposta')
    def test_post_mantem_sessao_existente(self, mock_resposta):
        """POST com session_id existente deve continuar a mesma conversa."""
        mock_resposta.return_value = {'resposta': 'Resposta', 'sucesso': True, 'erro': None}

        conversa = Conversa.objects.create()

        # Primeira mensagem
        self.client.post(
            self.url,
            {'session_id': str(conversa.session_id), 'pergunta': 'Pergunta 1'},
            format='json'
        )
        # Segunda mensagem na mesma sessão
        self.client.post(
            self.url,
            {'session_id': str(conversa.session_id), 'pergunta': 'Pergunta 2'},
            format='json'
        )

        # Deve ter 1 conversa com 4 mensagens (2 humano + 2 assistente)
        self.assertEqual(Conversa.objects.count(), 1)
        self.assertEqual(Mensagem.objects.filter(conversa=conversa).count(), 4)

    @override_settings(**TEST_SETTINGS)
    @patch('chatbot.views.obter_resposta')
    def test_resposta_contem_campos_obrigatorios(self, mock_resposta):
        """A resposta da API deve conter session_id, pergunta, resposta, sucesso."""
        mock_resposta.return_value = {'resposta': 'Resposta OK', 'sucesso': True, 'erro': None}

        res = self.client.post(self.url, {'pergunta': 'Teste de campos?'}, format='json')

        self.assertIn('session_id', res.data)
        self.assertIn('pergunta', res.data)
        self.assertIn('resposta', res.data)
        self.assertIn('sucesso', res.data)


# ============================================================
# TESTES DO ENDPOINT /api/historico/
# ============================================================

class HistoricoEndpointTest(APITestCase):
    """Testa os endpoints GET e DELETE /api/historico/<session_id>/"""

    def setUp(self):
        self.client = APIClient()
        self.conversa = Conversa.objects.create()
        Mensagem.objects.create(conversa=self.conversa, tipo='humano', conteudo='Pergunta')
        Mensagem.objects.create(conversa=self.conversa, tipo='assistente', conteudo='Resposta')

    def test_get_historico_existente(self):
        """GET com session_id válido deve retornar o histórico."""
        res = self.client.get(f'/api/historico/{self.conversa.session_id}/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['total_mensagens'], 2)

    def test_get_historico_inexistente_retorna_404(self):
        """GET com session_id inválido deve retornar 404."""
        import uuid
        res = self.client.get(f'/api/historico/{uuid.uuid4()}/')
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_limpa_mensagens(self):
        """DELETE deve remover todas as mensagens da conversa."""
        res = self.client.delete(f'/api/historico/{self.conversa.session_id}/limpar/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(Mensagem.objects.filter(conversa=self.conversa).count(), 0)

    def test_delete_historico_inexistente_retorna_404(self):
        """DELETE com session_id inválido deve retornar 404."""
        import uuid
        res = self.client.delete(f'/api/historico/{uuid.uuid4()}/limpar/')
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)


# ============================================================
# TESTES DO ENDPOINT /api/status/
# ============================================================

class StatusEndpointTest(APITestCase):
    """Testa o endpoint GET /api/status/"""

    def test_status_retorna_200(self):
        """GET /api/status/ deve sempre retornar 200."""
        res = self.client.get('/api/status/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_status_contem_campos(self):
        """Resposta deve conter os campos esperados."""
        res = self.client.get('/api/status/')
        self.assertIn('status', res.data)
        self.assertIn('api_key_configurada', res.data)
        self.assertIn('modelo', res.data)

    @override_settings(OPENAI_API_KEY='sk-chave-real-valida')
    def test_status_com_api_key_configurada(self):
        """Com API key configurada, api_key_configurada deve ser True."""
        res = self.client.get('/api/status/')
        self.assertTrue(res.data['api_key_configurada'])

    @override_settings(OPENAI_API_KEY='sk-sua-chave-aqui')
    def test_status_sem_api_key(self):
        """Com API key padrão (não configurada), api_key_configurada deve ser False."""
        res = self.client.get('/api/status/')
        self.assertFalse(res.data['api_key_configurada'])
        self.assertIsNotNone(res.data['aviso'])
