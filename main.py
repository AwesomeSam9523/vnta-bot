import asyncio
import discord
import json
import aiohttp
import traceback
import time
import datetime
from discord.ext import commands, tasks
from discord.ext.commands import *
import os
from dotenv import load_dotenv
import winerp
load_dotenv()

from utils import *
from core import *

print("Starting")

cogs = [
    'cogs.misc',
    'cogs.profile',
    'cogs.social',
    'cogs.staff'
]

bot = VntaBot()
bot.apikey = os.getenv('YT_API_KEY')

bot.ipc = winerp.Client('bot', port=8080)

for i in cogs:
    bot.load_extension(i)
    print(f"Loaded {i}")

os.environ["JISHAKU_NO_UNDERSCORE"] = "True"
os.environ["JISHAKU_NO_DM_TRACEBACK"] = "True"
os.environ["JISHAKU_HIDE"] = "True"
bot.load_extension('jishaku')

async def handle_1(userid):
    warn1.append(userid)
    await asyncio.sleep(2)
    warn1.remove(userid)

async def handle_2(userid):
    warn2.append(userid)
    await asyncio.sleep(2)
    warn2.remove(userid)

async def handle_disregard(userid):
    bot.muted.append(userid)
    await asyncio.sleep(10*60)
    bot.muted.remove(userid)

@bot.ipc.event
async def on_information(*args, **kwargs):
    print(args)
    print(kwargs)
    print('info')

@bot.check
async def general(ctx):
    state = await spam_protect(ctx.author.id)
    toreturn = True
    if state == 'warn':
        embed = discord.Embed(
            description=f'{economyerror} You are being rate-limited for using commands too fast!\nTry again in few secs..',
            color=error_embed
        )
        await ctx.send(embed=embed)
        toreturn = False
    elif state == 'disregard':
        embed = discord.Embed(
            title=f'{economyerror} Warning!',
            description=f'{ctx.author.mention} has been muted for 10 mins!\n**Reason: Spamming Commands**',
            color=error_embed
        )
        await ctx.send(embed=embed)
        toreturn= False
    elif state == 'return':
        toreturn= False
    
    return toreturn


@tasks.loop(minutes=1)
async def fotd_check():
    data = await bot.database.general.find_one({'name': 'fotd'})
    if time.time() - data['last'] >= 86400:
        index = data['index']
        index += 1
        fotd = bot.get_channel(813535171117580350)
        role = bot.get_guild(719946380285837322).get_role(813704961103888434)
        upv = await fotd.send(
            f"__**{role.mention} #{index+100}**__\n\n"
            f"{facts[index]}"
        )
        await upv.add_reaction("<:Upvote:837564803090219028>")
        await bot.database.general.update_one({'name': 'fotd'}, {'$set': {'index': index, 'last': time.time()}})
        await asyncio.sleep(10)

async def spam_protect(userid):
    if userid in bot.muted:
        if userid not in devs:
            return 'return'
        else:
            return 'ok'
    last = usercmds.get(userid, 0)
    current = time.time()
    usercmds[userid] = current
    if current - last < 2:
        if userid in warn2:
            asyncio.create_task(handle_disregard(userid))
            return 'disregard'
        elif userid in warn1:
            asyncio.create_task(handle_2(userid))
            return 'warn'
        else:
            asyncio.create_task(handle_1(userid))
            return 'warn'
    else:
        return 'ok'

async def linklog(ign, user, t, linkedby=None):
    if t == "l":
        embed = discord.Embed(
            description=f"`{user}` got linked with `{ign}`",
            colour=success_embed
        )
        if linkedby is not None:
            embed.set_footer(text=f"Force-Linked By: {linkedby}")
    else:
        embed = discord.Embed(
            description=f"`{user}` got unlinked with `{ign}`",
            colour=error_embed
        )
    embed.timestamp = datetime.datetime.utcnow()
    await bot.linkinglogs.send(embed=embed)

async def timeout(user):
    bot.interlist.append(user.id)
    await asyncio.sleep(3600)
    bot.interlist.remove(user.id)

