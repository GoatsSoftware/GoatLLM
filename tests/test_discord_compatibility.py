"""Verify the installed Discord APIs without connecting or registering commands."""

import discord

from goatllm.discord_app import GoatClient


def test_user_install_private_channel_command_payload(settings) -> None:
    client = GoatClient(settings, None)
    payload = client.tree.get_command("ask").to_dict(client.tree)
    assert discord.__version__ == "2.7.1"
    assert payload["integration_types"] == [1]  # USER_INSTALL
    assert set(payload["contexts"]) == {0, 1, 2}  # GUILD, BOT_DM, PRIVATE_CHANNEL
    assert payload["options"][0]["name"] == "prompt"
    assert payload["options"][0]["max_length"] == settings.max_prompt_chars
    assert client.intents.value == 0


def test_mentions_disabled_including_replies() -> None:
    assert discord.AllowedMentions.none().to_dict() == {"parse": []}
