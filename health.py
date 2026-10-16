"""
A tiny HTTP server with a health-check endpoint.

Render (and hosts like it) expect a web process to have an open port and
will restart it if a health check fails, so this runs alongside the Discord
client purely to keep the host happy and to surface connection state.
"""

import logging
import os

import discord
from aiohttp import web

log = logging.getLogger("spam-bot")


def _make_health_handler(bot: discord.Client):
    async def handle_health(request: web.Request) -> web.Response:
        if bot.is_ready():
            return web.Response(text="Bot is running")
        return web.Response(text="Bot is starting up", status=503)

    return handle_health


async def start_web_server(bot: discord.Client) -> None:
    app = web.Application()
    handler = _make_health_handler(bot)
    app.router.add_get("/", handler)
    app.router.add_get("/health", handler)  # what Render's health check pings

    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", "10000"))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    log.info("Health check server listening on port %d", port)
