# discord-spam-bot

A private Discord bot for a small allow-listed group of friends. `/send` reposts a
message several times in a channel (optionally pinging a user or `@everyone`), with
a "Spam" button to fire the same batch again. Anyone not on the allow-list is
blocked before any command runs.

## How it works

- `bot.py` — entrypoint. Loads config, builds the Discord client and the
  allow-list-gated command tree, starts the health-check web server, and runs the bot.
- `commands.py` — the `/send` and `/ping` slash commands, and the persistent
  "Spam" resend button (including the small on-disk store that lets the button
  survive a restart — see [Data stored locally](#data-stored-locally)).
- `health.py` — a tiny HTTP server with a `/health` endpoint, used by hosts
  like Render to confirm the process is alive.
- `PRIVACY.md` / `TERMS.md` — what the bot collects and the rules for using it.

## Setup

1. **Create a Discord application and bot** at the
   [Discord Developer Portal](https://discord.com/developers/applications),
   and copy its token.
2. **Clone this repo and install dependencies:**

   ```bash
   git clone <this-repo-url>
   cd discord-spam-bot
   python -m venv venv
   source venv/bin/activate  # on Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configure environment variables.** Copy `.env.example` to `.env` and fill it in:

   ```bash
   cp .env.example .env
   ```

   | Variable            | Required | Description                                                                 |
   | ------------------- | -------- | ---------------------------------------------------------------------------- |
   | `BOT_TOKEN`          | yes      | Your bot's token from the Developer Portal.                                 |
   | `ALLOWED_USER_IDS`   | yes      | Comma-separated Discord user IDs allowed to run commands, e.g. `111,222`.    |
   | `PORT`               | no       | Port for the health-check server. Defaults to `10000` (Render's default).   |

   To get a Discord user ID: enable Developer Mode in Discord (Settings →
   Advanced), then right-click a user and choose "Copy User ID".

4. **Invite the bot to a server (or install it to your own account)** using an
   OAuth2 URL generated in the Developer Portal, with the `bot` and
   `applications.commands` scopes.

## Running locally

```bash
python bot.py
```

On first run, the bot syncs its two slash commands (`/send`, `/ping`) globally,
which can take up to an hour to show up everywhere the first time. After that
it only re-syncs if you restart the process (syncing doesn't repeat on every
reconnect).

## Deploying (e.g. Render)

This bot expects to run as a persistent web service, not a one-off script:
`health.py` opens an HTTP port and responds to `GET /` and `GET /health`,
which is what lets a host like Render treat it as a live service and restart
it if the process dies. Point Render's health check at `/health` and set
`BOT_TOKEN` / `ALLOWED_USER_IDS` as environment variables in the dashboard
rather than committing `.env`.

## Data stored locally

Everything is in-memory and discarded on restart **except** `spam_store.json`,
which is created automatically next to `bot.py`. It records the text, requester,
and mention target of each `/send` batch (capped at the 500 most recent) so the
"Spam" button keeps working even after the bot restarts. It's listed in
`.gitignore` and should never be committed. See `PRIVACY.md` for the full
disclosure.

## Commands

- **`/send text [user] [everyone]`** — sends `text` 5 times in the current
  channel. `user` optionally mentions someone in every copy; `everyone` adds
  an `@everyone` ping (ignored in DMs, where it has no effect). Replies with a
  "Spam" button that resends the same batch.
- **`/ping`** — reports the bot's current latency.

Both commands are restricted to the Discord user IDs listed in
`ALLOWED_USER_IDS`; everyone else gets "Sorry, this bot is private."
