import os
import pytest

# Garante que GEMINI_API_KEY não está definida durante os testes,
# evitando chamadas reais à API do Gemini ao importar server.py
os.environ.pop("GEMINI_API_KEY", None)

import server  # noqa: E402


@pytest.fixture
def client():
    """Cliente Flask com rate limiting desabilitado."""
    server.app.config["TESTING"] = True
    server.app.config["RATELIMIT_ENABLED"] = False
    with server.app.test_client() as c:
        yield c
    server.app.config["RATELIMIT_ENABLED"] = True


@pytest.fixture
def client_with_rate_limit():
    """Cliente Flask com rate limiting habilitado (para testes de throttle)."""
    server.app.config["TESTING"] = True
    server.app.config["RATELIMIT_ENABLED"] = True
    with server.app.test_client() as c:
        yield c