@bot.command(aliases=['eval'],hidden=True)
@commands.is_owner()
async def evaluate(ctx: commands.Context, *, expression: str):
    try:
        await ctx.reply(eval(expression))
        await ctx.message.add_reaction(economysuccess)
    except Exception as e:
        await ctx.reply(f'```\n{e}```')

@bot.command(aliases=['exec'],hidden=True)
@commands.is_owner()
async def execute(ctx: commands.Context, *, expression: str):
    try:
        exec(expression)
        await ctx.message.add_reaction(economysuccess)
    except Exception as e:
        await ctx.reply(f'Command:```py\n{expression}```\nOutput:```\n{e}```')

@bot.command()
async def help(ctx: commands.Context, specify=None):
    embed = discord.Embed(
        description=f'To get help on a command, use `v.help <command name>`',
        color=embedcolor
    )
    embed.set_author(name='Help')
    embed.set_footer(text='Bot developed by AwesomeSam#7985', icon_url=sampfp)
    if specify is None:
        cogs = []
        commands = []
        for command in bot.commands:
            usage = command.description
            name = command.name
            aliases = command.aliases
            if len(aliases) == 0:
                aliases = 'None'
            else:
                aliases = '\n'.join(aliases)
            category = command.cog_name or 'None'
            if category not in cogs:
                cogs.append(category)
            
            commands.append({
                'name': name,
                'aliases': aliases,
                'category': category,
                'usage': usage
            })
        
        for cog in ['Profile', 'Misc']:
            cmds = '\n'.join([f'{command["name"]}' for command in commands if command['category'] == cog])
            embed.add_field(
                name=cog,
                value=f'```\n{cmds}\n```',
            )
            if cog == 'Profile':
                embed.add_field(
                    name='\u200b',
                    value='\u200b',
                )
        
        return await ctx.send(embed=embed)

    command = bot.get_command(specify)
    if command is None:
        return await ctx.send(f'Command `{specify}` not found')
    else:
        embed.set_author(name=f'Help for {command.name}')
        embed.description = command.description
        usage = ''
        for name, param in command.params.items():
            name = param.name
            if name.startswith('_'):
                continue
            optional = param.default is not param.empty
            usage += f'[{name}]' if optional else f'{name}'
        if usage != '':
            usage = ' ' + usage
        embed.add_field(
            name=f'Usage',
            value=f'`v.{command.name}{usage}`',
        )
        cmd_aliases = '\nv.'.join(command.aliases)
        if cmd_aliases != '':
            cmd_aliases = 'v.' + cmd_aliases
        else:
            cmd_aliases = 'None'
        embed.add_field(
            name='Aliases',
            value=f'```\n{cmd_aliases}```',
        )
        embed.add_field(
            name='Category',
            value=f'`{command.cog_name}`',
        )
        return await ctx.send(embed=embed)


async def load_peeps():
    timeout = aiohttp.ClientTimeout(total=10)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://kr.vercel.app/api/clan?clan=vnta", timeout=timeout) as a:
                if a.status != 200:
                    bot.apidown = True
                    return
                bot.apidown = False
                data = await a.json()
                bot.vntapeeps.clear()
                for i in data["data"]["members"]:
                    bot.vntapeeps.append(i["username"].lower())
    except:
        pass

async def run_winerp_server():
    cmd = 'python3 .heroku/python/lib/python3.9/site-packages/winerp/ --port 8080'
    sub = await asyncio.create_subprocess_shell(cmd)
    print('winerp process done:', sub.pid)

async def one_ready():
    global staff
    print("Connected")
    await bot.wait_until_ready()
    await run_winerp_server()
    bot.staff = [x.id for x in bot.get_guild(719946380285837322).get_role(813439914862968842).members]
    await load_peeps()
    vnta = bot.get_guild(719946380285837322)
    bot.starboards = bot.get_channel(874717466134208612)
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=f"{vnta.member_count} peeps"))
    bot.dev = bot.get_user(771601176155783198)
    bot.linkinglogs = bot.get_channel(861463678179999784)
    print("Ready")


