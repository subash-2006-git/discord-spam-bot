"""
Discord client, config, and the allow-list-gated command tree.

This module is imported by main.py (the real entrypoint) and by commands.py.

Important: never run this file directly with `python bot.py`. Doing so makes
Python treat it as the `__main__` module instead of as a module named `bot`,
and `commands.py`'s `from bot import bot, tree` would then reimport this
file a *second* time under the name `bot`, creating a second, separate
command tree that /send and /ping end up registered on instead of the one
that actually gets synced and run. Always start the bot with `python main.py`.
"""

import logging
import os

import discord
from discord import app_commands
from dotenv import load_dotenv

load_dotenv()

log = logging.getLogger("spam-bot")

# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("BOT_TOKEN is missing from .env")

# Comma-separated Discord user IDs allowed to use the bot, set in .env / Render.
ALLOWED_USER_IDS = {
    int(user_id) for user_id in os.getenv("ALLOWED_USER_IDS", "").split(",") if user_id.strip()
}

# Optional: a Discord user ID to DM a one-line log to every time /send (or the
# Spam button) fires. Leave unset in .env to disable this entirely.
_raw_log_user_id = os.getenv("LOG_USER_ID", "").strip()
LOG_USER_ID = int(_raw_log_user_id) if _raw_log_user_id else None

intents = discord.Intents.default()
bot = discord.Client(intents=intents)


# --------------------------------------------------------------------------
# Access control
# --------------------------------------------------------------------------


class FriendsOnlyTree(app_commands.CommandTree):
    """Command tree that blocks anyone not in ALLOWED_USER_IDS.

    interaction_check runs before every slash command (/send and /ping), so
    this is the single choke point for the bot's privacy guarantee.
    """

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id in ALLOWED_USER_IDS:
            return True

        log.info("Blocked command from unauthorized user %s", interaction.user.id)
        try:
            await interaction.response.send_message(
                "Sorry, this bot is private.", ephemeral=True
            )
        except discord.NotFound:
            pass  # interaction already expired; nothing more to do
        return False


tree = FriendsOnlyTree(bot)

# --------------------------------------------------------------------------
# Startup
# --------------------------------------------------------------------------

_synced_once = False


@bot.event
async def on_ready():
    global _synced_once
    log.info("Logged in as %s", bot.user)

    # Global command sync is slow to propagate and rate-limited, so only do
    # it once per process rather than on every reconnect.
    if not _synced_once:
        try:
            synced = await tree.sync()
            log.info("Synced %d global commands.", len(synced))
            _synced_once = True
        except discord.HTTPException as error:
            log.error("Command sync failed: %s", error)
