# Privacy Policy

**Effective Date:** October 12, 2026

## 1. Information Collection
This Discord application collects and processes only the data necessary for core operational functionality and access enforcement:
* **Discord User IDs:** Used to verify authorization against configured access lists (`ALLOWED_USER_IDS`).
* **Interaction Metadata:** Temporal processing of interaction payloads, parameters, and channel context required to execute invoked commands (`/send`, `/ping`).

## 2. Data Usage
Collected identifiers and execution state variables are used strictly to:
* Enforce access control restrictions.
* Process slash commands and manage UI component states (`discord.ui.View`).
* Maintain system availability and operational health.

## 3. Data Storage and Retention
* **No Persistent Data Storage:** The application does not maintain a database or store message contents, user metadata, or command histories persistently.
* **In-Memory Execution:** Interaction structures exist in application runtime memory only for the duration required to complete execution or until timeout intervals expire.

## 4. Third-Party Sharing
Data is not sold, rented, shared, or transferred to third parties, except as required for standard transmission across the official Discord API platform.

## 5. Contact
For privacy-related inquiries regarding this application instance, contact the bot administrator directly via Discord.

---