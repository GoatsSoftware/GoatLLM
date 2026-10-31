import pytest

from goatllm.discord_app import TRUNCATION_NOTICE, render_response
from goatllm.llm.base import ProviderError


@pytest.mark.parametrize("text", ["ok", "a" * 2000, "😀" * 1000, "@everyone @here <@123> <@&123>"])
def test_short_answers_unchanged(text):
    assert render_response(text) == text


@pytest.mark.parametrize("text", ["a" * 2001, "😀" * 1001, ("word 😀\n" * 1000), "x" * 100000])
def test_truncation_fits_discord_including_notice(text):
    result = render_response(text)
    assert result.endswith(TRUNCATION_NOTICE)
    assert len(result.encode("utf-16-le")) // 2 <= 2000
    assert text.startswith(result.removesuffix(TRUNCATION_NOTICE))


@pytest.mark.parametrize("text", ["", " \n ", None])
def test_empty_answers_are_errors(text):
    with pytest.raises(ProviderError):
        render_response(text)


def test_surrogates_do_not_break_transport():
    assert render_response("hello\ud800").encode("utf-8") == b"hello?"
