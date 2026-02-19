"""
Suite de testes para server.py.

Cobre:
- get_video_id: parsing de URLs do YouTube
- /summarize endpoint: validações, erros e fluxo feliz
- fetch_transcript: prioridade de idioma e fallbacks
- summarize_text: ausência de chave, sucesso e erros da API
- rate limiting: bloqueio após 10 requisições/min
- rota /: renderização da página inicial
"""

from unittest.mock import MagicMock, patch

import pytest

import server
from server import fetch_transcript, get_video_id, summarize_text


# ─── helpers ─────────────────────────────────────────────────────────────────

def _make_snippet(text):
    s = MagicMock()
    s.text = text
    return s


def _make_transcript(lang_code, texts):
    t = MagicMock()
    t.language_code = lang_code
    fetched = MagicMock()
    fetched.snippets = [_make_snippet(tx) for tx in texts]
    t.fetch.return_value = fetched
    return t


# ─── get_video_id ────────────────────────────────────────────────────────────

class TestGetVideoId:
    def test_url_padrao(self):
        assert get_video_id("https://www.youtube.com/watch?v=ABC123") == "ABC123"

    def test_url_padrao_com_outros_params(self):
        assert get_video_id("https://www.youtube.com/watch?v=ABC123&t=30&list=PL") == "ABC123"

    def test_url_curta(self):
        assert get_video_id("https://youtu.be/ABC123") == "ABC123"

    def test_url_curta_com_timestamp(self):
        assert get_video_id("https://youtu.be/ABC123?t=30") == "ABC123"

    def test_url_embed(self):
        # URL de embed não contém "v=" nem "youtu.be/" → None
        result = get_video_id("https://www.youtube.com/embed/ABC123")
        assert result is None

    def test_url_invalida_retorna_none(self):
        assert get_video_id("https://example.com/video") is None

    def test_string_vazia_retorna_none(self):
        assert get_video_id("") is None


# ─── /summarize — validações de entrada ──────────────────────────────────────

class TestSummarizeEndpointValidation:
    def test_sem_body_retorna_415(self, client):
        # Flask 3+ retorna 415 quando Content-Type não é application/json
        resp = client.post("/summarize")
        assert resp.status_code == 415

    def test_content_type_errado_retorna_415(self, client):
        # Flask 3+ retorna 415 para Content-Type incompatível com JSON
        resp = client.post(
            "/summarize",
            data="url=https://youtu.be/ABC123",
            content_type="application/x-www-form-urlencoded",
        )
        assert resp.status_code == 415

    def test_json_sem_campo_url_retorna_400(self, client):
        resp = client.post("/summarize", json={})
        assert resp.status_code == 400
        assert "error" in resp.get_json()

    def test_url_invalida_retorna_400(self, client):
        resp = client.post("/summarize", json={"url": "https://example.com/notayoutube"})
        assert resp.status_code == 400
        assert "error" in resp.get_json()


# ─── /summarize — fluxo do negócio ───────────────────────────────────────────

class TestSummarizeEndpointFlow:
    def test_sem_transcricao_retorna_404(self, client):
        with patch("server.fetch_transcript", return_value=None):
            resp = client.post("/summarize", json={"url": "https://youtu.be/ABC123"})
        assert resp.status_code == 404
        assert "error" in resp.get_json()

    def test_sucesso_retorna_resumo(self, client):
        with patch("server.fetch_transcript", return_value="transcrição de exemplo"), \
             patch("server.summarize_text", return_value="resumo gerado"):
            resp = client.post("/summarize", json={"url": "https://youtu.be/ABC123"})
        assert resp.status_code == 200
        assert resp.get_json()["summary"] == "resumo gerado"

    def test_transcricao_longa_e_truncada(self, client):
        texto_longo = "a" * 200_000
        capturado = {}

        def resumir_fake(text):
            capturado["text"] = text
            return "resumo"

        with patch("server.fetch_transcript", return_value=texto_longo), \
             patch("server.summarize_text", side_effect=resumir_fake):
            client.post("/summarize", json={"url": "https://youtu.be/ABC123"})

        assert len(capturado["text"]) <= 100_003  # 100000 + len("...")
        assert capturado["text"].endswith("...")

    def test_transcricao_no_limite_nao_e_truncada(self, client):
        texto_exato = "b" * 100_000
        capturado = {}

        def resumir_fake(text):
            capturado["text"] = text
            return "resumo"

        with patch("server.fetch_transcript", return_value=texto_exato), \
             patch("server.summarize_text", side_effect=resumir_fake):
            client.post("/summarize", json={"url": "https://youtu.be/ABC123"})

        assert capturado["text"] == texto_exato


# ─── rate limiting ────────────────────────────────────────────────────────────

