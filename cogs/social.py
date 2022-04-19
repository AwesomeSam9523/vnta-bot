from utils import *
from core import *
from discord.ext import commands, tasks
import discord
import time
import aiohttp
import json
import os

bot: VntaBot = None

YT_API_KEY = os.getenv("YT_API_KEY")
SOCIAL_KEY_1 = os.getenv("SOCIAL_KEY_1")
SOCIAL_KEY_2 = os.getenv("SOCIAL_KEY_2")
SOCIAL_KEY_3 = os.getenv("SOCIAL_KEY_3")
SOCIAL_KEYS = [SOCIAL_KEY_1, SOCIAL_KEY_2, SOCIAL_KEY_3]
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

TWITTER_API_KEY = os.getenv("TWITTER_API_KEY")
TWITTER_API_SECRET = os.getenv("TWITTER_API_SECRET")
TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN")


@tasks.loop(minutes=1)
async def yt_socials_check():
    reqs = await bot.database.socials.find_one({'platform': 'youtube'})
    requests = reqs["requests"]
    if requests >= 2500:
        SOCIAL_KEY = SOCIAL_KEYS[0]
    elif requests >= 12475:
        SOCIAL_KEY = SOCIAL_KEYS[1]
    elif requests >= 22450:
        SOCIAL_KEY = SOCIAL_KEYS[2]
    else:
        SOCIAL_KEY = YT_API_KEY
        await bot.database.socials.update_one({'platform': 'youtube'}, {'$set': {'requests': 0}})
    
    async with aiohttp.ClientSession() as session:
        allSubs = reqs['subs']
        donevids  = reqs['done']
        for i in allSubs:
            i = i['id']
            ytcache = reqs['cache']
            uploadsid = ytcache.get(i)
            if uploadsid is None:
                uri = f"https://www.googleapis.com/youtube/v3/channels?id={i}&key={YT_API_KEY}&part=contentDetails"
                a = await session.get(uri)
                data = await a.json()
                if data["pageInfo"]["totalResults"] == 0:
                    await bot.database.socials.update_one({'platform': 'youtube'}, {'$pull': {'subs': i}})
                    continue

                uploadsid = data["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
                ytcache[i] = uploadsid
                await bot.database.socials.update_one({'platform': 'youtube'}, {'$set': {'cache': ytcache}})
            
            uri2 = f"https://www.googleapis.com/youtube/v3/playlistItems?part=snippet%2CcontentDetails&maxResults=50&playlistId={uploadsid}&key={SOCIAL_KEY}"
            b = await session.get(uri2)
            vids: dict = await b.json()
            if vids.get('error'):
                err = vids['error']
                print(err)
                try:
                    print(SOCIAL_KEYS.index(SOCIAL_KEY))
                except:
                    print(YT_API_KEY)

                if err['code'] == 403:
                    if requests >= 22450:
                        requests = 0
                    elif requests >= 12475:
                        requests = 22450
                    elif requests >= 2500:
                        requests = 12475
                    else:
                        requests = 2500
                    await bot.database.socials.update_one({'platform': 'youtube'}, {'$set': {'requests': requests}})
                    return
            try:
                vidid = vids["items"][0]["contentDetails"]["videoId"]
            except KeyError:
                continue
            if vidid not in donevids:
                await publishNewVideo(vidid, vids["items"][0]["snippet"]["channelTitle"])
                await bot.database.socials.update_one({'platform': 'youtube'}, {'$push': {'done': vidid}})
            await bot.database.socials.update_one({'platform': 'youtube'}, {'$inc': {'requests': 1}})

@tasks.loop(seconds=40)
async def twitch_socials_check():
    async with aiohttp.ClientSession() as session:
        data = await bot.database.socials.find_one({'platform': 'twitch'})
        live: list = data["live"]
        if data["expiry"] < time.time():
            print("Requesting new token...")
            a = await session.post(
                f"https://id.twitch.tv/oauth2/token?client_id={CLIENT_ID}&client_secret={CLIENT_SECRET}&grant_type=client_credentials"
            )
            res = await a.json()
            await bot.database.socials.update_one({'platform': 'twitch'}, {'$set': {
                'expiry': res['expires_in'] + time.time(),
                'token': res['access_token']
            }})
        headers = {'Authorization': f'Bearer {bot.twitchapi["token"]}', 'Client-Id': CLIENT_ID}
        for i in data["subs"]:
            i = i['id']
            uri = f"https://api.twitch.tv/helix/streams?user_login={i}"
            a = await session.get(uri, headers=headers)
            req2 = await a.json()
            fin = req2.get("data", [])
            if len(fin) != 0:
                if i not in live:
                    await twitchStreamStart(i, fin[0])
            else:
                await twitchSteamEnd(live[i])

@tasks.loop(seconds=40)
async def twitter_socials_check():
    header = {"Authorization": f"Bearer {TWITTER_BEARER_TOKEN}"}
    data = await bot.database.socials.find_one({'platform': 'twitter'})
    subs = data['subs']
    donetweets = data["done"]
    async with aiohttp.ClientSession() as session:
        for sub in subs:
            id = sub['id']
            uri = f"https://api.twitter.com/2/users/{id}/tweets"
            a = await session.get(uri, headers=header)
            res = await a.json()
            res = res["data"][0]
            if res['id'] not in donetweets:
                await twitterNewPost(sub['name'], data)
                await bot.database.socials.update_one({'platform': 'twitter'}, {'$push': {'done': res['id']}})

async def publishNewVideo(vidid, name):
    ytdata = await bot.database.socials.find_one({'platform': 'youtube'})
    chl = bot.get_channel(ytdata["channel"])
    if name == "VNTA Krunker":
        role = chl.guild.get_role(ytdata["role"]).mention
    else: 
        role = "Hey All!"
    await chl.send(ytdata["msg"].format(name=name, role=role, link=f"https://youtu.be/{vidid}"))

async def twitchStreamStart(key: str, data: dict):
    data = await bot.database.socials.find_one({'platform': 'twitch'})
    chl = bot.get_channel(data["channel"])
    role = chl.guild.get_role(data["role"])
    msg = await chl.send(
        data["msg"].format(
            name=data["user_name"],
            role=role.mention,
            link=f"https://twitch.tv/{data['user_login']}",
            title=data['title']
        )
    )
    await bot.database.socials.update_one({'platform': 'twitch'}, {'$push': {'live': { 'msg': msg.id, 'sub': key, 'channel': chl.id }}})

async def twitchSteamEnd(data: dict):
    chl = bot.get_channel(data['channel'])
    msg = await chl.fetch_message(data['msg'])
    if msg is not None:
        await msg.delete()
    
    await bot.database.socials.update_one({'platform': 'twitch'}, {'$pull': {'live': {'msg': data['msg']}}})

async def twitterNewPost(user: str, data: dict):
    data = await bot.database.socials.find_one({'platform': 'twitter'})
    chl = bot.get_channel(data["channel"])
    role = chl.guild.get_role(data["role"])
    twmsg = data["msg"].format(
        name=user,
        role=role.mention,
        link=f"https://twitter.com/i/web/status/{data['id']}"
    )
    await chl.send(twmsg)

class Socials(commands.Cog):
    def __init__(self, bot_) -> None:
        global bot
        bot = bot_

        yt_socials_check.start()
        twitch_socials_check.start()
        twitter_socials_check.start()

    @commands.command(aliases=["soc"])
    async def socials(
        self,
        ctx: commands.Context,
        platform: str = None,
        action: str = None
    ):
        if ctx.author.id not in bot.staff:
            return

        if platform is None:
            embed = discord.Embed(
                title="VNTA Social Manager",
                description="Here are the commands for management:",
                color=localembed
            )
            embed.add_field(name=f"{youtube} YouTube", value="Manage YouTube", inline=False)
            embed.add_field(name=f"{twitch} Twitch", value="Manage Twitch", inline=False)
            embed.add_field(name=f"{twitter} Twitter", value="Manage Twitter", inline=False)
            view = PlatformManager(ctx.author)
            view.msg = await ctx.send(embed=embed, view=view)


class PlatformManager(discord.ui.View):
    def __init__(self, author: discord.User):
        self.author = author
        self.msg = None
        super().__init__()
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        await interaction.response.defer()
        if interaction.user == self.author:
            return True
        else:
            await interaction.followup.send('You cannot control command used by others!', ephemeral=True)
            return False

    @discord.ui.button(label='YouTube', emoji=youtube, style=discord.ButtonStyle.green)
    async def youtube(self, button, interaction: discord.Interaction):
        await manage_platform(interaction, self.msg, 'youtube')

    @discord.ui.button(label='Twitch', emoji=twitch, style=discord.ButtonStyle.green)
    async def twitch(self, button, interaction: discord.Interaction):
        await manage_platform(interaction, self.msg, 'twitch')

    @discord.ui.button(label='Twitter', emoji=twitter, style=discord.ButtonStyle.green)
    async def twitter(self, button, interaction: discord.Interaction):
        await manage_platform(interaction, self.msg, 'twitter')

async def getTwitterID(username: str) -> str:
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"https://api.twitter.com/2/users/by/username/{username}",
            headers={"Authorization": f"Bearer {TWITTER_BEARER_TOKEN}"}
        ) as resp:
            data = await resp.json()
            print(json.dumps(data, indent=2))
            return data["data"]["id"]