async def chatbotReply(message: discord.Message):
    content = message.content
    apiKey = os.getenv('CHATBOT_KEY')
    webhook = await bot.fetch_webhook(int(os.getenv('CHATBOT_WEBHOOK')))
    if bot.session is None:
        bot.session = aiohttp.ClientSession()
    reply = await bot.session.get(f"https://some-random-api.ml/chatbot?message={content}&key={apiKey}")
    reply = await reply.json()
    if reply.get("error") is not None:
        return
    await webhook.send(
        f"> {content}\n{reply['response']}",
        allowed_mentions=discord.AllowedMentions(everyone=False, roles=False, users=False)
    )

def get_staff_opinions(text: str):
    if text == "":
        return {}
    text = text.replace("\n\n", "\n> ")
    ops = text.split("\n> ")
    i = 0
    sugs = {}
    while i < len(ops):
        user = int(ops[i].replace("<@", "").replace(">", ""))
        sug = ops[i+1]
        sugs[user] = sug
        i += 2
    return sugs

@bot.event
async def on_message(message: discord.Message):
    if message.channel.id == 915489093629149195 and message.reference is None:
        return await chatbotReply(message)

    if (message.channel.id == 861555361264697355) and (message.reference is not None):
        reply = message.reference.message_id
        msg = await message.channel.fetch_message(reply)
        embed = msg.embeds[0]
        oldval = ""
        for index, i in enumerate(embed.fields):
            if i.name == "Staff Opinions:":
                oldval = i.value
                embed.remove_field(index)
                break
        if oldval == "\u200b":
            oldval = ""
        ops = get_staff_opinions(oldval)
        ops[message.author.id] = message.content
        oldval = ""
        for k, v in ops.items():
            oldval += f"<@{k}>\n> {v}\n\n"
        embed.add_field(name="Staff Opinions:", value=oldval)
        await msg.edit(embed=embed)
        await message.delete(delay=2)
        return

    if message.type in [
        discord.MessageType.premium_guild_subscription,
        discord.MessageType.premium_guild_tier_1,
        discord.MessageType.premium_guild_tier_2,
        discord.MessageType.premium_guild_tier_3,
    ]:
        user = message.author
        emoji = "<a:Boost_Spin:883010481437155368>"
        perks = """__**Single Booster Perks:**__
    
                <a:Boost_Spin:883010481437155368> 3x Claim Time on all Giveaways!
                <a:Boost_Spin:883010481437155368> Bypass all requirements on Giveaways!
                <a:Boost_Spin:883010481437155368> Custom Emote + Name (No NSFW)!
                <a:Boost_Spin:883010481437155368> Custom Role!
                <a:Boost_Spin:883010481437155368> 5x Extra Entries on all Giveaways! 
                <a:Boost_Spin:883010481437155368> Hoisted role above all members!
                <a:Boost_Spin:883010481437155368> Extra permissions in Text & Voice channels!
                <a:Boost_Spin:883010481437155368> 15% Discount on all ads you purchase!
    
                __**Double Booster Perks:**__
    
                <a:boost_evolve:829395858961334353> 10x Extra Entries!
                <a:boost_evolve:829395858961334353> Unlimited Claim Time on Giveaways!
                <a:boost_evolve:829395858961334353> Reaction with your emote!
                <a:boost_evolve:829395858961334353> Respect from all Staff!
                <a:boost_evolve:829395858961334353> An extra 20% off ads, totalling at a 35% discount!
    
                **Create a ticket in <#813510158264565780> to claim your perks and thank you for boosting!**
                """
        embed = discord.Embed(
            color=localembed,
            description=f"{emoji} Thank you for boosting {user.mention}! {emoji}\n"
                        f"We now have {bot.get_guild(719946380285837322).premium_subscription_count} boosts! **Remember to claim your perks:**\n\n"
                        f"{perks}")
        embed.set_author(name=str(user), icon_url=user.display_avatar.url)
        embed.set_footer(text="#vantalizing")
        embed.timestamp = datetime.datetime.utcnow()
        await bot.get_channel(813435497442967562).send(content=f"{user.mention}", embed=embed)

    await bot.process_commands(message)

@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    if payload.user_id == 853971223682482226:
        return

    if str(payload.emoji) == "⭐":
        return await starboard(payload)

    if str(payload.emoji) == "✨" and payload.user_id in staff:
        msg = await bot.get_guild(payload.guild_id).get_channel(payload.channel_id).fetch_message(payload.message_id)
        await msg.add_reaction("⭐")
        await msg.clear_reaction("✨")
        return await starboard(payload, force=True)

