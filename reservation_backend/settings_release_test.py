"""Isolated local PostgreSQL; never use the application-configured database."""
import getpass
import os
from .settings_test import *
DATABASES={'default':{'ENGINE':'django.db.backends.postgresql','HOST':'127.0.0.1','PORT':os.environ.get('RESERVATION_RELEASE_POSTGRES_PORT','56445'),'NAME':'reservation_ai_preview','USER':getpass.getuser(),'TEST':{'NAME':'reservation_ai_isolated_test','CHARSET':'UTF8','TEMPLATE':'template0'}}}
ALLOWED_HOSTS=['localhost','127.0.0.1','testserver']
INSTALLED_APPS=[*INSTALLED_APPS,'simple_history']
MIDDLEWARE=[*MIDDLEWARE,'simple_history.middleware.HistoryRequestMiddleware']
PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher']
CACHES={'default':{'BACKEND':'django.core.cache.backends.locmem.LocMemCache'}}
CHAT_AI_ASSISTANT_ENABLED=True
CHAT_AI_MODEL_URL='http://127.0.0.1:9/v1'
CHAT_AI_MODEL_ID='isolated-test-no-inference'
CHAT_AI_MODEL_TIMEOUT=2
