# Privacy Policy

**Effective Date:** October 12, 2026
**Last Updated:** October 16, 2026

## 1. Information Collection
This Discord application collects and processes only the data necessary for core operational functionality and access enforcement:
* **Discord User IDs:** Used to verify authorization against configured access lists (`ALLOWED_USER_IDS`).
* **Interaction Metadata:** Temporal processing of interaction payloads, parameters, and channel context required to execute invoked commands (`/send`, `/ping`).
* **"Spam" Button State:** When `/send` is used, the message text, the requester's Discord User ID, and any mentioned user's ID are saved locally (in `spam_store.json`, alongside the bot's code) so the "Spam" resend button keeps working even if the bot restarts. Entries are capped at the 500 most recent batches; older entries are dropped automatically.
* **Optional Audit Log:** If the bot administrator configures `LOG_USER_ID`, a one-line summary (requester's username, server name, channel name, a preview of the message text, and how many copies were sent) is sent as a direct message to that single Discord user each time `/send` or the "Spam" button is used. This is disabled by default and only active if the administrator opts in.

## 2. Data Usage
Collected identifiers and execution state variables are used strictly to:
* Enforce access control restrictions.
* Process slash commands and manage UI component states (`discord.ui.View`), including replaying a prior `/send` batch when the "Spam" button is pressed.
* Maintain system availability and operational health.

## 3. Data Storage and Retention
* **Limited Persistent Storage:** The application does not maintain a database, but it does store the "Spam" button state described above (message text, requester ID, mentioned user ID) in a local file for as long as needed to support the resend button, up to a maximum of 500 recent batches.
* **In-Memory Execution:** All other interaction data exists in application runtime memory only for the duration required to complete execution or until timeout intervals expire.

## 4. Third-Party Sharing
Data is not sold, rented, shared, or transferred to third parties, except as required for standard transmission across the official Discord API platform.

## 5. Contact
For privacy-related inquiries regarding this application instance, contact the bot administrator directly via Discord.

---