class TestRateLimiting:
    def test_rate_limit_apos_10_requisicoes(self, client_with_rate_limit):
        with patch("server.fetch_transcript", return_value=None):
            respostas = [
                client_with_rate_limit.post(
                    "/summarize", json={"url": "https://youtu.be/ABC123"}
                )
                for _ in range(11)
            ]
        codigos = [r.status_code for r in respostas]
        assert 429 in codigos, (
            f"Esperava HTTP 429 após 10 requisições, mas obteve apenas: {set(codigos)}"
        )

    def test_rota_index_nao_tem_rate_limit(self, client_with_rate_limit):
        # A rota raiz não tem limitador — todas as 15 chamadas devem retornar 200
        respostas = [client_with_rate_limit.get("/") for _ in range(15)]
        assert all(r.status_code == 200 for r in respostas)


# ─── fetch_transcript ─────────────────────────────────────────────────────────

class TestFetchTranscript:
    def test_prefere_pt_br(self):
        transcript_pt = _make_transcript("pt-BR", ["Olá", "mundo"])
        transcript_list = MagicMock()
        transcript_list.find_transcript.return_value = transcript_pt

        with patch("server.YouTubeTranscriptApi") as MockApi:
            MockApi.return_value.list.return_value = transcript_list
            result = fetch_transcript("VIDEO_ID")

        assert result == "Olá mundo"

    def test_usa_ingles_quando_disponivel(self):
        transcript_en = _make_transcript("en", ["Hello", "world"])
        transcript_list = MagicMock()
        transcript_list.find_transcript.return_value = transcript_en

        with patch("server.YouTubeTranscriptApi") as MockApi:
            MockApi.return_value.list.return_value = transcript_list
            result = fetch_transcript("VIDEO_ID")

        assert result == "Hello world"

    def test_fallback_para_primeiro_disponivel_quando_idioma_nao_encontrado(self):
        transcript_fr = _make_transcript("fr", ["Bonjour", "monde"])
        transcript_list = MagicMock()
        transcript_list.find_transcript.side_effect = Exception("idioma não encontrado")
        transcript_list.__iter__ = MagicMock(return_value=iter([transcript_fr]))

        with patch("server.YouTubeTranscriptApi") as MockApi:
            MockApi.return_value.list.return_value = transcript_list
            result = fetch_transcript("VIDEO_ID")

        assert result == "Bonjour monde"

    def test_retorna_none_quando_api_falha(self):
        with patch("server.YouTubeTranscriptApi") as MockApi:
            MockApi.return_value.list.side_effect = Exception("erro de rede")
            result = fetch_transcript("VIDEO_ID")

        assert result is None

    def test_concatena_snippets_com_espaco(self):
        transcript = _make_transcript("en", ["palavra1", "palavra2", "palavra3"])
        transcript_list = MagicMock()
        transcript_list.find_transcript.return_value = transcript

        with patch("server.YouTubeTranscriptApi") as MockApi:
            MockApi.return_value.list.return_value = transcript_list
            result = fetch_transcript("VIDEO_ID")

        assert result == "palavra1 palavra2 palavra3"


# ─── summarize_text ───────────────────────────────────────────────────────────

class TestSummarizeText:
    def test_retorna_erro_quando_sem_modelo(self):
        original = server.gemini_model
        server.gemini_model = None
        try:
            result = summarize_text("qualquer texto")
        finally:
            server.gemini_model = original

        assert "Error" in result

    def test_retorna_resumo_gerado(self):
        mock_model = MagicMock()
        mock_model.generate_content.return_value.text = "Resumo gerado com sucesso."
        original = server.gemini_model
        server.gemini_model = mock_model
        try:
            result = summarize_text("transcrição de exemplo")
        finally:
            server.gemini_model = original

        assert result == "Resumo gerado com sucesso."
        mock_model.generate_content.assert_called_once()

    def test_prompt_contem_transcricao(self):
        mock_model = MagicMock()
        mock_model.generate_content.return_value.text = "ok"
        original = server.gemini_model
        server.gemini_model = mock_model
        try:
            summarize_text("minha transcrição especial")
        finally:
            server.gemini_model = original

        chamada = mock_model.generate_content.call_args[0][0]
        assert "minha transcrição especial" in chamada

    def test_retorna_mensagem_de_erro_em_excecao(self):
        mock_model = MagicMock()
        mock_model.generate_content.side_effect = Exception("falha na API")
        original = server.gemini_model
        server.gemini_model = mock_model
        try:
            result = summarize_text("texto")
        finally:
            server.gemini_model = original

        assert "Error summarizing" in result


# ─── rota / ──────────────────────────────────────────────────────────────────

class TestIndexRoute:
    def test_index_retorna_200(self, client):
        resp = client.get("/")
        assert resp.status_code == 200

    def test_index_retorna_html(self, client):
        resp = client.get("/")
        assert b"html" in resp.data.lower()