@bot.event
async def on_raw_reaction_remove(payload: discord.RawReactionActionEvent):
    if payload.user_id == 853971223682482226:
        return

    if str(payload.emoji) == "⭐":
        return await starboard(payload)

@bot.event
async def on_member_update(before, after):
    if before.roles == after.roles: return
    autroles = [y.id for y in after.roles]
    vnta = bot.get_guild(719946380285837322)
    for k, v in order.items():
        if any([x in autroles for x in v]):
            if k not in autroles:
                await after.add_roles(vnta.get_role(k))
        else:
            if k in autroles:
                await after.remove_roles(vnta.get_role(k))

@bot.command()
@commands.is_owner()
async def dividers(ctx: commands.Context):
    vnta = bot.get_guild(719946380285837322)
    i = 1
    for after in vnta.members:
        print(f"Divider for {after} ({i}/{len(vnta.members)})")
        autroles = [y.id for y in after.roles]
        for k, v in order.items():
            if any([x in autroles for x in v]):
                if k not in autroles:
                    print(f"  |- Added {k}")
                    await after.add_roles(vnta.get_role(k))
            else:
                if k in autroles:
                    print(f"  |- Removed {k}")
                    await after.remove_roles(vnta.get_role(k))
        i += 1
        print()

async def starboard(payload:discord.RawReactionActionEvent, force=False):
    msg = await bot.get_guild(payload.guild_id).get_channel(payload.channel_id).fetch_message(payload.message_id)
    stars_ = msg.reactions
    stars = 0
    for i in stars_:
        if str(i.emoji) == "⭐":
            stars = i.count
            break
    msgdata = await bot.database.starboard.find_one({'payload': payload.message_id})
    if msgdata is not None:
        oldmsg = msgdata['message']
        msg = await bot.get_guild(payload.guild_id).get_channel(874717466134208612).fetch_message(oldmsg)
        await msg.edit(content=f"✨ **{stars}** <#{payload.channel_id}>")

    elif (stars >= 5 and msgdata is None) or force:
        embed = discord.Embed(description=msg.content, color=localembed)
        embed.set_author(name=msg.author, icon_url=msg.author.display_avatar.url)
        embed.add_field(name="Orignal", value=f"[Jump!]({msg.jump_url})")
        embed.timestamp = datetime.datetime.utcnow()
        if len(msg.attachments) != 0:
            embed.set_image(url=msg.attachments[0].url)
        msg = await bot.starboards.send(f"✨ **{stars}** <#{payload.channel_id}>", embed=embed)
        msgdata['message'] = msg.id
        await bot.database.starboard.update_one({'payload': payload.message_id}, {'$set': msgdata}, upsert=True)

@bot.event
async def on_command_error(
    ctx: commands.Context,
    error: commands.CommandError,
):
    error = getattr(error, "original", error)
    if isinstance(error, CheckFailure):
        return
    
    if isinstance(error, commands.CommandNotFound):
        return await ctx.send(f"{ctx.author.mention} That command doesn't exist!")
    
    if isinstance(error, commands.MissingRequiredArgument):
        return await ctx.send(
            f"{ctx.author.mention} You're missing a required argument! " + 
            f"Refer to `{ctx.prefix}help {ctx.command}` for more info."
    )

    if isinstance(error, commands.BadArgument):
        return await ctx.send(
            f"{ctx.author.mention} That's not a valid argument! " + 
            f"Refer to `{ctx.prefix}help {ctx.command}` for more info."
        )

    if isinstance(error, commands.CommandInvokeError):
        await ctx.send(
            f"{ctx.author.mention} An error occured! " + 
            f"Please contact the bot owner."
    )

    etype = type(error)
    trace = error.__traceback__
    lines = traceback.format_exception(etype, error, trace)
    traceback_text = ''.join(lines)
    print(traceback_text)
    lent = 1970 - len(ctx.message.content)
    await bot.get_channel(873038954163748954).send(
        f"Command: `{ctx.message.content}`\n"
        f"```py\n{traceback_text[:lent]}```"
    )

bot.loop.create_task(one_ready())
bot.run(os.getenv('TOKEN'))
