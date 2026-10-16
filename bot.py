"""
Entrypoint for the private Discord "spam" bot.

This module owns the parts everything else depends on: config/env loading,
the Discord client and the allow-list-gated command tree, and wiring it all
together with the health-check web server at startup.

Slash commands and the "Spam" resend button live in commands.py; the
health-check HTTP server lives in health.py. Importing commands.py below is
what actually registers /send and /ping on the tree — see the comment there.
"""

import asyncio
import logging
import os

import discord
from discord import app_commands
from dotenv import load_dotenv

from health import start_web_server

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

# Registers /send, /ping, the tree's error handler, and the "Spam" button's
# custom_id handler onto `tree` (imported from this module) as a side effect.
import commands  # noqa: E402,F401

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


async def main():
    discord.utils.setup_logging()

    # Re-attach the handler behind the "Spam" button's custom_id so clicks on
    # buttons from before a restart still work (see commands.py for how the
    # actual message/owner/mentions are recovered from disk).
    bot.add_view(commands.ResendView())

    await start_web_server(bot)  # start the web server first so Render sees the open port
    async with bot:
        await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
