# Copilot Commit Message Guidelines

For **all commits**, follow this structure:

- Start the commit message with **two emojis**.
  - The **first emoji** represents the *category* of the change (e.g., dashboard, automation).
  - The **second emoji** represents the *type* of change (e.g., bugfix, refactor).
- Add a **single space**, then write a concise, imperative sentence (max 72 characters, no period).
- Use the [gitmoji.dev](https://gitmoji.dev/) list for change-type emojis (2nd emoji).
- Do **not** guess the category. If you're unsure, **omit the category emoji** and use only the change-type emoji.

---

## Category Emoji Table (1st emoji)

| Category             | Emoji |
| -------------------- | :---: |
| Dashboard (Lovelace) | 🖼️    |
| Automations          | 🤖    |
| Scripts              | 🎬    |
| Template Sensors     | 🧮    |
| YAML Cleanup         | 🧹    |
| New Integration      | 🧩    |
| Git/Docs/Meta        | 📚    |
| Secrets/Env/Keys     | 🔐    |
| UI Theme             | 🎨    |
| Add-on Updates       | ⬆️    |
| Logging / Debug      | 🪵    |
| Firmware             | 📦    |

> ⚠️ Do **not** use 🖼️ unless the file is in the `lovelace/` folder and starts with `view_`.

---

## Change-Type Emojis (2nd emoji)

Use gitmoji for this:
https://gitmoji.dev/

Some common examples:
| Type        | Emoji | Description                 |
|-------------|:-----:|-----------------------------|
| New         | ➕    | Adding a new feature        |
| Fix         | 🐛    | Bugfix                      |
| Refactor    | ♻️    | Code improvement            |
| Remove      | ➖    | Removing code or files      |
| Feature     | ✨    | Significant new capability  |
| Cleanup     | 🔥    | Removing unused code/config |
| Docs        | 📝    | Documentation               |

---

## Examples

These examples are here to **teach Copilot** the expected format:

```text
🎨➕ Refactor device tracker card layout and add missing entities
🖼️➕ Add person badges and improve sensor activity view on security dashboard
🧮🐛 Fix crash in vacuum power estimate sensors due to missing battery level
🤖♻️ Restructure morning routine automation for readability
📚➖ Remove deprecated gitignore rules
