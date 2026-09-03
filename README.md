# 📸 Discord "Hall of Shame" Bot

A fun Discord bot for friend groups that turns embarrassing moments into official records. When a message receives **3 Camera (`📸`) reactions**, the bot captures it, generates an authentic Discord dark-mode styled screenshot card with a red **"CAUGHT IN 4K"** stamp, and posts it directly to `#hall-of-shame`.

---

## ✨ Features

- 📸 **Automated Reaction Monitor:** Listens for 3 `📸` reactions on any message.
- 🎨 **Custom Screenshot Card Generator:** Uses Pillow to dynamically generate a dark-mode screenshot card (author avatar, username, timestamp, wrapped text, attachments, and angled red rubber stamp).
- 🔒 **SQLite Deduplication:** Guarantees that a message is never shamed more than once.
- 🏆 **Leaderboard:** Slash command `/shame_stats` displays who in the server has been caught the most.
- 🛠️ **Diagnostics:** Slash command `/check_shame_setup` verifies permissions and confirms the `#hall-of-shame` channel is ready.
- ☁️ **Discloud Ready:** Pre-configured `discloud.config` optimized for Discloud's free 100MB RAM tier.

---

## 🚀 Setup & Local Testing

### 1. Install Dependencies
Open PowerShell or your terminal in this directory and install `discord.py` and `Pillow`:
```bash
pip install discord.py Pillow
```

### 2. Configure Your Bot Token
1. Go to the [Discord Developer Portal](https://discord.com/developers/applications).
2. Open your Application -> **Bot** tab:
   - Click **Reset Token** and copy the token.
   - Under **Privileged Gateway Intents**, enable:
     - ✅ **Message Content Intent**
3. Open the `.env` file in this folder and paste your token:
   ```ini
   DISCORD_TOKEN=your_token_here
   SHAME_CHANNEL_NAME=hall-of-shame
   TRIGGER_EMOJI=📸
   REQUIRED_REACTIONS=3
   ```

### 3. Invite the Bot to Your Server
Under **OAuth2 -> URL Generator**:
- **Scopes:** `bot`, `applications.commands`
- **Bot Permissions:**
  - Send Messages
  - Embed Links
  - Attach Files
  - Read Message History
  - Add Reactions
- Open the generated URL to invite it to your server!

### 4. Run Locally
```bash
python main.py
```
Make sure you have a channel named `#hall-of-shame` in your server. Type a message in any other channel and react with 3 `📸` emojis!

---

## ☁️ Deploying to Discloud (Free 24/7 Hosting)

Discloud lets you host Discord bots for free without keeping your computer on.

### Method A: Web Dashboard (Easiest)
1. Zip the following files together into a single `.zip` file:
   - `main.py`
   - `card_generator.py`
   - `requirements.txt`
   - `discloud.config`
   - `.env`
2. Go to [discloud.app](https://discloud.app) and sign in with Discord.
3. Click **Add App** (or **Upload**), select your `.zip` file, and upload!

### Method B: Via Discloud Discord Bot
1. Join the [Discloud Discord Server](https://discord.gg/discloud).
2. In any bot command channel, run `.login` to receive your API token.
3. Send `.upload` with your `.zip` attached!

---

## 📜 Slash Commands

- `/shame_stats` — Displays the Hall of Shame leaderboard showing the top 10 most convicted members.
- `/check_shame_setup` — Tests if the `#hall-of-shame` channel exists and checks if the bot has all required permissions.
