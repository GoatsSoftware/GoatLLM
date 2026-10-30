"""Discord transport, non-queueing admission, and safe single-message responses."""

import asyncio
import logging

import discord
from discord import app_commands

from goatllm.config import Settings
from goatllm.llm.base import LLMProvider, ProviderError, ProviderErrorCode

logger = logging.getLogger("goatllm")
TRUNCATION_NOTICE = "\n\n[Response truncated.]"
ERROR_MESSAGES = {
    ProviderErrorCode.UNAVAILABLE: "The host cannot reach Ollama. Please ask the host to check it.",
    ProviderErrorCode.TIMEOUT: "The model took too long to answer. Please try again later.",
    ProviderErrorCode.MODEL_NOT_FOUND: "The host needs to check or install its configured model.",
    ProviderErrorCode.INVALID_RESPONSE: "The model returned an unusable answer. Please try again.",
    ProviderErrorCode.GENERATION_FAILED: (
        "Generation failed. The host should check its model and resources."
    ),
}
INTERNAL_ERROR = "Something went wrong while answering. Please try again later."


def render_response(text: str) -> str:
    """Fit one content field, counting supplementary Unicode characters conservatively."""
    if not isinstance(text, str) or not text.strip():
        raise ProviderError(ProviderErrorCode.INVALID_RESPONSE)
    # Invalid surrogate escapes can appear in untrusted JSON strings.
    text = text.encode("utf-8", errors="replace").decode("utf-8").strip()
    if sum(2 if ord(char) > 0xFFFF else 1 for char in text) <= 2000:
        return text
    budget = 2000 - len(TRUNCATION_NOTICE)
    used = 0
    end = 0
    for index, char in enumerate(text):
        used += 2 if ord(char) > 0xFFFF else 1
        if used > budget:
            end = index
            break
    prefix = text[:end]
    boundary = max(prefix.rfind("\n"), prefix.rfind(" "))
    if boundary >= len(prefix) - 120:
        prefix = prefix[:boundary]
    return prefix.rstrip() + TRUNCATION_NOTICE


class GoatClient(discord.Client):
    def __init__(self, settings: Settings, provider: LLMProvider) -> None:
        super().__init__(
            intents=discord.Intents.none(), allowed_mentions=discord.AllowedMentions.none()
        )
        self.settings = settings
        self.provider = provider
        self.tree = app_commands.CommandTree(self)
        self.tree.on_error = self.command_error
        self._active = 0
        self._handlers: set[asyncio.Task] = set()
        self._stopping = False
        self.tree.add_command(build_ask_command(self))

    async def setup_hook(self) -> None:
        await self.tree.sync()
        logger.info("commands_synced")

    async def on_ready(self) -> None:
        logger.info("discord_ready")

    async def on_error(self, event_method: str, *args, **kwargs) -> None:
        # Override discord.py's default traceback handler; event args may be private.
        logger.error("discord_event_failed")

    async def command_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        logger.warning("command_rejected")
        if not interaction.response.is_done():
            await self._reject(
                interaction, "The command could not be processed. Please check its input."
            )

    async def _reject(self, interaction: discord.Interaction, message: str) -> None:
        try:
            await interaction.response.send_message(
                message,
                ephemeral=True,
                allowed_mentions=discord.AllowedMentions.none(),
                suppress_embeds=True,
            )
        except discord.HTTPException:
            logger.warning("discord_reply_failed")

    async def ask(self, interaction: discord.Interaction, prompt: str) -> None:
        if interaction.user.id not in self.settings.allowed_user_ids:
            await self._reject(interaction, "You are not authorized to use this application.")
            return
        if not prompt.strip() or len(prompt) > self.settings.max_prompt_chars:
            await self._reject(
                interaction, "Please provide a nonblank prompt within the command limit."
            )
            return
        if self._stopping or self._active >= self.settings.max_concurrent_generations:
            await self._reject(interaction, "The host is busy. Please try again later.")
            return

        # No await between capacity check and reservation: one asyncio event loop.
        self._active += 1
        task = asyncio.current_task()
        if task is not None:
            self._handlers.add(task)
        try:
            await interaction.response.defer(thinking=True, ephemeral=False)
            try:
                # Enforce the deadline even if a future provider forgets to do so.
                async with asyncio.timeout(self.settings.generation.timeout_seconds):
                    answer = await self.provider.generate(
                        prompt,
                        self.settings.system_prompt,
                        self.settings.generation,
                    )
                content = render_response(answer)
                logger.info("generation_completed")
            except (ProviderError, TimeoutError) as error:
                code = error.code if isinstance(error, ProviderError) else ProviderErrorCode.TIMEOUT
                logger.warning("generation_failed_%s", code.value)
                content = ERROR_MESSAGES[code]
            except Exception:
                logger.error("generation_failed_unexpected")
                content = INTERNAL_ERROR
            # The pinned original-response API has no suppress_embeds option.
            await interaction.edit_original_response(
                content=content,
                allowed_mentions=discord.AllowedMentions.none(),
            )
        except discord.HTTPException:
            logger.warning("discord_reply_failed")
        finally:
            self._active -= 1
            if task is not None:
                self._handlers.discard(task)

    async def close(self) -> None:
        self._stopping = True
        current = asyncio.current_task()
        tasks = [task for task in self._handlers if task is not current]
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        await super().close()


def build_ask_command(client: GoatClient) -> app_commands.Command:
    async def ask(interaction: discord.Interaction, prompt: str) -> None:
        await client.ask(interaction, prompt)

    # Range is evaluated against the configured limit, without postponed annotations.
    ask.__annotations__["prompt"] = app_commands.Range[str, 1, client.settings.max_prompt_chars]
    command = app_commands.command(
        name=client.settings.command_name,
        description="Ask the locally hosted LLM",
    )(ask)
    command = app_commands.allowed_installs(guilds=False, users=True)(command)
    return app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)(command)
