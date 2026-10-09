"""Isolated PostgreSQL tests and preview; never uses application database settings."""

from reservation_backend.settings_test import *  # noqa: F403,F401
from reservation_backend.settings import INSTALLED_APPS  # noqa: F401

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "reservation_release_preview",
        "USER": "reservation_preview",
        "HOST": "127.0.0.1",
        "PORT": "55442",
        "PASSWORD": "",
    }
}
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
ALLOWED_HOSTS = ["127.0.0.1", "localhost", "testserver"]
CORS_ALLOWED_ORIGINS = ["http://127.0.0.1:3002", "http://localhost:3002"]
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_SSL_REDIRECT = False