async def getTwitchID(username: str) -> str:
    return username

async def getYoutubeID(username: str) -> str:
    return username

class Platform(discord.ui.View):
    def __init__(
        self,
        author: discord.User,
        options: dict,
        msg: discord.Message,
        platform: str
    ):
        self.author = author
        self.msg = msg
        self.platform = platform
        super().__init__()

        self.add_item(DropdownOptions(options))
    
    async def callback(self, interaction: discord.Interaction, action: str):
        await interaction.response.defer()
        data: dict = await bot.database.socials.find_one({'platform': self.platform})
        user = self.author
        ctx = interaction.channel
        if self.platform == 'youtube':
            url = 'https://www.youtube.com/channel/'
            coro = getYoutubeID
        elif self.platform == 'twitch':
            url = 'https://www.twitch.tv/'
            coro = getTwitchID
        else:
            url = 'https://www.twitter.com/'
            coro = getTwitterID

        def rcheck(reaction, user_):
            return user_ == user

        def check(msg):
            return msg.author == user and msg.channel == interaction.channel
        
        if action == "channel":
            a = data.setdefault("channel", 0)
            if a == 0:
                chl = "Not set"
            else:
                chl = bot.get_channel(a).mention

            embed = discord.Embed(
                title="Channel",
                description=f"""
> {chl}\n
f"To change the channel, react with 🇨""",
                color=localembed
            )
            msg = await ctx.send(embed=embed)
            await msg.add_reaction("🇨")

            reaction, user_ = await bot.wait_for('reaction_add', timeout=60.0, check=rcheck)
            if str(reaction.emoji) != "🇨":
                return

            await ctx.send("Send the ID of the new channel (DO NOT MENTION THE CHANNEL)")

            chlid: discord.Message = await bot.wait_for("message", timeout=60, check=check)
            try:
                newchl = int(chlid.content)
                newchl = bot.get_channel(newchl)
                if newchl is None:
                    raise ValueError
            except:
                return await chlid.reply("Invalid ID")
            
            data["channel"] = newchl.id
            await chlid.add_reaction(economysuccess)

        elif action == "subs":
            subs = data.get("subs", [])
            subs_string = ""
            for i in subs:
                subs_string += f'[`{i["name"]}`]({url}{i["id"]})\n'
            if subs_string == "":
                subs_string = "> No channels subscribed!"
            embed = discord.Embed(
                title="Your Subscriptions",
                description=subs_string,
                color=localembed
            )
            await ctx.send(embed=embed)

        elif action == "add":
            await ctx.send("Enter the channel URL to add. Prefer regular URL over vanity URL as they are more reliable")
            msg: discord.Message = await bot.wait_for("message", timeout=60, check=check)
            msgc = msg.content
            if url not in msgc:
                return await msg.reply(f"Invalid URL. The url must start with `{url}`")
                
            finalurl = msgc.replace(url, "")
            subId = await coro(finalurl)
            old = data.get("subs", [])
            if subId in [x['id'] for x in old]:
                return await msg.reply("URL already subscribed!")
            
            await ctx.send('Enter the name of the person whom the channel belongs to. This will show in the list of subscriptions')
            msg: discord.Message = await bot.wait_for("message", timeout=60, check=check)
            old.append({
                'name': msg.content,
                'id': subId,
                'mod': msg.author.id
            })
            data["subs"] = old
            await ctx.send('Subscription added!')

        elif action == "rem":
            await ctx.send("Enter the channel URL to remove")
            msg = await bot.wait_for("message", timeout=60, check=check)
            msgc = msg.content

            if url not in msgc:
                return await msg.reply(f"Invalid URL. The url must start with `{url}`")

            finalurl = msgc.replace(url, "")
            old = data.get("subs", [])
            if finalurl not in [x['id'] for x in old]:
                return await msg.reply("URL isn't subscribed!")

            for i in old:
                if i['id'] == finalurl:
                    old.remove(i)
                    break
            data["subs"] = old
            await ctx.send('Subscription removed!')
        elif action == "msg":
            oldmsg = data.setdefault("msg", "{role}: {link}")
            embed = discord.Embed(
                title="Message",
                description= f"```\n{oldmsg}```" + """
Variables:
`{role}`- Role to ping
`{name}`- Name of the user
`{link}`- Link of the video/stream
`{title}`- Title of the video/stream""",
                color=localembed
            )
            embed.set_footer(text="To change the message, react below")
            msg = await ctx.send(embed=embed)
            await msg.add_reaction("🇨")

            reaction, user_ = await bot.wait_for('reaction_add', timeout=60.0, check=rcheck)
            if str(reaction.emoji) != "🇨": return
            await ctx.send(
                "Enter the new message. You can only use the variables defined above.\n"
                "Do **not** remove the brackets `{}` from the variables"
            )

            chlid = await bot.wait_for("message", timeout=60, check=check)
            data["msg"] = chlid.content
            await chlid.add_reaction(economysuccess)

        elif action == "role":
            a = data.setdefault("role", 0)
            if a == 0:
                chl = "Not set"
            else:
                chl = ctx.guild.get_role(a).mention
            embed = discord.Embed(
                title="Role",
                description=f"""
> {chl}\n
f"To change the role, react with 🇨""",
                color=localembed
            )
            msg = await ctx.send(embed=embed)
            await msg.add_reaction("🇨")

            reaction, user_ = await bot.wait_for('reaction_add', timeout=60.0, check=rcheck)
            if str(reaction.emoji) != "🇨":
                return
            await ctx.send("Send the ID of the new role (DO NOT MENTION THE ROLE)")

            chlid = await bot.wait_for("message", timeout=60, check=check)
            try:
                newchl = int(chlid.content)
                newchl = ctx.guild.get_role(newchl)
                if newchl is None: raise ValueError
            except:
                return await chlid.reply("Invalid ID")
            data["role"] = newchl.id
            await chlid.add_reaction(economysuccess)
        else:
            return

        await bot.database.socials.update_one({"platform": self.platform}, {"$set": data}, upsert=True)

