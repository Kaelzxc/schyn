import discord
from discord.ext import commands, tasks
import logging
from dotenv import load_dotenv
import os
import random
import aiohttp
import json
from flask import Flask
import threading
import datetime
import pytz
from datetime import datetime
import asyncio

# ========== FLASK APP FOR RENDER HOSTING ==========
app = Flask('')

@app.route('/')
def home():
    return "Bot is running!"

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

# Start Flask app in a separate thread
flask_thread = threading.Thread(target=run_flask)
flask_thread.start()

# Create a global lock for the tiktoklive command
tiktoklive_lock = asyncio.Lock()

PH_TZ = pytz.timezone("Asia/Manila")

load_dotenv()
token = os.getenv('DISCORD_TOKEN')
GIPHY_API_KEY = os.getenv('GIPHY_API_KEY')

handler = logging.FileHandler(filename='bot.log', encoding='utf-8', mode='w')
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

valorant_role = "Valorant"
tft_role = "Teamfight Tactics"
lol_role = "League of Legends"

live_match_messages = {}

# ===== STATUS FILES =====
SCHYN_STATUS_FILE = "SCHYN_status.json"

# ===== STATUS LOADERS =====
def load_status(file):
    try:
        with open(file, "r") as f:
            return json.load(f).get("status", None)
    except (FileNotFoundError, json.JSONDecodeError):
        return None

def save_status(file, status):
    with open(file, "w") as f:
        json.dump({"status": status}, f)

# Initial status values
schyn_status = load_status(SCHYN_STATUS_FILE)

# ===== Helpers =====
def normalize_url(u: str) -> str:
    if not u:
        return None
    if u.startswith("//"):
        return "https:" + u
    if u.startswith("/"):
        return "https://www.vlr.gg" + u
    return u

async def fetch_giphy_gif(search_term):
    async with aiohttp.ClientSession() as session:
        url = "https://api.giphy.com/v1/gifs/search"
        params = {
            "api_key": GIPHY_API_KEY,
            "q": search_term,
            "limit": 25,
            "offset": 0,
            "rating": "pg-13",
            "lang": "en"
        }
        async with session.get(url, params=params) as resp:
            if resp.status == 200:
                data = await resp.json()
                gifs = data.get("data")
                if gifs:
                    chosen = random.choice(gifs)
                    return chosen["images"]["original"]["url"]
    return None

@bot.event
async def on_ready():
    print(f"Bot has logged in as {bot.user}")
    await bot.change_presence(activity=discord.Game(name="Playing with code!"))
    remind_follow_tiktok.start()  # Start the reminder task

@tasks.loop(minutes=90)
async def remind_follow_tiktok():
    # Get the target channel where you want the reminder to be sent
    target_channel_id = 1322632194698641508  # Replace with your target channel ID
    channel = bot.get_channel(target_channel_id)

    if channel:
        # Create the embed for the TikTok reminder
        embed = discord.Embed(
            description="**Don't forget to follow @schyn on TikTok!** 🎥\n\n"
                        "Stay updated with the latest content, streams, and fun!\n\n",
            color=discord.Color.from_rgb(255, 105, 180),  # Light pinkish color
        )

        # Add the GIF from the provided URL
        embed.set_image(url="https://i.pinimg.com/originals/58/61/b7/5861b7f7c987775889e748d3ec1939cd.gif")

        # Create the follow button
        follow_button = discord.ui.Button(label="Follow on TikTok", style=discord.ButtonStyle.link, url="https://www.tiktok.com/@.schyn")

        # Create a View to hold the button
        view = discord.ui.View(timeout=None)  # `timeout=None` to make the button last indefinitely
        view.add_item(follow_button)

        # Send the embed and the button
        await channel.send(embed=embed, view=view)

