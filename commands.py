"""
Slash commands (/send, /ping) and the "Spam" resend button.

Importing this module from bot.py is what registers these commands on
`tree` — the decorators below run at import time and attach themselves to
the tree object imported from bot.py.

The "Spam" button is a *persistent* view (timeout=None, a fixed custom_id)
so Discord keeps routing clicks to it even after the bot process restarts.
Since Discord only remembers the custom_id and not any Python state attached
to the original view instance, the actual message text, requester, and
mention settings for each batch are saved to spam_store.json (see
SPAM_STORE below) keyed by message id, and looked back up when the button is
clicked. This is the one piece of state the bot persists to disk; it's
listed in PRIVACY.md for that reason.
"""

import json
import logging
from pathlib import Path

import discord
from discord import app_commands

from bot import bot, tree

log = logging.getLogger("spam-bot")

# How many times a message is reposted per /send call or "Spam" button press.
REPEAT_COUNT = 5

# Discord's hard cap on a single message's length (mentions count towards it).
MAX_MESSAGE_LENGTH = 2000

NO_MENTIONS = discord.AllowedMentions.none()

# --------------------------------------------------------------------------
# Persisted "Spam" button state
# --------------------------------------------------------------------------

STORE_PATH = Path(__file__).parent / "spam_store.json"

# Caps how many past batches we remember, so the file can't grow forever.
# Oldest entries are dropped first once the cap is hit.
MAX_STORE_ENTRIES = 500


def _load_store() -> dict[int, dict]:
    if not STORE_PATH.exists():
        return {}
    try:
        with STORE_PATH.open("r", encoding="utf-8") as handle:
            raw = json.load(handle)
        return {int(message_id): data for message_id, data in raw.items()}
    except (json.JSONDecodeError, OSError, ValueError) as error:
        log.warning("Could not load %s, starting with an empty store: %s", STORE_PATH.name, error)
        return {}


def _save_store() -> None:
    try:
        with STORE_PATH.open("w", encoding="utf-8") as handle:
            json.dump({str(message_id): data for message_id, data in SPAM_STORE.items()}, handle)
    except OSError as error:
        log.warning("Could not save %s: %s", STORE_PATH.name, error)


# message_id -> {"text": str, "owner_id": int, "everyone": bool, "mention_user_id": int | None}
SPAM_STORE: dict[int, dict] = _load_store()


def remember_batch(
    message_id: int,
    *,
    text: str,
    owner_id: int,
    everyone: bool,
    mention_user_id: int | None,
) -> None:
    """Record what a /send batch contained so the "Spam" button can replay it later."""
    SPAM_STORE[message_id] = {
        "text": text,
        "owner_id": owner_id,
        "everyone": everyone,
        "mention_user_id": mention_user_id,
    }
    if len(SPAM_STORE) > MAX_STORE_ENTRIES:
        oldest_message_id = next(iter(SPAM_STORE))
        del SPAM_STORE[oldest_message_id]
    _save_store()


def mentions_for(everyone: bool, mention_user_id: int | None) -> discord.AllowedMentions:
    return discord.AllowedMentions(
        everyone=everyone,
        users=[discord.Object(id=mention_user_id)] if mention_user_id else False,
        roles=False,
    )


# --------------------------------------------------------------------------
# Message sending
# --------------------------------------------------------------------------


async def send_many(
    interaction: discord.Interaction,
    text: str,
    count: int,
    mentions: discord.AllowedMentions,
) -> tuple[int, bool]:
    """Send `text` to the invoking channel `count` times.

    Tries interaction.channel.send() first. If that fails (DM edge cases,
    missing permissions, a transient Discord error), it falls back to
    interaction.followup.send() for the rest of the batch.

    Returns (messages_sent, was_capped) where was_capped is True if Discord
    rejected a send partway through, so the caller can tell the user some
    messages didn't go out.
    """
    sent = 0
    use_followup = False

    for _ in range(count):
        if not use_followup:
            try:
                await interaction.channel.send(text, allowed_mentions=mentions)
                sent += 1
                continue
            except (AttributeError, discord.Forbidden, discord.HTTPException) as error:
                log.warning("channel.send failed, falling back to followup: %s", error)
                use_followup = True

        try:
            await interaction.followup.send(text, allowed_mentions=mentions)
            sent += 1
        except discord.HTTPException as error:
            log.warning("followup.send failed after %d/%d messages: %s", sent, count, error)
            return sent, True

    return sent, False


