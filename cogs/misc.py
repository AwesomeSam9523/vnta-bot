from utils import *
from core import *
from discord.ext import commands, tasks
import discord
import asyncio
import time
import aiohttp
from PIL import ImageColor, Image
import io
import datetime
import uuid

bot: VntaBot = None

class Reviewal(discord.ui.View):
    def __init__(self, uuid_, type):
        super().__init__(timeout=None)
        self.add_item(Accept(uuid_, type))
        self.add_item(Decline(uuid_, type))

async def addReminder(desc: str, secs: int, ctx: commands.Context):
    remid = (await bot.database.reminders.find_one({'name': 'reminder_count'}))['value']
    await bot.database.reminders.update_one(
        {'name': 'reminder_count'}, {'$inc': {'value': 1}}
    )
    await bot.database.reminders.insert_one(
        {"tadd": time.time(), "desc":desc, "time":secs, "remid":remid+1, "chl":ctx.channel.id, "id": ctx.author.id}
    )

@tasks.loop(seconds=2)
async def handle_reminders():
    rems = await bot.database.reminders.find({}).to_list(length=None)
    for reminder in rems:
        if reminder.get('name') is not None:
            continue
        if reminder['time'] <= time.time() - reminder['tadd']:
            await bot.database.reminders.delete_one({'remid': reminder['remid']})
            await execute_reminder(reminder)


async def execute_reminder(rem):
    user = bot.get_user(int(rem['id']))
    if user is None:
        return
    embed = discord.Embed(
        title="Reminder",
        description=f"""
{rem['desc']}
Set at: <t:{int(rem['tadd'])}:F> (<t:{int(rem['tadd'])}:R>)""",
        color=embedcolor
    )
    embed.set_author(name=user.name, icon_url=user.display_avatar.url)
    embed.set_thumbnail(url="https://pngimg.com/uploads/stopwatch/stopwatch_PNG140.png")
    try:
        await user.send(embed=embed)
    except:
        await bot.get_channel(rem["chl"]).send(f"{user.mention}", embed=embed)


async def conv_rem(msg: str):
    days = 0
    hrs = 0
    mins = 0
    secs = 0
    try:
        if "d" in msg:
            newmsg = msg.split("d")
            days = int(newmsg[0])
            newmsg.pop(0)
            msg = "".join(newmsg)
        if "h" in msg:
            newmsg = msg.split("h")
            hrs = int(newmsg[0])
            newmsg.pop(0)
            msg = "".join(newmsg)
        if "m" in msg:
            newmsg = msg.split("m")
            mins = int(newmsg[0])
            newmsg.pop(0)
            msg = "".join(newmsg)
        if "s" in msg:
            newmsg = msg.split("s")
            secs = int(newmsg[0])
            newmsg.pop(0)
            msg = "".join(newmsg)
        return (days*86400) + (hrs*3600) + (mins*60) + secs
    except:
        return "error"

