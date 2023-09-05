import asyncpraw
import configparser
import json
import re
import discord
from discord import default_permissions, option

config = configparser.ConfigParser()
config.read("config.ini")

intents = discord.Intents.default()
intents.message_content = True
bot = discord.Bot(intents=intents)
with open("channels.json") as fp:
    channels = json.load(fp)

def update_channel_parameters():
    with open("channels.json", "w") as fp:
        json.dump(channels, fp)

@bot.event
async def on_ready():
    print(f"Initialized Discord")
    await monitor()

@bot.command(name="enable-scorepost", description="Enable scorepost feed on the specified channel")
@default_permissions(manage_channels=True)
@option(
    "channel",
    description="Channel to enable scorepost feed in",
    required=True
)
@option(
    "role",
    description="Optional role to ping when posting scores",
    required=False,
    default=None
)
async def enable_scorepost(ctx, channel: discord.TextChannel):
    guild_id = str(channel.guild.id)
    channel_id = str(channel.id) 
    # roflcopter
    if guild_id in channels and any(item["channel_id"] == channel_id for item in channels[guild_id]):
        await ctx.respond(f"Scorepost feed is already enabled in channel {channel.name}")
        return

    channel_item = { "channel_id": channel_id, "ping_role": "" }

    if guild_id in channels:
        channels[guild_id].append(channel_item)
    else: 
        channels[guild_id] = [channel_item]

    update_channel_parameters()
    await ctx.respond(f"Enabled scorepost feed in channel {channel.name}")

@bot.command(name="disable-scorepost", description="Disable scorepost feed on the specified channel")
@default_permissions(manage_channels=True)
@option(
    "channel",
    description="Channel to disable scorepost feed in",
    required=True
)
async def disable_scorepost(ctx, channel: discord.TextChannel):
    guild_id = str(channel.guild.id)
    channel_id = str(channel.id)
    if guild_id in channels and any(item["channel_id"] == channel_id for item in channels[guild_id]):
        channels[guild_id] = list(filter(lambda x: x["channel_id"] != channel_id, channels[guild_id]))
        update_channel_parameters()
        await ctx.respond(f"Disabled scorepost feed in channel {channel.name}")
    else:
        await ctx.respond(f"Scorepost feed is not currently enabled in channel {channel.name}")

@bot.command(name="set-ping-role", description="Set a role to be pinged when posting scores")
@default_permissions(manage_channels=True)
@option(
    "channel",
    description="Channel to modify",
    required=True
)
@option(
    "role",
    description="Role to ping when posting scores (leave blank to clear)",
    required=False,
    default=None
)
async def set_ping_role(ctx, channel: discord.TextChannel, role: discord.Role):
    guild_id = str(channel.guild.id)
    channel_id = str(channel.id)
    if guild_id in channels and any(item["channel_id"] == channel_id for item in channels[guild_id]):
        role_id = str(role.id) if role else ""
        channel_item = next(item for item in channels[guild_id] if item["channel_id"] == channel_id)
        channel_item["ping_role"] = role_id
        await ctx.respond(f"Updated ping role preferences in channel {channel.name}")
        update_channel_parameters()
    else:
        await ctx.respond(f"Scorepost feed is not currently enabled in channel {channel.name}")
        
async def send_feeds(submission):

    url = "https://www.reddit.com" + submission.permalink
    embed = discord.Embed(title=submission.title, url=url)
    embed.set_footer(text=f"Posted by /u/{submission.author.name}" )

    if hasattr(submission, 'preview') and 'images' in submission.preview:
        embed.set_image(url=submission.preview['images'][0]['source']['url'])

    for guild_id in channels:
        channel_items = channels[guild_id]
        for item in channel_items:
            channel_id = item["channel_id"]
            role_id = item["ping_role"]
            guild = bot.get_guild(int(guild_id))
            if guild == None:
                break
            channel = guild.get_channel(int(channel_id))
            role = guild.get_role(int(role_id)) if role_id else None
            if role:
                await channel.send(f"<@&{role_id}>",embed=embed)
            else:
                await channel.send(embed=embed)

@bot.event
async def monitor():
    reddit = asyncpraw.Reddit(
        client_id = config["reddit"]["client_id"],
        client_secret = config["reddit"]["client_secret"],
        username = config["reddit"]["username"],
        user_agent = config["reddit"]["user_agent"],
        password = config["reddit"]["password"]
    )
    subreddit = await reddit.subreddit("osugame")
    async for submission in subreddit.stream.submissions(skip_existing=True):
        print(submission.title)
        score_re = re.compile(".+[\|丨].+-.+\[.+\]")
        if score_re.match(submission.title):
            await send_feeds(submission)

bot.run(config["discord"]["token"])