@bot.event
async def on_member_join(member):
    await member.send(f"Welcome to the server {member.name}")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    content = message.content.lower()

    # Auto-replies for greetings — only trigger once, no repeated calls to process commands
    if "goodmorning" in content or "good morning" in content:
        await message.channel.send(f"Good morning, {message.author.mention}! ☀️")
    elif "goodnight" in content or "good night" in content:
        await message.channel.send(f"Good night, {message.author.mention}! 🌙")
    elif "hello" in content or "halo" in content:
        await message.channel.send(f"Hello there, {message.author.mention}! 👋")
    elif "hi" in content or "hai" in content:
        await message.channel.send(f"Hi there, {message.author.mention}! 👋")
    elif "good afternoon" in content or "goodafternoon" in content:
        await message.channel.send(f"Good afternoon, {message.author.mention}! 👋")

    # Banned words filtering — only once, prevent multiple `await bot.process_commands(message)`
    banned_words = ["nigga", "niggers", "naega", "kantutan", "ninja", "ninjas"]
    for word in banned_words:
        if word in content:
            await message.delete()
            await message.channel.send(f"{message.author.mention} - wag mo banggitin yan!")
            break  # Stop after the first match

    await bot.process_commands(message)

# ===== STATUS COMMANDS =====
@bot.command()
async def schyn(ctx, *, status: str = None):
    global schyn_status
    ALLOWED_USER_ID = 1168024067362787408  # Lil's ID

    if status is None:
        if schyn_status:
            await ctx.send(f"📢 Schyn is currently **{schyn_status}**!")
        else:
            await ctx.send("Schyn status has not been set yet.")
    else:
        if ctx.author.id != ALLOWED_USER_ID:
            await ctx.send("❌ You are not allowed to change Schyn's status.")
            return

        schyn_status = status
        save_status(SCHYN_STATUS_FILE, schyn_status)
        await ctx.send(f"✅ Schyn's status has been set to **{status}**!")

        # Dynamically change the bot's status based on the new status
        await bot.change_presence(activity=discord.Game(name=status))

@bot.command()
async def tiktok(ctx):
    await ctx.send(f"https://www.tiktok.com/@.schyn {ctx.author.mention}!")

@bot.command()
async def rank(ctx):
    await ctx.send(f"Radiant {ctx.author.mention}!")

@bot.command()
async def valorant(ctx):
    role = discord.utils.get(ctx.guild.roles, name=valorant_role)
    if role:
        await ctx.author.add_roles(role)
        await ctx.send(f"{ctx.author.mention} is now assigned to {valorant_role}!")
    else:
        await ctx.send("Role doesn't exist")

@bot.command()
async def tft(ctx):
    role = discord.utils.get(ctx.guild.roles, name=tft_role)
    if role:
        await ctx.author.add_roles(role)
        await ctx.send(f"{ctx.author.mention} is now assigned to {tft_role}!")
    else:
        await ctx.send("Role doesn't exist")

@bot.command()
async def lol(ctx):
    role = discord.utils.get(ctx.guild.roles, name=lol_role)
    if role:
        await ctx.author.add_roles(role)
        await ctx.send(f"{ctx.author.mention} is now assigned to {lol_role}!")
    else:
        await ctx.send("Role doesn't exist")

@bot.command()
async def tiktoklive(ctx):
    async with tiktoklive_lock:  # Lock to prevent concurrent execution
        target_channel_id = 1446841462581886997
        channel = bot.get_channel(target_channel_id)

        if channel is not None:
            embed = discord.Embed(
                title="🔴 Schyn is LIVE on TikTok!",
                description=(
                    "🎥 **.schyn** just went live on TikTok!\n\n"
                    "✨ Come chill, vibe, and be part of the stream — it’s gonna be a fun time you won’t want to miss.\n\n"
                    "👉 **Tap below to join the live now:**\n"
                    "[📲 Watch the Stream](https://www.tiktok.com/@.schyn/live)"
                ),
                color=discord.Color.from_rgb(255, 0, 102),
                timestamp=ctx.message.created_at
            )

            embed.set_thumbnail(url="https://i.pinimg.com/1200x/e7/9f/ca/e79fcaefef85b2d634dd7eab1318664b.jpg")
            embed.set_image(url="https://i.pinimg.com/originals/b7/f8/1d/b7f81df43aa6b9229dad05c73d3b345a.gif")

            embed.set_footer(
                text="🔗 Powered by Schyn bot • Brought to you by aiz",
                icon_url=ctx.guild.icon.url if ctx.guild.icon else discord.Embed.Empty
            )

            await channel.send(content="@everyone", embed=embed)
            await ctx.send("✅ Live alert sent!")
        else:
            await ctx.send("❌ Could not find the live announcement channel.")