class Misc(commands.Cog):
    def __init__(self, bot_) -> None:
        global bot
        bot = bot_
        handle_reminders.start()
        bot.loop.create_task(self.database_stuff())

    async def database_stuff(self):
        d = await bot.database.posts.find_one(
            { 'name': 'approval' }
        )
        for val in ['suggest', 'scopes', 'css', 'settings']:
            data = d[val]
            for i in data:
                uuid_, data = list(i.items())[0]
                bot.add_view(Reviewal(uuid_, val), message_id=data[2])
    
    @commands.command()
    async def ping(
        self,
        ctx: commands.Context
    ):
        msg = await ctx.send('Pinging Bot...')
        ping = "{:.2f} ms".format(bot.latency*1000)
        await msg.edit(
            content=f'Pong!\nBot: `{ping}`\nPinging Web Server...'
        )
        t1 = time.time()
        async with aiohttp.ClientSession() as session:
            async with session.get("https://vntaweb.herokuapp.com/ping") as a:
                if a.status == 200:
                    pingtime = "{:.2f} ms".format((time.time() - t1)*1000)
                else:
                    pingtime = f"Unreachable ({a.status})"
        await msg.edit(
            content=f'Pong!\nBot: `{ping}`\nWeb: `{pingtime}`'
        )
    
    
    @commands.command(aliases=["color"])
    async def colour(
        self,
        ctx: commands.Context,
        *,
        color: str
    ):
        if color.startswith("#") and len(color) == 7:
            h = color.lower()
            r, g, b = ImageColor.getcolor(h, "RGB")
        else:
            r, g, b = color.replace(" ", "").split(",")
        r = int(r)
        g = int(g)
        b = int(b)
        if (r > 255 or r < 0) or (g > 255 or g < 0) or (b > 255 or b < 0):
            return await ctx.reply("Invalid Color")
    
        hex_code = '%02x%02x%02x' % (r, g, b)
        embedc = int(hex_code, 16)
        embed = discord.Embed(
            title="Color",
            description=f"RGB Code: {r}, {g}, {b}\nHex Code: #{hex_code}",
            color=embedc
        )

        image = Image.open('images/vnta_logo.png')
        pixdata = image.load()
        for y in range(image.size[1]):
            for x in range(image.size[0]):
                pixdata[x, y] = tuple(list((r, g, b)) + [pixdata[x, y][-1]])
        image_bytes = io.BytesIO()
        image.save(image_bytes, 'PNG', transparent=True)
        image_bytes.seek(0)
        embed.set_thumbnail(url="attachment://logo.png")
        await ctx.send(embed=embed, file=discord.File(image_bytes, filename=f"logo.png"))
    
    
    @commands.command(aliases=["rem", "rems", "reminders"])
    async def reminder(
        self,
        ctx: commands.Context,
        action: str = None,
        *args
    ):
        if action is None:
            embed = discord.Embed(
                title="Reminders",
                description="""
Set a reminder and let the bot DM/ping you. Never forget anything again!\n
**Commands:**
`v.rem add`  (for interactive setup)
`v.rem show` (view all active reminders)
`v.rem del <reminder-id>` (delete reminder)
`v.rem del -a`             (delete all reminders)

**For a quick reminder:** `v.remindme <time> [desc]`
Example:
- `v.remindme 5m switch off microwave`
- `v.remindme 1h english class`
- `v.remindme 2d5h announce smth`""",
                color=embedcolor
            )
            embed.set_thumbnail(url="https://pngimg.com/uploads/stopwatch/stopwatch_PNG140.png")
            return await ctx.send(embed=embed)

        if action.lower() == "show":
            aut = await bot.getReminders(ctx.author.id)
            if len(aut) == 0:
                embed = discord.Embed(
                    description="Nothing here. But its never too late to add a reminder!",
                    color=localembed
                )
                embed.set_author(name=f'{ctx.author.name}\'s Reminders:', icon_url=ctx.author.display_avatar.url)
                embed.set_thumbnail(
                    url="https://pngimg.com/uploads/stopwatch/stopwatch_PNG140.png")

                return await ctx.send(embed=embed)
            embed = discord.Embed(
                title="Your Reminders",
                color=localembed
            )
            embed.set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar.url)
            embed.set_thumbnail(url="https://pngimg.com/uploads/stopwatch/stopwatch_PNG140.png")

            for i in aut:
                hours, remainder = divmod(int(i["time"] - time.time() + i["tadd"]), 3600)
                minutes, seconds = divmod(remainder, 60)
                days, hours = divmod(hours, 24)
                embed.add_field(
                    name=f"ID: {i['remid']}",
                    value=f"""
`Desc:` {i['desc']}
`Time Left:` {days}d, {hours}h, {minutes}m, {seconds}s
`Set at:` <t:{int(i['tadd'])}:F> (<t:{int(i['tadd'])}:R>)
`End at:` <t:{int(i['time'] + i['tadd'])}:F> (<t:{int(i['time'] + i['tadd'])}:R>)""",
                    inline=False
                )
            await ctx.send(embed=embed)
        elif action.lower() == "add":
            try:
                embed = discord.Embed(
                    title="Add a reminder",
                    description="Enter the description for the reminder.\nFor empty description, type `skip`",
                    color=localembed
                )
                embed.set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar.url)
                embed.set_thumbnail(url="https://pngimg.com/uploads/stopwatch/stopwatch_PNG140.png")
                em = await ctx.send(embed=embed)

                def check(msg):
                    return msg.author == ctx.author and msg.channel == ctx.channel

                msg = await bot.wait_for("message", timeout=300, check=check)
                desc = msg.content
                if desc.lower() == "skip":
                    desc = ""
                await msg.delete()
                embed = discord.Embed(
                    title="Add a reminder",
                    description="""
Enter the time duration from now. This should be in x**d**x**h**x**m**x**s**
Examples:
`1d5h`  => 1 day 5 hrs
`5h10m` => 5 hrs 10 mins
`5m30s` => 5 mins 30 secs""",
                    color=localembed
                )
                embed.set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar.url)
                embed.set_thumbnail(url="https://pngimg.com/uploads/stopwatch/stopwatch_PNG140.png")
                await em.edit(embed=embed)

                def check(msg):
                    return msg.author == ctx.author and msg.channel == ctx.channel

                msg_ = await bot.wait_for("message", timeout=300, check=check)
                msg = msg_.content.lower()

                secs = await conv_rem(msg)
                if secs == "error":
                    return await ctx.send(f"{ctx.author.mention} Invalid time format!")
                
                await addReminder(desc, secs, ctx)
                await msg_.delete()
                embed = discord.Embed(
                    title="Add a reminder",
                    description=f"Done! I will remind you at <t:{int(time.time() + secs)}:F> ;)",
                    colour=localembed
                )
                embed.set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar.url)
                embed.set_thumbnail(url="https://pngimg.com/uploads/stopwatch/stopwatch_PNG140.png")
                await em.edit(embed=embed)
            except asyncio.TimeoutError:
                await ctx.send(f"{ctx.author.mention} You didn't reply in time. Reminder aborted")
        elif action.lower() in ["delete", "del"]:
            aut = await bot.getReminders(ctx.author.id)
            if len(aut) == 0:
                embed = discord.Embed(
                    title="Your Reminders",
                    description="Nothing here. But its never too late to add a reminder!",
                    color=localembed
                )
                embed.set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar.url)
                embed.set_thumbnail(url="https://pngimg.com/uploads/stopwatch/stopwatch_PNG140.png")
                return await ctx.send(embed=embed)
            try:
                if any(["-a" in args, "-A" in args]):
                    await ctx.send(f"{ctx.author.mention} Are you sure you want to delete all your reminders? **(`Y`/`N`)**")
                    def check(msg):
                        return msg.author == ctx.author and msg.channel == ctx.channel
                    msg = await bot.wait_for("message", timeout=300, check=check)

                    if msg.content.lower() == "y":
                        await bot.database.reminders.delete_many({"id": ctx.author.id})
                        await ctx.send(f"{ctx.author.mention} All your reminders have been deleted")
                        return
                else:
                    args = [int(x) for x in args]
                    await bot.database.reminders.delete_many(
                        {"id": ctx.author.id, "remid": {"$in": args}}
                    )
                await ctx.reply(f"{economysuccess} Reminder(s) Deleted")
            except NameError as e:
                await ctx.reply(f"Invalid Reminder ID(s): `{e}`")
            
        else:
            await self.reminder(ctx)


    @commands.command()
    async def remindme(
        self,
        ctx: commands.Context,
        rtime: str,
        *,
        desc: str = None
    ):
        secs = await conv_rem(rtime.lower())
        if secs == "error":
            return await ctx.send(f"{ctx.author.mention} Invalid time format!")
    
        if desc is None:
            desc = ""

        await addReminder(desc, secs, ctx)
        embed = discord.Embed(
            title="Quick Reminder",
            description=f"Done! I will remind you at <t:{int(time.time() + secs)}:F> ;)",
            colour=localembed
        )
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar.url)
        embed.set_thumbnail(
            url="https://pngimg.com/uploads/stopwatch/stopwatch_PNG140.png")
        await ctx.send(embed=embed)

    
    @commands.command()
    async def post(
        self,
        ctx: commands.Context
    ):
        view = Post(ctx)
        view.msg = await ctx.send("**Choose:**", view=view)

