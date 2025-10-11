import discord
from discord.ext import tasks
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pandas as pd
import pytz
import random

tz = pytz.timezone("Europe/Berlin")
rules = {}
OWNERS = None
channels = {}

def load_channels(filename="channels.csv"):
    """Load numbered channels into dictionary: nr → channel_id"""
    global channels
    df = pd.read_csv(filename, dtype=str)
    channels = {int(row["nr"]): int(row["id"]) for _, row in df.iterrows()}
    print(f"✅ Loaded {len(channels)} channels from {filename}")

def load_rules(filename="ids.csv"):
    global rules, OWNERS
    rules = {}
    
    df = pd.read_csv(filename, dtype=str).fillna("")  # read as strings, empty -> ""
    OWNERS = {int(a) for a in df["author"].head(2) if a.strip()}
    for _, row in df.iterrows():
        author_id = int(row["author"])
        emoji_id = int(row["emoji"])
        channel = row["channel"].strip()

        if author_id not in rules:
            rules[author_id] = {"default": None, "channels": {}}

        if channel:  # channel-specific
            rules[author_id]["channels"][int(channel)] = emoji_id
        else:  # default
            rules[author_id]["default"] = emoji_id

schedule = pd.read_csv("schedule.csv")

scheduler = AsyncIOScheduler()

class Client(discord.Client):
    async def on_ready(self):
        load_rules()
        load_channels()
        print(f'Logged on as {self.user}!')
        for _, row in schedule.iterrows():
            day = row["day"]
            time_parts = row["time"].split(":")
            hour, minute = int(time_parts[0]), int(time_parts[1])
            channel_id = int(row["channel"])
            message = row["message"]
            scheduler.add_job(send_message,CronTrigger(day_of_week=day, hour=hour, minute=minute, timezone=tz),args=[channel_id, message])
        scheduler.start()
    
    async def on_message(self, message):
            # --- Handle private messages ---
        if isinstance(message.channel, discord.DMChannel) and message.author.id in OWNERS:
            if message.content.startswith("!send "):
                parts = message.content.split(" ", 2)
                if len(parts) < 3:
                    await message.channel.send("⚠️ Usage: `!send <channel_id> <message>`")
                    return
                nr = int(parts[1])
                text = parts[2]
                if nr in channels:
                    await send_message(channels[nr], text)
                else:
                    await send_message(nr, text)
            return
        # --- Handle reactions in servers ---
        author_id = message.author.id
        channel_id = message.channel.id
        if author_id in rules:
        # pick channel-specific or default
            if channel_id in rules[author_id]["channels"]:
                emoji_id = rules[author_id]["channels"][channel_id]
            else:
                emoji_id = rules[author_id]["default"]

            if emoji_id:
                emoji = client.get_emoji(emoji_id)  # fetch emoji object
            await message.add_reaction(emoji)


async def send_message(channel_id, message):
    channel = client.get_channel(channel_id)
    if channel:
        await channel.send(message)


file = open("key.txt", "r")
key = file.read()
file.close()
intents = discord.Intents.default()
intents.message_content = True
client = Client(intents=intents)

client.run(key)
