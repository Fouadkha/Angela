import discord
import datetime
from datetime import date
from zoneinfo import ZoneInfo
from discord.ext import tasks
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pandas as pd

time = datetime.time(hour=8, minute=30)
ids = pd.read_csv("ids.csv")
author_to_emoji = dict(zip(ids['author'], ids['emoji']))
schedule = pd.read_csv("schedule.csv")

scheduler = AsyncIOScheduler()

class Client(discord.Client):
    async def on_ready(self):
        print(f'Logged on as {self.user}!')
        for _, row in schedule.iterrows():
            day = row["day"]
            time_parts = row["time"].split(":")
            hour, minute = int(time_parts[0]), int(time_parts[1])
            channel_id = int(row["channel"])
            message = row["message"]
            scheduler.add_job(send_message,CronTrigger(day_of_week=day, hour=hour, minute=minute),args=[channel_id, message])
        scheduler.start()
    
    async def on_message(self, message):
        if message.author.id in ids["author"].values:
            reaction = client.get_emoji(author_to_emoji.get(message.author.id))
            await message.add_reaction(reaction)

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