class Post(discord.ui.View):
    def __init__(self, ctx: commands.Context):
        super().__init__()
        self.ctx = ctx
        self.msg = None
        self.uuid = str(uuid.uuid4())

    @discord.ui.button(label="Suggestion", emoji="👤", style=discord.ButtonStyle.green)
    async def suggestion(self, button, interaction: discord.Interaction):
        if interaction.user.id != self.ctx.author.id:
            return await interaction.response.defer()
        ctx = self.ctx
        def check(msg):
            return msg.author == ctx.author and msg.channel == ctx.channel

        await interaction.response.send_message("Enter your suggestion", ephemeral=True)
        try:
            msg = await bot.wait_for("message", timeout=180, check=check)
            sug = msg.content
            stfchl = bot.get_channel(813447381752348723)
            embed = discord.Embed(
                title="Suggestion Approval",
                description=sug,
                color=localembed
            )
            embed.set_author(name=ctx.author, icon_url=ctx.author.display_avatar.url)
            em = await stfchl.send(embed=embed, view=Reviewal(self.uuid, 'suggest'))
            await bot.database.posts.update_one(
                {'name': 'approval'},
                {'$push': {'suggest': {self.uuid: [ctx.author.id, sug, em.id]}}}
            )
            await msg.delete()
            await ctx.send(
                "Your suggestion is sent to staff for approval."
                " It will show in <#861555361264697355> once its approved!"
            )
        except:
            pass

    @discord.ui.button(label="Settings", emoji="⚙️", style=discord.ButtonStyle.grey)
    async def settings(self, button, interaction: discord.Interaction):
        if interaction.user.id != self.ctx.author.id: return await interaction.response.defer()
        ctx = self.ctx
        def check(msg):
            return msg.author == ctx.author and len(msg.attachments) != 0

        await interaction.response.send_message("Upload the `.txt` file", ephemeral=True)
        try:
            msg = await bot.wait_for("message", timeout=180, check=check)
            file = msg.attachments[0].url
            async with aiohttp.ClientSession() as session:
                async with session.get(file) as r:
                    text = await r.text()
                    with open(f"settings.txt", "w", encoding='utf8') as f:
                        f.write(text)
                    file = discord.File("settings.txt")
                    a = await bot.get_channel(865587676999843840).send(file=file)
                    file = a.attachments[0].url
            await msg.delete()
            await ctx.send(
                "Your settings are sent to staff for approval. It will show in <#882312116797861899> once they are approved!"
            )
            embed = discord.Embed(
                title="Settings Approval",
                description=file,
                color=localembed
            )
            embed.set_author(name=str(ctx.author), icon_url=ctx.author.display_avatar.url)
            a = await bot.get_channel(813447381752348723).send(embed=embed, view=Reviewal(self.uuid, 'settings'))
            await bot.database.posts.update_one(
                {'name': 'approval'},
                {'$push': {'settings': {self.uuid: [ctx.author.id, file, a.id]}}}
            )
        except asyncio.TimeoutError:
            pass

    @discord.ui.button(label="CSS", emoji="🗒️", style=discord.ButtonStyle.red)
    async def css(self, button, interaction: discord.Interaction):
        if interaction.user.id != self.ctx.author.id: return await interaction.response.defer()
        ctx = self.ctx

        def check(msg):
            return msg.author == ctx.author and len(msg.attachments) != 0

        await interaction.response.send_message("Upload the `.css` file", ephemeral=True)
        try:
            msg = await bot.wait_for("message", timeout=180, check=check)
            file = msg.attachments[0].url
            async with aiohttp.ClientSession() as session:
                async with session.get(file) as r:
                    text = await r.text()
                    with open(f"main_custom.css", "w", encoding='utf8') as f:
                        f.write(text)
                    file = discord.File("main_custom.css")
                    a = await bot.get_channel(865587676999843840).send(file=file)
                    file = a.attachments[0].url
            await msg.delete()
            await ctx.send(
                "Your css is sent to staff for approval. It will show in <#882312235416965120> once it is approved!"
            )
            embed = discord.Embed(
                title="CSS Approval",
                description=file,
                color=localembed
            )
            embed.set_author(name=str(ctx.author), icon_url=ctx.author.display_avatar.url)
            a = await bot.get_channel(813447381752348723).send(embed=embed, view=Reviewal(self.uuid, 'css'))
            await bot.database.posts.update_one(
                {'name': 'approval'},
                {'$push': {'css': {self.uuid: [ctx.author.id, file, a.id]}}}
            )
        except asyncio.TimeoutError:
            pass

    @discord.ui.button(label="Scope", emoji="🔭", style=discord.ButtonStyle.blurple)
    async def scope(self, button, interaction: discord.Interaction):
        if interaction.user.id != self.ctx.author.id: return await interaction.response.defer()
        ctx = self.ctx

        def check(msg):
            return msg.author == ctx.author and len(msg.attachments) != 0

        await interaction.response.send_message("Attach the file or send the link to it.", ephemeral=True)
        try:
            msg = await bot.wait_for("message", timeout=180, check=check)
            try:
                file = msg.attachments[0].url
            except:
                file = msg.content

            embed = discord.Embed(
                title="Scope Approval",
                color=localembed
            )
            embed.set_image(url=file)
            embed.set_author(name=str(ctx.author), icon_url=ctx.author.display_avatar.url)
            a = await bot.get_channel(813447381752348723).send(embed=embed, view=Reviewal(self.uuid, 'scope'))
            await ctx.send(
                "Your scope is sent to staff for approval. It will show in <#882312052432068689> once it is approved!"
            )
            await bot.database.posts.update_one(
                {'name': 'approval'},
                {'$push': {'scopes': {self.uuid: [ctx.author.id, file, a.id]}}}
            )
        except asyncio.TimeoutError:
            pass

