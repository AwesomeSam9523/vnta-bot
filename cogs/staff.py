from re import S
from utils import *
from core import *
from discord.ext import commands, tasks
import discord
import aiohttp
from PIL import ImageColor, Image
from typing import Union

def isStaff(ctx: commands.Context):
    return ctx.author.id in ctx.bot.staff

bot: VntaBot = None

class Staff(commands.Cog):

    def __init__(self, bot_) -> None:
        global bot
        bot = bot_
    
    @commands.command(aliases=["addemoji"])
    @commands.has_permissions(manage_emojis=True)
    async def steal(
        self,
        ctx: commands.Context, name:str,
        emoji: Union[discord.Emoji, str] = None):
        url = ""
        if isinstance(emoji, discord.Emoji):
            url = emoji.url
        elif isinstance(emoji, str):
            url = emoji
        elif emoji is None and len(ctx.message.attachments) != 0:
            url = ctx.message.attachments[0].url
        else:
            await ctx.send("Incorrect Syntax! Use `v.steal <name> [url or emoji or file-attachment]`")

        if len(name) < 2:
            return await ctx.reply("Name should be minimum 2 characters long")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        await ctx.send("Failed to get emoji!")
                        return
                    data = await resp.read()
                    newemoji = await ctx.guild.create_custom_emoji(name=name, image=data)
                    await ctx.send(f"""
Added emoji successfully!
Emoji: {newemoji}
Name: {newemoji.name}
Code: `:{newemoji.name}:{newemoji.id}`"""
                    )
        except Exception as e:
            await ctx.send(f"An error occured: {e}")

    @commands.command()
    @commands.check(isStaff)
    async def mute(
        self,
        ctx: commands.Context,
        member: discord.Member
    ):
        bot.muted.append(member.id)
        embed = discord.Embed(
            title=f'{economyerror} Warning!',
            description=f'**{member.mention} has been muted indefinately!**',
            color=error_embed
        )
        await ctx.send(embed=embed)

    @commands.command()
    @commands.check(isStaff)
    async def unmute(
        self,
        ctx: commands.Context,
        member: discord.Member
    ):
        bot.muted.remove(member.id)
        await ctx.message.add_reaction(economysuccess)
    
    @commands.command()
    @commands.is_owner()
    async def enable(
        self,
        ctx: commands.Context,
        cmd: str
    ):
        bot.dcmds.pop(cmd)
        await bot.database.staff.update_one({'name': 'disabled'}, {'$pull': {'cmds': cmd}})
        await ctx.message.add_reaction(economysuccess)
    
    @commands.command()
    @commands.is_owner()
    async def disable(
        self,
        ctx: commands.Context,
        cmd: str
    ):
        await bot.database.staff.update_one({'name': 'disabled'}, {'$push': {'cmds': cmd}})
        await ctx.message.add_reaction(economysuccess)
    

    @commands.command()
    @commands.check(isStaff)
    async def say(
        self,
        ctx: commands.Context,
        *,
        sentence: str
    ):
        chl = sentence.split(" ")[0]
        chlmodified = False
        testchl = chl.replace("<#", "").replace(">", "")
        if len(testchl) == 18:
            try:
                chl = int(testchl)
                saycmd[str(ctx.author.id)] = chl
                chlmodified = True
            except Exception as e:
                pass
        chnid = saycmd.get(str(ctx.author.id))
        if chnid is None:
            return await ctx.reply(
                "No last used channel found! Use `v.say #channel <msg>` to set a channel for the first time."
            )
        chn = bot.get_channel(chnid)
        try:
            if chlmodified:
                sentence_new = " ".join(sentence.split(" ")[1:])
                await chn.send(sentence_new)
            else:
                await chn.send(sentence)
        except:
            ctx.reply("An error occured. Make sure I have sufficient permission in the channel to talk")
    
    
    @commands.command(aliases=["fl", "forcel", "flink"])
    @commands.check(isStaff)
    async def forcelink(
        self,
        ctx: commands.Context,
        user:discord.Member,
        *,
        ign: str
    ):
        t = await bot.getAccounts(user.id)
        if t:
            t["all"] = list(set(t["all"]))
            if ign.lower() in [x.lower() for x in t["all"]]:
                return await ctx.reply(f"User is already linked with `{ign}`")
            t["all"].append(ign)
        else:
            t = {
                "all": [ign],
                "main": ign
            }
        await bot.database.links.update_one({'id': user.id}, {'$set': t}, upsert=True)
        try:
            await user.send(
                f"✅ You were force-linked with `{ign}`.\n"
                f"If this seems incorrect, you can unlink using `v.unlink {ign}` and report the issue to <@771601176155783198>"
            )
        except:
            pass
        await ctx.reply("Done")
        #await linklog(ign=ign, user=user, t="l", linkedby=ctx.author) TODO
    
    
    @commands.command()
    @commands.is_owner()
    async def ov(
        self,
        ctx: commands.Context,
        *,
        bgname: str
    ):
        bgname = bgname.lower()
        bgdat = await bot.getBgData(bgname)
        if bgdat is None:
            return await ctx.reply(f"Background `{bgname}` not found!")
        
        await bot.database.bgdata.update_one({'name': bgname}, {'$set': {'ov': not bgdat["ov"]}})
        await ctx.message.add_reaction(economysuccess)


def setup(bot_: VntaBot) -> None:
    bot_.add_cog(Staff(bot_))