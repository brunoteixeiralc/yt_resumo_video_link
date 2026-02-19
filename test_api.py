"""
Testes de integração para a lógica de fallback de idioma da transcrição.

Por padrão, estes testes usam mocks para evitar dependência de rede.
Para rodar os testes reais contra a API do YouTube, use:

    pytest test_api.py -m live
"""

from unittest.mock import MagicMock

import pytest

from youtube_transcript_api import YouTubeTranscriptApi


# ─── helpers ──────────────────────────────────────────────────────────────────

PRIORITY_LANGUAGES = ['pt-BR', 'en']


def _fallback_logic(video_id):
    """Replica a lógica de seleção de idioma de server.py."""
    api = YouTubeTranscriptApi()
    transcript_list = api.list(video_id)
    try:
        transcript = transcript_list.find_transcript(PRIORITY_LANGUAGES)
    except Exception:
        transcript = next(iter(transcript_list))
    return transcript.language_code


def _make_transcript_mock(lang_code):
    t = MagicMock()
    t.language_code = lang_code
    return t


# ─── testes com mock (padrão) ─────────────────────────────────────────────────

class TestFallbackLogicMocked:
    def test_seleciona_ingles_quando_unico_disponivel(self, monkeypatch):
        transcript_en = _make_transcript_mock("en")
        transcript_list = MagicMock()
        transcript_list.find_transcript.return_value = transcript_en

        monkeypatch.setattr(
            "test_api.YouTubeTranscriptApi",
            lambda: MagicMock(list=lambda vid: transcript_list),
        )

        assert _fallback_logic("VIDEO_EN") == "en"

    def test_seleciona_pt_br_quando_disponivel(self, monkeypatch):
        transcript_pt = _make_transcript_mock("pt-BR")
        transcript_list = MagicMock()
        transcript_list.find_transcript.return_value = transcript_pt

        monkeypatch.setattr(
            "test_api.YouTubeTranscriptApi",
            lambda: MagicMock(list=lambda vid: transcript_list),
        )

        assert _fallback_logic("VIDEO_PT") == "pt-BR"

    def test_fallback_para_primeiro_disponivel_quando_sem_idioma_prioritario(
        self, monkeypatch
    ):
        transcript_ja = _make_transcript_mock("ja")
        transcript_list = MagicMock()
        transcript_list.find_transcript.side_effect = Exception("não encontrado")
        transcript_list.__iter__ = MagicMock(return_value=iter([transcript_ja]))

        monkeypatch.setattr(
            "test_api.YouTubeTranscriptApi",
            lambda: MagicMock(list=lambda vid: transcript_list),
        )

        assert _fallback_logic("VIDEO_JA") == "ja"


# ─── testes ao vivo (requerem rede) ──────────────────────────────────────────

@pytest.mark.live
class TestFallbackLogicLive:
    """
    Testes que fazem chamadas reais à API do YouTube.
    Execute com: pytest test_api.py -m live
    """

    def test_video_ingles_retorna_en(self):
        lang = _fallback_logic('HwKDe80NydA')
        assert lang == 'en', f"Esperava 'en', obteve '{lang}'"

    def test_video_portugues_retorna_pt_br(self):
        lang = _fallback_logic('hlkYw4kL9A0')
        assert lang == 'pt-BR', f"Esperava 'pt-BR', obteve '{lang}'"