async def settings_approval(data):
    user, file, msg = data
    user = bot.get_user(user)
    if user is None:
        return

    chl = bot.get_channel(882312116797861899)
    async with aiohttp.ClientSession() as session:
        async with session.get(file) as r:
            text = await r.text()
            with open(f"settings.txt", "w", encoding='utf8') as f:
                f.write(text)
    file = discord.File("settings.txt")
    em = await chl.send(
        f"Settings by: {user.mention}\n"
        f"React with 👍 or 👎 to rate it",
        file=file
    )
    await em.add_reaction("👍")
    await em.add_reaction("👎")

async def suggest_approval(data):
    user, suggestion, msg = data
    user = bot.get_user(user)
    if user is None:
        return

    sugchl = bot.get_channel(861555361264697355)
    embed = discord.Embed(
        description=suggestion,
        color=localembed
    )
    embed.add_field(name="Staff Opinions:", value="\u200b")
    embed.set_author(name=f"By: {user}", icon_url=user.display_avatar.url)
    embed.set_footer(text="#vantalizing")
    embed.timestamp = datetime.datetime.utcnow()
    em = await sugchl.send(embed=embed)
    await em.add_reaction("👍")
    await em.add_reaction("👎")

async def css_approval(data):
    user, file, msg = data
    user = bot.get_user(user)
    if user is None:
        return
    
    chl = bot.get_channel(882312235416965120)
    async with aiohttp.ClientSession() as session:
        async with session.get(file) as r:
            text = await r.text()
            with open(f"main_custom.css", "w", encoding='utf8') as f:
                f.write(text)
    file = discord.File("main_custom.css")
    em = await chl.send(
        f"CSS by: {user.mention}\n"
        f"React with 👍 or 👎 to rate it",
        file=file
    )
    await em.add_reaction("👍")
    await em.add_reaction("👎")
    

