"""
Configurações do Python Tutor Chatbot
======================================
Projeto Django + LangChain + OpenAI + LangSmith
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env automaticamente
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# Chave secreta do Django — lida do .env em produção
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-chatbot-dev-key-troque-em-producao')

DEBUG = os.getenv('DJANGO_DEBUG', 'True') == 'True'

ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Django REST Framework
    'rest_framework',
    # CORS — permite que o frontend (HTML) faça chamadas à API
    'corsheaders',
    # Nossa app do chatbot
    'chatbot',
]

MIDDLEWARE = [
    # CorsMiddleware deve vir primeiro!
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# Permite requisições de qualquer origem (necessário para o frontend local)
CORS_ALLOW_ALL_ORIGINS = True

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
]

LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ============================================================
# CONFIGURAÇÕES DA IA — LangChain + OpenAI + LangSmith
# ============================================================

# Chave da API OpenAI — lida do .env
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')

# Modelo GPT a ser utilizado
OPENAI_MODEL = 'gpt-4o-mini'  # Mais rápido e barato; troque por 'gpt-4' se preferir

# Temperatura: 0 = determinístico, 1 = criativo. 0.7 é bom para tutoriais.
OPENAI_TEMPERATURE = 0.7

# Número máximo de tokens na resposta
OPENAI_MAX_TOKENS = 1500

# Quantas mensagens do histórico manter no contexto (memória da conversa)
CHAT_HISTORY_LIMIT = 10

# ============================================================
# LANGSMITH — Monitoramento e rastreamento (opcional)
# ============================================================
# Quando configurado, registra cada chamada à LLM no painel do LangSmith
# Acesse: https://smith.langchain.com para visualizar os traces

LANGCHAIN_TRACING_V2 = os.getenv('LANGCHAIN_TRACING_V2', 'false').lower() == 'true'
LANGCHAIN_API_KEY = os.getenv('LANGCHAIN_API_KEY', '')
LANGCHAIN_PROJECT = os.getenv('LANGCHAIN_PROJECT', 'python-tutor-chatbot')

# Propaga as configurações do LangSmith como variáveis de ambiente
# (necessário para o SDK do LangSmith funcionar)
if LANGCHAIN_TRACING_V2 and LANGCHAIN_API_KEY:
    os.environ['LANGCHAIN_TRACING_V2'] = 'true'
    os.environ['LANGCHAIN_API_KEY'] = LANGCHAIN_API_KEY
    os.environ['LANGCHAIN_PROJECT'] = LANGCHAIN_PROJECT