async def report_if_capped(interaction: discord.Interaction, sent: int, requested: int, capped: bool):
    """Edit the original response to warn the user if not every message went out."""
    if not capped:
        return
    try:
        await interaction.edit_original_response(
            content=f"Sent {sent} of {requested}. Discord's limit stopped the rest."
        )
    except discord.HTTPException as error:
        log.warning("Could not report capped send: %s", error)


# --------------------------------------------------------------------------
# "Spam" resend button
# --------------------------------------------------------------------------


class ResendView(discord.ui.View):
    """Persistent view backing the "Spam" button.

    Carries no per-message state on the Python object itself — Discord only
    round-trips the button's custom_id, including after a restart, so the
    real text/owner/mentions are looked up from SPAM_STORE using the id of
    the message the button is attached to.
    """

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Spam", style=discord.ButtonStyle.danger, custom_id="spam_bot:resend")
    async def resend(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = SPAM_STORE.get(interaction.message.id)
        if data is None:
            try:
                await interaction.response.send_message(
                    "This button has expired. Run /send again.", ephemeral=True
                )
            except discord.NotFound:
                pass
            return

        if interaction.user.id != data["owner_id"]:
            try:
                await interaction.response.send_message(
                    "Only the person who ran this command can use this button.",
                    ephemeral=True,
                )
            except discord.NotFound:
                pass
            return

        try:
            await interaction.response.defer()
        except discord.NotFound:
            return  # interaction expired before we could even defer

        mentions = mentions_for(data["everyone"], data["mention_user_id"])
        sent, capped = await send_many(interaction, data["text"], REPEAT_COUNT, mentions)
        await report_if_capped(interaction, sent, REPEAT_COUNT, capped)


# --------------------------------------------------------------------------
# Slash commands
# --------------------------------------------------------------------------


@tree.command(name="send", description="Send a message")
@app_commands.describe(
    text="The message you want to send",
    user="Optional: a user to mention in each message",
    everyone="Optional: add an @everyone ping to all messages",
)
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def send(
    interaction: discord.Interaction,
    text: str,
    user: discord.User | None = None,
    everyone: bool = False,
):
    content = f"{user.mention} {text}" if user else text

    # @everyone only means anything inside a guild; ignore the flag in DMs.
    ping_everyone = everyone and interaction.guild is not None
    if ping_everyone:
        content = f"@everyone {content}"

    mentions = mentions_for(ping_everyone, user.id if user else None)

    if len(content) > MAX_MESSAGE_LENGTH:
        try:
            await interaction.response.send_message(
                f"Your message must be {MAX_MESSAGE_LENGTH} characters or fewer (mentions count).",
                ephemeral=True,
            )
        except discord.NotFound:
            pass
        return

    try:
        await interaction.response.send_message(
            f"Sending {REPEAT_COUNT} messages... Press the button to send them again.",
            view=ResendView(),
            ephemeral=True,
        )
    except discord.NotFound:
        return

    # Save what this batch was so the button above still works after a
    # restart. Best-effort: if this fails, /send itself still works fine,
    # the button just won't come back to life later.
    try:
        original = await interaction.original_response()
        remember_batch(
            original.id,
            text=content,
            owner_id=interaction.user.id,
            everyone=ping_everyone,
            mention_user_id=user.id if user else None,
        )
    except discord.HTTPException as error:
        log.warning("Could not register the Spam button for later: %s", error)

    sent, capped = await send_many(interaction, content, REPEAT_COUNT, mentions)
    await report_if_capped(interaction, sent, REPEAT_COUNT, capped)


@tree.command(name="ping", description="Check the bot's latency.")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def ping(interaction: discord.Interaction):
    try:
        await interaction.response.send_message(f"Pong! `{round(bot.latency * 1000)} ms`")
    except discord.NotFound:
        pass


@tree.error
async def on_tree_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    """Catch-all so a bug in one command is logged instead of vanishing silently."""
    log.exception("Unhandled error in command %r", interaction.command, exc_info=error)
    try:
        if interaction.response.is_done():
            await interaction.followup.send("Something went wrong running that command.", ephemeral=True)
        else:
            await interaction.response.send_message("Something went wrong running that command.", ephemeral=True)
    except discord.HTTPException:
        pass
