import os
import discord
from discord import app_commands
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise RuntimeError("BOT_TOKEN is missing from .env")

intents = discord.Intents.default()

bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

REPEAT_COUNT = 5
NO_MENTIONS = discord.AllowedMentions.none()


async def send_many(
    interaction: discord.Interaction,
    text: str,
    count: int = REPEAT_COUNT,
    mentions: discord.AllowedMentions = NO_MENTIONS,
    first_text: str | None = None,
    first_mentions: discord.AllowedMentions | None = None,
) -> tuple[int, bool]:
    sent = 0
    use_followup = False
    followups_used = 0

    for i in range(count):
        content = first_text if (i == 0 and first_text) else text
        allowed = first_mentions if (i == 0 and first_mentions) else mentions

        if not use_followup:
            try:
                await interaction.channel.send(content, allowed_mentions=allowed)
                sent += 1
                continue
            except (AttributeError, discord.Forbidden, discord.HTTPException):
                use_followup = True

        if followups_used >= REPEAT_COUNT:
            return sent, True

        try:
            await interaction.followup.send(content, allowed_mentions=allowed)
        except discord.HTTPException:
            return sent, True

        followups_used += 1
        sent += 1

    return sent, False


async def report_if_capped(
    interaction: discord.Interaction, sent: int, requested: int, capped: bool
):
    if not capped:
        return
    try:
        await interaction.edit_original_response(
            content=f"Sent {sent} of {requested}. Discord's limit stopped the rest."
        )
    except discord.HTTPException:
        pass


class ResendView(discord.ui.View):
    def __init__(
        self,
        message: str,
        owner_id: int,
        mentions: discord.AllowedMentions,
        first_text: str | None = None,
        first_mentions: discord.AllowedMentions | None = None,
    ):
        super().__init__(timeout=120)
        self.message = message
        self.owner_id = owner_id
        self.mentions = mentions
        self.first_text = first_text
        self.first_mentions = first_mentions

    @discord.ui.button(
        label="Spam",
        style=discord.ButtonStyle.danger,
    )
    async def resend(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        if interaction.user.id != self.owner_id:
            try:
                await interaction.response.send_message(
                    "Only the person who ran this command can use this button.",
                    ephemeral=True
                )
            except discord.NotFound:
                pass
            return

        try:
            await interaction.response.defer()
        except discord.NotFound:
            return

        sent, capped = await send_many(
            interaction, 
            self.message, 
            REPEAT_COUNT, 
            mentions=self.mentions,
            first_text=self.first_text,
            first_mentions=self.first_mentions
        )
        await report_if_capped(interaction, sent, REPEAT_COUNT, capped)


@tree.command(
    name="send",
    description="Send a message"
)
@app_commands.describe(
    text="The message you want to send",
    user="Optional: a user to mention in each message",
    everyone="Optional: add an @everyone ping to all messages"
)
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(
    guilds=True,
    dms=True,
    private_channels=True
)
async def send(
    interaction: discord.Interaction,
    text: str,
    user: discord.User | None = None,
    everyone: bool = False,
):
    base_content = f"{user.mention} {text}" if user else text

    if everyone:
        content = f"@everyone {base_content}"
        mentions = discord.AllowedMentions(
            everyone=True, users=[user] if user else False, roles=False
        )
    else:
        content = base_content
        mentions = (
            discord.AllowedMentions(everyone=False, users=[user], roles=False)
            if user
            else NO_MENTIONS
        )

    if len(content) > 2000:
        try:
            await interaction.response.send_message(
                "Your message must be 2000 characters or fewer (mentions count).",
                ephemeral=True
            )
        except discord.NotFound:
            pass
        return

    view = ResendView(
        message=content,
        owner_id=interaction.user.id,
        mentions=mentions,
        first_text=content,
        first_mentions=mentions,
    )

    try:
        await interaction.response.send_message(
            f"Sending {REPEAT_COUNT} messages... Press the button to send them again.",
            view=view,
            ephemeral=True
        )
    except discord.NotFound:
        return

    sent, capped = await send_many(
        interaction,
        content,
        REPEAT_COUNT,
        mentions=mentions,
        first_text=content,
        first_mentions=mentions,
    )
    await report_if_capped(interaction, sent, REPEAT_COUNT, capped)


@tree.command(
    name="ping",
    description="Check the bot's latency."
)
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(
    guilds=True,
    dms=True,
    private_channels=True
)
async def ping(interaction: discord.Interaction):
    try:
        await interaction.response.send_message(
            f"Pong! `{round(bot.latency * 1000)} ms`"
        )
    except discord.NotFound:
        pass


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

    try:
        synced = await tree.sync()
        print(f"Synced {len(synced)} global commands.")
    except discord.HTTPException as error:
        print(f"Command sync failed: {error}")


bot.run(TOKEN)