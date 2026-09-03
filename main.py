import sys

# Ensure UTF-8 output encoding for Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
import os
import io
import asyncio
import sqlite3
from datetime import datetime
import discord
from discord import app_commands
from discord.ext import commands

from card_generator import generate_shame_card

# --- Load Environment Variables (.env support without extra dependencies) ---
def load_env_file(filepath=".env"):
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ.setdefault(key.strip(), val.strip().strip("\"'"))

load_env_file()

TOKEN = os.getenv("DISCORD_TOKEN")
SHAME_CHANNEL_NAME = os.getenv("SHAME_CHANNEL_NAME", "hall-of-shame").lower()
TRIGGER_EMOJI = os.getenv("TRIGGER_EMOJI", "📸")
REQUIRED_REACTIONS = int(os.getenv("REQUIRED_REACTIONS", "3"))
DB_PATH = os.getenv("DB_PATH", "shame.db")

# --- Database Setup (SQLite) ---
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS shamed_messages (
            message_id TEXT PRIMARY KEY,
            guild_id TEXT NOT NULL,
            channel_id TEXT NOT NULL,
            author_id TEXT NOT NULL,
            author_name TEXT NOT NULL,
            shamed_at TIMESTAMP NOT NULL,
            hall_post_id TEXT,
            reaction_count INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

def is_already_shamed(message_id: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM shamed_messages WHERE message_id = ?", (str(message_id),))
    row = cursor.fetchone()
    conn.close()
    return row is not None

def record_shame(message_id: str, guild_id: str, channel_id: str, author_id: str, author_name: str, hall_post_id: str, reaction_count: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO shamed_messages 
        (message_id, guild_id, channel_id, author_id, author_name, shamed_at, hall_post_id, reaction_count)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (str(message_id), str(guild_id), str(channel_id), str(author_id), author_name, datetime.utcnow(), str(hall_post_id), reaction_count))
    conn.commit()
    conn.close()

def get_leaderboard(guild_id: str, limit: int = 10):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT author_id, author_name, COUNT(*) as shame_count
        FROM shamed_messages
        WHERE guild_id = ?
        GROUP BY author_id
        ORDER BY shame_count DESC
        LIMIT ?
    """, (str(guild_id), limit))
    rows = cursor.fetchall()
    conn.close()
    return rows

# --- Bot Client Setup ---
intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
intents.guilds = True

# OPTIMIZATION: Disable massive internal caches to save RAM (Discloud friendly)
bot = commands.Bot(
    command_prefix="!", 
    intents=intents, 
    max_messages=10, 
    chunk_guilds_at_startup=False,
    member_cache_flags=discord.MemberCacheFlags.none()
)

@bot.event
async def on_ready():
    init_db()
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")
    print(f"📸 Monitoring for {TRIGGER_EMOJI} (Threshold: {REQUIRED_REACTIONS})")
    print(f"🎯 Target Hall of Shame channel: #{SHAME_CHANNEL_NAME}")
    try:
        synced = await bot.tree.sync()
        print(f"⚡ Synced {len(synced)} slash command(s)")
    except Exception as e:
        print(f"⚠️ Error syncing slash commands: {e}")


@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    # Only listen for the designated trigger emoji
    if str(payload.emoji) != TRIGGER_EMOJI:
        return

    # Don't react in DMs
    if not payload.guild_id:
        return

    guild = bot.get_guild(payload.guild_id)
    if not guild:
        return

    channel = guild.get_channel(payload.channel_id)
    if not channel or not isinstance(channel, discord.TextChannel):
        return

    # Avoid shaming messages inside the hall-of-shame channel itself to prevent loops
    if channel.name.lower() == SHAME_CHANNEL_NAME:
        return

    # Check if message is already recorded in the Hall of Shame
    if is_already_shamed(payload.message_id):
        return

    try:
        message = await channel.fetch_message(payload.message_id)
    except (discord.NotFound, discord.Forbidden):
        return

    # Don't shame bot messages
    if message.author.bot:
        return

    # Find the reaction object for TRIGGER_EMOJI to check the current count
    reaction = discord.utils.get(message.reactions, emoji=TRIGGER_EMOJI)
    if not reaction or reaction.count < REQUIRED_REACTIONS:
        return

    # Re-check DB to prevent race condition when multiple people react simultaneously
    if is_already_shamed(message.id):
        return

    # Find the designated Hall of Shame channel
    shame_channel = discord.utils.get(guild.text_channels, name=SHAME_CHANNEL_NAME)
    if not shame_channel:
        print(f"⚠️ Channel #{SHAME_CHANNEL_NAME} not found in guild '{guild.name}'!")
        return

    # Mark as shamed first so duplicate tasks don't fire
    record_shame(
        message_id=str(message.id),
        guild_id=str(guild.id),
        channel_id=str(channel.id),
        author_id=str(message.author.id),
        author_name=message.author.display_name,
        hall_post_id="pending",
        reaction_count=reaction.count
    )

    # Check if there is an image attachment
    attachment_url = None
    if message.attachments:
        for att in message.attachments:
            if att.content_type and att.content_type.startswith("image/"):
                attachment_url = att.url
                break

    # Author details
    author_name = message.author.display_name
    avatar_url = message.author.display_avatar.url if message.author.display_avatar else None
    content_text = message.clean_content or message.content or ""

    # Generate the screenshot card in a background thread to keep event loop responsive
    card_buffer = await asyncio.to_thread(
        generate_shame_card,
        author_name=author_name,
        message_text=content_text,
        timestamp=message.created_at,
        avatar_url=avatar_url,
        attachment_url=attachment_url
    )

    # Fetch witnesses who reacted
    witnesses = []
    async for u in reaction.users():
        if not u.bot:
            witnesses.append(u.mention)
    
    witness_text = ""
    if witnesses:
        witness_text = f" ({', '.join(witnesses)})"

    # Build the Hall of Shame post
    shame_file = discord.File(fp=card_buffer, filename="shame_card.png")
    
    embed = discord.Embed(
        title="🚨 CAUGHT IN 4K!",
        description=(
            f"**Culprit:** {message.author.mention}\n"
            f"**Location:** {channel.mention}\n"
            f"**Witnesses:** {reaction.count} {TRIGGER_EMOJI}{witness_text}\n\n"
            f"🔗: {message.jump_url}"
        ),
        color=discord.Color.from_rgb(255, 0, 85) # Neon Pink
    )
    embed.set_image(url="attachment://shame_card.png")
    embed.set_footer(text=f"Hall of Shame • Convicted by server vote")

    try:
        shame_post = await shame_channel.send(embed=embed, file=shame_file)
        # Update post ID in DB
        record_shame(
            message_id=str(message.id),
            guild_id=str(guild.id),
            channel_id=str(channel.id),
            author_id=str(message.author.id),
            author_name=author_name,
            hall_post_id=str(shame_post.id),
            reaction_count=reaction.count
        )
        # Acknowledge the crime on the original message
        try:
            await message.add_reaction("💀")
        except Exception:
            pass
        print(f"📸 Convicted {author_name} (Msg ID: {message.id}) to #{SHAME_CHANNEL_NAME}")
    except discord.Forbidden:
        print(f"❌ Bot does not have permissions to send messages or embed files in #{SHAME_CHANNEL_NAME}")
    except Exception as e:
        print(f"❌ Failed to post shame card: {e}")


# --- Slash Commands ---

@bot.tree.command(name="shame_stats", description="View the Hall of Shame leaderboard for this server")
async def shame_stats(interaction: discord.Interaction):
    if not interaction.guild_id:
        await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
        return

    rows = get_leaderboard(str(interaction.guild_id), limit=10)
    if not rows:
        await interaction.response.send_message("🕊️ The Hall of Shame is currently empty! Nobody has been caught yet.", ephemeral=True)
        return

    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    leaderboard_lines = []
    for i, (author_id, author_name, count) in enumerate(rows):
        medal = medals[i] if i < len(medals) else f"**#{i+1}**"
        leaderboard_lines.append(f"{medal} <@{author_id}> — **{count}** conviction{'s' if count != 1 else ''}")

    embed = discord.Embed(
        title="🏆 Hall of Shame — Most Wanted Leaderboard",
        description="\n".join(leaderboard_lines),
        color=discord.Color.from_rgb(237, 66, 69)
    )
    embed.set_footer(text=f"Total monitored threshold: {REQUIRED_REACTIONS} {TRIGGER_EMOJI} reactions")
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="check_shame_setup", description="Verify if the bot is set up properly in this server")
async def check_shame_setup(interaction: discord.Interaction):
    guild = interaction.guild
    if not guild:
        await interaction.response.send_message("Use this command in a server.", ephemeral=True)
        return

    shame_channel = discord.utils.get(guild.text_channels, name=SHAME_CHANNEL_NAME)
    status_lines = [
        f"**Trigger Emoji:** {TRIGGER_EMOJI}",
        f"**Required Reactions:** {REQUIRED_REACTIONS}",
    ]

    if shame_channel:
        perms = shame_channel.permissions_for(guild.me)
        can_send = perms.send_messages
        can_embed = perms.embed_links
        can_attach = perms.attach_files

        status_lines.append(f"✅ Found channel: {shame_channel.mention}")
        status_lines.append(f"• Send Messages: {'✅' if can_send else '❌'}")
        status_lines.append(f"• Embed Links: {'✅' if can_embed else '❌'}")
        status_lines.append(f"• Attach Files: {'✅' if can_attach else '❌'}")

        if not (can_send and can_embed and can_attach):
            status_lines.append("\n⚠️ **Action Needed:** Please give the bot `Send Messages`, `Embed Links`, and `Attach Files` in that channel.")
    else:
        status_lines.append(f"❌ **Channel missing!** Could not find a text channel named `#{SHAME_CHANNEL_NAME}`.")
        status_lines.append(f"👉 Please create a channel named `#{SHAME_CHANNEL_NAME}` or rename an existing one.")

    embed = discord.Embed(
        title="🛠️ Hall of Shame Setup Status",
        description="\n".join(status_lines),
        color=discord.Color.blue() if shame_channel else discord.Color.orange()
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


if __name__ == "__main__":
    if not TOKEN or TOKEN == "your_bot_token_here":
        print("=" * 60)
        print("⚠️  ERROR: DISCORD_TOKEN is missing or not set!")
        print("Please edit the .env file and paste your bot token.")
        print("Example:")
        print("DISCORD_TOKEN=MTA2Nz...your_actual_token_here")
        print("=" * 60)
    else:
        bot.run(TOKEN)