@bot.command()
async def kiss(ctx, member: discord.Member = None):
    if not member:
        await ctx.send("You need to mention someone to kiss! 😳")
        return
    if member == ctx.author:
        await ctx.send("Awww, self-love is important! 😘")
        return
    gif = await fetch_giphy_gif("anime kiss")
    if not gif:
        await ctx.send("Couldn't fetch a kiss GIF right now, try again later! 😞")
        return

    ph_time = datetime.now(PH_TZ)

    embed = discord.Embed(
        description=f"**{ctx.author.mention}** kisses **{member.mention}**!! 💋",
        color=discord.Color.pink(),
        timestamp=ph_time
    )

    embed.set_author(
        name=f"{ctx.author.name} gives a sweet kiss!",
        icon_url=ctx.author.avatar.url
    )

    embed.set_thumbnail(url="https://media.giphy.com/media/1oPGRlhvEx9bGdfoDe/giphy.gif")
    embed.set_image(url=gif)

    await ctx.send(embed=embed)



@bot.command()
async def slap(ctx, member: discord.Member = None):
    if not member:
        await ctx.send("Mention someone to slap! 😡")
        return
    if member == ctx.author:
        await ctx.send("Why are you slapping yourself? 😢")
        return
    gif = await fetch_giphy_gif("anime slap")
    if not gif:
        await ctx.send("Couldn't fetch a slap GIF right now, try again later! 😞")
        return

    ph_time = datetime.now(PH_TZ)

    embed = discord.Embed(
        description=f"**{ctx.author.mention}** slaps **{member.mention}**!! 👋",
        color=discord.Color.red(),
        timestamp=ph_time
    )

    embed.set_author(
        name=f"{ctx.author.name} delivers a harsh slap!",
        icon_url=ctx.author.avatar.url
    )

    embed.set_thumbnail(url="https://media.giphy.com/media/MfuD0fLvL8Xag/giphy.gif")
    embed.set_image(url=gif)

    await ctx.send(embed=embed)



@bot.command()
async def hug(ctx, member: discord.Member = None):
    if not member:
        await ctx.send("You gotta mention someone to hug! 🤗")
        return
    if member == ctx.author:
        await ctx.send("Sending a virtual hug to yourself 🤗💖")
        return
    gif = await fetch_giphy_gif("anime hug")
    if not gif:
        await ctx.send("Couldn't fetch a hug GIF right now, try again later! 😞")
        return

    ph_time = datetime.now(PH_TZ)

    embed = discord.Embed(
        description=f"**{ctx.author.mention}** gives **{member.mention}** a warm hug!! 🤗",
        color=discord.Color.blue(),
        timestamp=ph_time
    )

    embed.set_author(
        name=f"{ctx.author.name} embraces with a loving hug!",
        icon_url=ctx.author.avatar.url
    )

    embed.set_thumbnail(url="https://media.giphy.com/media/1xV0VmeOa35JXrdWqA/giphy.gif")
    embed.set_image(url=gif)

    await ctx.send(embed=embed)



@bot.command()
async def punch(ctx, member: discord.Member = None):
    """Playful, non-graphic punch (like slap)."""
    if not member:
        await ctx.send("Mention someone to punch! (playfully) 🥊")
        return
    if member == ctx.author:
        await ctx.send("Why are you punching yourself? Be kind to yourself! 🤕")
        return
    gif = await fetch_giphy_gif("anime punch")
    if not gif:
        await ctx.send("Couldn't fetch a punch GIF right now, try again later! 😞")
        return

    ph_time = datetime.now(PH_TZ)

    embed = discord.Embed(
        description=f"**{ctx.author.mention}** playfully punches **{member.mention}**!! 🥊",
        color=discord.Color(0xE53935),
        timestamp=ph_time
    )

    embed.set_author(
        name=f"{ctx.author.name} delivers a punch!",
        icon_url=ctx.author.avatar.url
    )

    embed.set_thumbnail(url="https://media.giphy.com/media/v5I6d6PzV5mxa/giphy.gif")
    embed.set_image(url=gif)

    await ctx.send(embed=embed)



