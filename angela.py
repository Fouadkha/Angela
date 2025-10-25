import discord
from discord.ext import tasks
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pandas as pd
import pytz
import random
import aiohttp

tz = pytz.timezone("Europe/Berlin")
key = None
reactions = {}
OWNERS = None
channels = {}
scheduler = None

def read_key():
    global key
    file = open("key.txt", "r")
    key = file.read()
    file.close()

def load_channels(filename="channels.csv"):
    global channels
    df = pd.read_csv(filename, dtype=str, comment='#')
    channels = {int(row["nr"]): int(row["id"]) for _, row in df.iterrows()}
    print(f"✅ Loaded {len(channels)} channels from {filename}")

def load_reactions(filename="reactions.csv"):
    global reactions, OWNERS
    reactions = {}
    
    df = pd.read_csv(filename, dtype=str).fillna("")  # read as strings, empty -> ""
    OWNERS = {int(a) for a in df["author"].head(2) if a.strip()}
    for _, row in df.iterrows():
        author_id = int(row["author"])
        emoji_id = int(row["emoji"])
        channel = row["channel"].strip()

        if author_id not in reactions:
            reactions[author_id] = {"default": None, "channels": {}}

        if channel:  # channel-specific
            reactions[author_id]["channels"][int(channel)] = emoji_id
        else:  # default
            reactions[author_id]["default"] = emoji_id
    print(f"✅ Loaded {len(reactions)} reactions from {filename}")


def load_schedule(filename="schedule.csv"):
    global scheduler
    scheduler = AsyncIOScheduler()
    schedule = pd.read_csv(filename, comment='#')
    for _, row in schedule.iterrows():
            day = row["day"]
            time_parts = row["time"].split(":")
            hour, minute = int(time_parts[0]), int(time_parts[1])
            channel_id = int(row["channel"])
            message = row["message"]
            scheduler.add_job(send_message,CronTrigger(day_of_week=day, hour=hour, minute=minute, timezone=tz),args=[channel_id, message])
    print(f"✅ Loaded {len(schedule)} messages from {filename}")


class Client(discord.Client):
    async def on_ready(self):
        load_reactions()
        load_channels()
        load_schedule()
        print(f'Logged on as {self.user}!')
        scheduler.start()
    
    async def reload(self):
        global scheduler
        scheduler.remove_all_jobs()
        scheduler.shutdown(wait=False)
        reactions.clear()
        OWNERS.clear()
        channels.clear()
        load_reactions()
        load_channels()
        load_schedule()
        scheduler.start()

    async def on_message(self, message):
        # --- Handle private messages ---
        if isinstance(message.channel, discord.DMChannel) and message.author.id in OWNERS:
            if message.content.startswith("!send "):
                parts = message.content.split(" ", 2)
                if len(parts) == 3:
                    nr = int(parts[1])
                    text = parts[2]
                    if nr in channels:
                        await send_message(channels[nr], text)
                    else:
                        await send_message(nr, text)
            elif message.content.startswith("!reload"):
                await self.reload()
                
        # --- Handle reactions in servers ---
        author_id = message.author.id
        channel_id = message.channel.id
        if author_id in reactions:
        # pick channel-specific or default
            if channel_id in reactions[author_id]["channels"]:
                emoji_id = reactions[author_id]["channels"][channel_id]
            else:
                emoji_id = reactions[author_id]["default"]

            if emoji_id:
                emoji = client.get_emoji(emoji_id)  # fetch emoji object
            await message.add_reaction(emoji)
        # !cat
        if message.content.strip().lower().startswith("!cat"):
            await fetch_cat_gif(message.channel)


async def fetch_cat_gif(channel: discord.abc.Messageable):
    url = "https://api.thecatapi.com/v1/images/search?mime_types=gif"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    await channel.send("⚠️ The Cat API didn’t respond properly.")
                    return

                data = await resp.json()
                gif_url = data[0].get("url") if data else None

                if gif_url:
                    await channel.send(gif_url)
                else:
                    await channel.send("😿 Couldn't find a cat gif right now.")

    except aiohttp.ClientError as e:
        await channel.send(f"⚠️ Network error while fetching cat gif: {e}")




async def send_message(channel_id, message):
    if channel := client.get_channel(channel_id):
        await channel.send(message)
    elif user := await client.fetch_user(channel_id):
        await user.send(message)



read_key()
intents = discord.Intents.default()
intents.message_content = True
client = Client(intents=intents)

client.run(key)
