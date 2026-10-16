"""
Entrypoint. Run the bot with `python main.py` (not `python bot.py` —
see the warning at the top of bot.py for why that matters).

Importing `commands` here is what registers /send, /ping, the tree's error
handler, and the "Spam" button's custom_id handler onto `bot.tree`.
"""

import asyncio

import discord

import commands  # noqa: F401
from bot import TOKEN, bot
from health import start_web_server


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