@bot.command()
async def kill(ctx, member: discord.Member = None):
    if not member:
        await ctx.send("Who do you want to kill? Mention someone! 👀")
        return

    if member == ctx.author:
        await ctx.send("Killing yourself? A+ self-harm. 🤗")
        return

    gif = await fetch_giphy_gif("kill anime")
    if not gif:
        await ctx.send("Couldn't fetch a kill GIF right now, try again later! 😞")
        return

    # Get Philippine Time
    ph_time = datetime.now(PH_TZ)

    embed = discord.Embed(
        description=f"**{ctx.author.mention}** gives **{member.mention}** a finishing blow!! 👆",
        color=discord.Color.from_rgb(255, 0, 0),
        timestamp=ph_time
    )

    embed.set_author(
        name=f"{ctx.author.name} delivers a final blow!",
        icon_url=ctx.author.avatar.url
    )

    embed.set_thumbnail(url="https://media.giphy.com/media/yPOXYBdFlIT5vZEC0v/giphy.gif")
    embed.set_image(url=gif)

    await ctx.send(embed=embed)


@bot.command()
async def vanish(ctx, member: discord.Member = None):
    """Playful 'vanish' — harmless alternative to destructive commands."""
    target_text = f" at {member.mention}" if member and member != ctx.author else ""
    if member == ctx.author:
        await ctx.send("You try to vanish... but you're still here. ✨")
        return
    gif = await fetch_giphy_gif("poof disappear anime")
    if not gif:
        await ctx.send(f"{ctx.author.mention} dramatically vanishes{target_text}... (but comes back soon).")
        return

    ph_time = datetime.now(PH_TZ)

    embed = discord.Embed(
        description=f"✨ **{ctx.author.mention}** dramatically vanishes{target_text}... (it's just a prank!)",
        color=discord.Color.purple(),
        timestamp=ph_time
    )

    embed.set_author(
        name=f"{ctx.author.name} makes a magical exit!",
        icon_url=ctx.author.avatar.url
    )

    embed.set_thumbnail(url="https://media.giphy.com/media/MnGl9iJ6k7f5s/giphy.gif")
    embed.set_image(url=gif)

    await ctx.send(embed=embed)

@bot.command()
async def aiz(ctx):
    await ctx.reply(f"soft spoken clove main yan hehe sarap {ctx.author.mention}!")

@bot.command()
async def birthday(ctx):
    target_channel_id = 1371553825118355550  # Replace with your target channel ID where the birthday greeting should go
    target_channel = bot.get_channel(target_channel_id)

    if target_channel is not None:
        embed = discord.Embed(
            title="🎉 **Happy Birthday Schyn!** 🎉",
            color=discord.Color.from_rgb(255, 87, 34),  # Bright, celebratory orange color
            timestamp=datetime.datetime.utcnow()
        )

        # Add a festive animated gif (replace with your own URL if preferred)
        embed.set_image(url="https://i.pinimg.com/736x/cb/ef/ec/cbefece3d03bd34efe2790deab764a19.jpg")

        embed.set_footer(
            text="🎂 Powered by Lil Bot • Let's celebrate Schyn! 🎉",
            icon_url=ctx.guild.icon.url if ctx.guild.icon else discord.Embed.Empty
        )

        # Send the message with @everyone ping
        await target_channel.send(content="@everyone", embed=embed)
        await ctx.send("✅ Birthday message has been sent to the designated channel!")

    else:
        await ctx.send("❌ Could not find the target birthday channel.")



bot.run(token, log_handler=handler, log_level=logging.INFO)