async def scope_approval(data):
    user, file, msg = data
    user = bot.get_user(user)
    if user is None: 
        return

    chl = bot.get_channel(882312052432068689)
    em = await chl.send(
        f"Scope by: {user.mention}\n"
        f"{file}\n\n"
        f"React with 👍 or 👎 to rate it")
    await em.add_reaction("👍")
    await em.add_reaction("👎")

class Accept(discord.ui.Button):
    def __init__(self, uuid_, type):
        self.uuid = uuid_
        self.type_ = type
        super().__init__(
            style=discord.ButtonStyle.green,
            label='Accept',
            custom_id=f'{uuid_}-{type}-a'
        )
    
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            'Processing...', ephemeral=True
        )
        type = self.type_
        
        data = await bot.database.posts.find_one({'name': 'approval'})
        data = [x for x in data[self.type_] if list(x.keys())[0] == str(self.uuid)][0][self.uuid]
        user = data[0]
        try:
            await bot.get_user(user).send(
                f'{economysuccess} Your {self.type_} was accepted by {str(interaction.user)}'
            )
        except:
            pass
        
        if type == "suggest":
            await suggest_approval(data)
        elif type == "settings":
            await settings_approval(data)
        elif type == "css":
            await css_approval(data)
        elif type == "scopes":
            await scope_approval(data)
        
        await bot.database.posts.update_one(
            {'name': 'approval'},
            {'$pull': {self.type_: {str(self.uuid): data}}}
        )
        #await interaction.response.delete()
        await interaction.message.edit(content=f'{economysuccess} Accepted by: {str(interaction.user)}', view=None)

class Decline(discord.ui.Button):
    def __init__(self, uuid_, type):
        self.uuid = uuid_
        self.type_ = type
        super().__init__(
            style=discord.ButtonStyle.red,
            label='Decline',
            custom_id=f'{uuid_}-{type}-b'
        )
    
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            'Processing...', ephemeral=True
        )
        data = await bot.database.posts.find_one({'name': 'approval'})
        data = [x for x in data[self.type_] if list(x.keys())[0] == str(self.uuid)][0][self.uuid]
        user = data[0]
        try:
            await bot.get_user(user).send(
                f'{economyerror} Your {self.type_} was rejected by {str(interaction.user)}'
            )
        except:
            pass
        await bot.database.posts.update_one(
            {'name': 'approval'},
            {'$pull': {self.type_: {str(self.uuid): data}}}
        )
        await interaction.message.edit(content=f'{economyerror} Declied by: {str(interaction.user)}', view=None)


def setup(bot_: VntaBot) -> None:
    bot_.add_cog(Misc(bot_))