class DropdownOptions(discord.ui.Select):
    def __init__(self, options: dict):
        _options = []
        for i, j in options.items():
            _options.append(
                discord.SelectOption(label=i, value=j)
            )
        
        super().__init__(placeholder='Select your option here...', options=_options)
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        view: Platform = self.view
        await interaction.response.defer()
        if interaction.message.author == view.author:
            return True
        else:
            await interaction.followup.send('You cannot control command used by others!', ephemeral=True)
            return False
    
    async def callback(self, interaction: discord.Interaction):
        await self.view.callback(interaction, self.values[0].lower())

async def manage_platform(
    interaction: discord.Interaction,
    msg: discord.Message,
    platform: str,
):
    ctx = interaction.followup
    if platform == "twitch":
        emoji = twitch
    elif platform == "youtube":
        emoji = youtube
    elif platform == "twitter":
        emoji = twitter

    embed = discord.Embed(
        title=f"{emoji} {platform.capitalize()}",
        description="Here are the actions you can perform:",
        color=localembed
    )
    embed.add_field(name="`channel`", value="View or change the channel where you want to send notification", inline=False)
    embed.add_field(name="`subs`", value="Check the people whom you have subscribed", inline=False)
    embed.add_field(name="`add`", value="Add a subscription", inline=False)
    embed.add_field(name="`rem`", value="Remove a subscription", inline=False)
    embed.add_field(name="`msg`", value="View or change the message the bot sends", inline=False)
    embed.add_field(name="`role`", value="View or change the role which is pinged", inline=False)
    opts = {
        "Configure feed channel": "channel",
        "View people subscribed": "subs",
        "Add a subscription": "add",
        "Remove a subscription": "rem",
        "Configure message": "msg",
        "Configure role pinged": "role"
    }
    view = Platform(interaction.user, opts, msg, platform)
    await msg.edit(embed=embed, view=view)


def setup(bot_: VntaBot) -> None:
    bot_.add_cog(Socials(bot_))