"""Verify the installed Discord APIs without connecting or registering commands."""

import discord
from discord import app_commands


def test_user_install_private_channel_command_payload() -> None:
    @app_commands.command(name="ask", description="Ask the locally hosted LLM")
    @app_commands.allowed_installs(guilds=False, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def ask(interaction: discord.Interaction, prompt: str) -> None:
        pass

    client = discord.Client(intents=discord.Intents.none())
    tree = app_commands.CommandTree(client)
    payload = ask.to_dict(tree)
    assert discord.__version__ == "2.7.1"
    assert payload["integration_types"] == [1]  # USER_INSTALL
    assert set(payload["contexts"]) == {0, 1, 2}  # GUILD, BOT_DM, PRIVATE_CHANNEL
    assert payload["options"][0]["name"] == "prompt"
    assert client.intents.value == 0


def test_mentions_disabled_including_replies() -> None:
    assert discord.AllowedMentions.none().to_dict() == {"parse": []}
