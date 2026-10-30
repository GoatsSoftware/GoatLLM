# Discord setup and compatibility

Checked against official documentation and installed `discord.py==2.7.1` on
2026-10-30. Offline tests verify serialization; live group DM operation remains
unverified. See [manual testing](MANUAL_TESTING.md).

## Application configuration

1. Open the [Developer Portal](https://discord.com/developers/applications), create
   a dedicated application, and keep it separate from any production bot.
2. On **Installation**, enable **User Install**. Guild Install is unnecessary for M1.
   Select **Discord Provided Link**, configure User Install with the
   `applications.commands` scope, and save. Do not request Administrator or a guild
   bot invite for this path.
3. On **Bot**, obtain/reset the application's bot token and save it only in your
   local `.env`. A bot token authenticates the official application, even though no
   bot member joins the group. Do not use your personal account token.
4. Leave privileged intents disabled. Leave **Interactions Endpoint URL** empty:
   GoatLLM uses Gateway delivery rather than an inbound HTTP webhook.
5. Copy the provided install link and choose **Add to my apps**. Repeat for each
   friend who needs to invoke the command. Installation eligibility, app distribution
   settings, and Discord account policy still apply; check the portal's displayed
   restrictions if another account cannot install it.
6. Enable Discord Developer Mode in the Discord client, copy your numeric user ID,
   and populate `DISCORD_ALLOWED_USER_IDS`. App installation alone grants no GoatLLM
   authorization. Anyone seeing a public response can read it regardless of allowlist.
7. Once runtime implementation lands, start one host instance. It will sync `/ask`
   globally in `setup_hook()`. Global commands are needed for private channels;
   a guild-only development sync is not a substitute. Allow propagation/client
   refresh time if the command does not immediately appear.
8. Invoke `/ask` in a real group DM and confirm all participants can see the answer.
   Guild and bot-DM contexts are secondary tests, subject to Discord policy.

## Verified command definition

```python
@app_commands.command(name="ask", description="Ask the locally hosted LLM")
@app_commands.allowed_installs(guilds=False, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def ask(interaction: discord.Interaction, prompt: str) -> None: ...
```

These decorators serialize as `integration_types=[1]` (USER_INSTALL) and
`contexts=[0,1,2]` (GUILD, BOT_DM, PRIVATE_CHANNEL). `guilds=True` in contexts makes
the user-installed command eligible in server channels; it does not require a guild
installation. Server settings can restrict external app use/public replies.
PRIVATE_CHANNEL covers DMs with other users and group DMs and requires USER_INSTALL.
The installed library exposes the APIs; only a real installation can confirm the
end-to-end Discord experience.

Discord requires an initial acknowledgment within three seconds; interaction tokens
last fifteen minutes. The plan immediately defers admitted requests, then edits the
original non-ephemeral response. Pre-generation rejections can be ephemeral.
No intents are needed to receive interactions. No public endpoint or ngrok is needed.

## Troubleshooting when the runtime exists

- Missing `/ask`: verify User Install on the application and command, global sync,
  PRIVATE_CHANNEL context, installation on the invoking account, and client refresh.
- No interaction reaches the host: check token and Gateway connection; clear any
  Interactions Endpoint URL that routes delivery elsewhere. Do not run two instances.
- Visible only to the invoker: inspect external app permissions/context. Successful
  public group DM output remains a required acceptance check.
- Token rejected: reset it in the portal and update `.env`; never log it.
- Commands disappeared from another project: use a separate Discord application;
  global tree sync reconciles all commands owned by that application.

## Primary sources

- [Discord user-installable application tutorial](https://docs.discord.com/developers/tutorials/developing-a-user-installable-app)
- [Application command installation and interaction contexts](https://docs.discord.com/developers/interactions/application-commands#installation-context)
- [Interaction delivery, deadlines, and responses](https://docs.discord.com/developers/interactions/receiving-and-responding)
- [discord.py allowed installs](https://discordpy.readthedocs.io/en/stable/interactions/api.html#discord.app_commands.allowed_installs)
- [discord.py allowed contexts](https://discordpy.readthedocs.io/en/stable/interactions/api.html#discord.app_commands.allowed_contexts)
- [discord.py defer](https://discordpy.readthedocs.io/en/stable/interactions/api.html#discord.InteractionResponse.defer)
