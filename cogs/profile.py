import re
from discord.ext import commands
import aiohttp
import time
import datetime
import discord
from utils import *
from core import *
import time
import random
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter, ImageSequence, ImageColor
from io import BytesIO
import copy
import asyncio

from utils.functions import notLinkedYet, userNotLinkedYet

bot: VntaBot = None

class Profile(commands.Cog):
    def __init__(self, bot_) -> None:
        global bot
        bot = bot_
    
        
    @commands.command()
    async def link(
        self,
        ctx: commands.Context,
        *,
        ign: str
    ):
        d = await bot.getAccounts(ctx.author.id)
        if d is not None and ign.lower() in [x.lower for x in d['all']]:
            return await ctx.send("You already have this account linked")

        await ctx.message.add_reaction(loading)
        apiReq = VntabotAPI()
        data = await apiReq.get(ign)
        if data.status != 200:
            await apiError(ctx)
            await ctx.message.clear_reaction(loading)
            await apiReq.end()
            return

        userdata = await data.json()
        await apiReq.end()
        if not userdata["success"]:
            await ctx.message.clear_reaction(loading)
            return await ctx.reply(userdata["error"])

        randflag = random.choice(flags_list)
        newflag = randflag[2]
        embed = discord.Embed(
            title="Link your account..",
            description=f"""```diff
- Open krunker.io and login with your account
+ Click your profile on top right and go to settings
- Change your flag to '{randflag[0]}'
+ Enter the match and finish it.```""",
            color=embedcolor
        )
        embed.set_footer(text="Once done, react below..")
        await ctx.message.clear_reaction(loading)
        view = LinkAccount(ctx.author.id, ign, newflag)
        view.msg = await ctx.send(embed=embed, view=view)
    
    
    @commands.command()
    async def unlink(
        self,
        ctx: commands.Context,
        *,
        ign: str
    ):
        t = await bot.getAccounts(ctx.author.id)
        if t is None:
            return await ctx.send('You don\'t have any linked account.')

        t["all"] = list(set(t["all"]))
        found = False
        totalunlink = False
        for i in t["all"]:
            if i.lower() == ign.lower():
                t["all"].remove(i)
                if t["main"].lower() == ign.lower() and len(t["all"]) != 0:
                    t["main"] = t["all"][0]
                else:
                    totalunlink = True
                found = True
                break
        if not found:
            return await ctx.reply("You can only unlink the accounts which are linked to you")
        if totalunlink:
            await bot.database.links.delete_one({ 'id': ctx.author.id })
        else:
            await bot.database.links.find_one_and_update(
                { 'id': ctx.author.id },
                { '$set': { 'all': t } }
            )

        await ctx.send(f"✅ You are unlinked with `{ign}`")
        #await linklog(ign=ign, user=ctx.author, t="ul") #TODO: fix
    
    
    @commands.command(aliases=["p", "pf"])
    async def profile(
        self,
        ctx: commands.Context,
        *,
        ign: str = None,
        _via: bool = False
    ):
        via = _via
        if bot.pause:
            return await ctx.send("⚠ ️Maintainence Update. Please retry later")
        if not via:
            if ign is None:
                ign = await bot.getAccounts(ctx.author.id)
                if ign is None:
                    return await notLinkedYet(ctx)
                ign = ign["main"]
            else:
                possible = str(ign).replace('<@!', '').replace('>', '').replace('<@', '')
                if len(possible) == 18:
                    id = int(possible)
                    ign = await bot.getAccounts(id)
                    isIncognito = (await bot.getUserData(id) or {}).get('incognito', False)
                    if isIncognito and (ctx.author.id != id):
                        ign = None
                    if ign is None:
                        return await userNotLinkedYet(ctx)
                    ign = ign["main"]
        await ctx.message.add_reaction(loading)
        if isinstance(ign, dict):
            ign = ign["main"]
        print(ign)
        found = False
        bgdata = await bot.getBgData(ign)
        if not bgdata:
            bgdata = {
                'file': 'https://media.discordapp.net/attachments/856723935357173780/856731786456858684/unknown.png',
                'hd': [255, 123, 57],
                'st': [222, 222, 222],
                'mt': '#vantalizing',
                'us': [36, 36, 36],
                'ov': True
            }
        else:
            found = True
        if via:
            for i, data in bot.unsaved.items():
                if i.lower() != ign.lower():
                    continue
                if data["file"] != "":
                    bgdata = data
                    found = True
                    break

        apiReq = VntabotAPI()
        try:
            data = await apiReq.get(ign)
            userdata = await data.json()
            if not userdata["success"]:
                await ctx.message.clear_reaction(loading)
                return await ctx.reply(userdata["error"])
        except:
            await ctx.message.clear_reaction(loading)
            return await apiError(ctx)
        finally:
            await apiReq.end()
        userdata = userdata["data"]
        username = userdata["username"]
        clan = userdata["clan"]
        if not found:
            if clan == "VNTA":
                bgdata = await bot.getBgData("vntasam123")

        kills = userdata["kills"]
        deaths = userdata["deaths"]
        kr = userdata["funds"]
        datestr = userdata["createdAt"].split("T")[0]
        wins = userdata["wins"]
        score = userdata["score"]
        level = userdata["level"]
        played = userdata["games"]
        loses = played - wins
        challenge = userdata.get("challenge")
        if challenge is None:
            challenge = 0
        else:
            challenge = int(challenge) + 1
        nukes = userdata["stats"].get("n", 0)
        headshots = userdata["stats"].get("hs", 0)
        shots = userdata["stats"].get("s", 0)
        hits = userdata["stats"].get("h", 0)
        timeplayed = int(userdata["timePlayed"]/1000)
        melee = userdata["stats"].get("mk", 0)
        wallbangs = userdata["stats"].get("wb", 0)
        date_obj = datetime.datetime.strptime(datestr, '%Y-%m-%d')
        now = datetime.datetime.now()
        daysplayed = (now-date_obj).days
        if kills == 0: mpk = "{:.2f}".format((shots - hits)/1)
        else: mpk = "{:.2f}".format((shots - hits) / kills)
        if hits == 0: hps = "{:.2f}%".format((headshots/1)*100)
        else: hps = "{:.2f}%".format((headshots/hits)*100)
        if nukes == 0: gpn = "{:.2f}".format(played/1)
        else: gpn = "{:.2f}".format(played / nukes)
        if daysplayed == 0: npd = "{:.2f}".format(nukes/ 1)
        else: npd = "{:.2f}".format(nukes/ daysplayed)
        if played == 0: kpg = "{:.2f}".format(kills/1)
        else: kpg = "{:.2f}".format(kills/played)
        kpm = "{:.2f}".format(float(kpg)/4)
        if loses == 0: wl = "{:.2f}".format(wins/1)
        else: wl = "{:.2f}".format(wins/loses)
        if deaths == 0: kdr = "{:.4f}".format(kills/1)
        else: kdr = "{:.4f}".format(kills / deaths)
        if kills == 0: spk = "{:.2f}".format(score/1)
        else: spk = "{:.2f}".format(score / kills)
        if played == 0: avgscore = int(score/1)
        else: avgscore = int(score / played)
        if shots == 0: accuracy = "{:.2f}%".format((hits/1)*100)
        else: accuracy = "{:.2f}%".format((hits/shots)*100)
        statsoverlay = Image.new("RGBA", (1280, 720))
        borders = Image.open("images/borders.png")

        if bgdata is None:
            bgdata = {
                'file': 'https://media.discordapp.net/attachments/856723935357173780/856731786456858684/unknown.png',
                'hd': [255, 123, 57],
                'st': [222, 222, 222],
                'mt': '#vantalizing',
                'us': [36, 36, 36],
                'ov': True
            }

        if bgdata["ov"]:
            overlay = Image.open("images/overlay.png")
            borders.paste(overlay, (0, 0), overlay)

        statsoverlay.paste(borders, (0, 0))

        # ============ DRAWING STARTS ==============
        order = [["Score", "Kills", "Deaths", "KR", "Playtime", "Nukes"],
                ["Played", "Won", "Lost", "W/L", "KDR", "Challenge"],
                ["MPK", "SPK", "GPN", "NPD", "KPM", "KPG"],
                ["Avg. Score", "Accuracy", "Headshots", "HPS", "Melee", "Wallbangs"]]
        draw = ImageDraw.Draw(statsoverlay)
        shadow = Image.new("RGBA", statsoverlay.size)
        draw2 = ImageDraw.Draw(shadow)
        font = ImageFont.truetype("images/font.ttf", 20)
        font2 = ImageFont.truetype("images/font.ttf", 40)
        font3 = ImageFont.truetype("images/font.ttf", 26)
        font4 = ImageFont.truetype("images/font.ttf", 22)

        yloc = 148
        for row in order:
            xloc = 105
            for stat in row:
                size = font4.getsize(str(stat))[0]
                draw2.text((xloc - (size / 2), yloc), str(stat), font=font4, fill=(0, 0, 0))
                xloc += 214
            yloc += 119

        yloc = 148
        for row in order:
            xloc = 105
            for stat in row:
                size = font4.getsize(str(stat))[0]
                draw.text((xloc - (size / 2), yloc), str(stat), font=font4, fill=tuple(bgdata["hd"]))
                xloc += 214
            yloc += 119
        if bgdata["file"] == "":
            bgdata["file"] = 'https://media.discordapp.net/attachments/856723935357173780/856731786456858684/unknown.png'
        if userdata["hacker"]:
            bgdata["file"] = "https://media.discordapp.net/attachments/865932222577115146/867999500252381194/image_13.png"
            bgdata['hd'] = [255, 121, 121]
            bgdata['st'] = [183, 183, 183]
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(bgdata["file"]) as r:
                    imgtype = bgdata['file'].lower()[-3:]
                    if r.status == 200:
                        with open(f"images/{ctx.author.id}.{imgtype}", 'wb') as f:
                            f.write(await r.read())
                    else:
                        raise ValueError
                    bgimage = Image.open(f"images/{ctx.author.id}.{imgtype}")
        except Exception as error:
            await bot.database.bgdata.fine_one_and_update(
                { 'ign': ign },
                { '$set': { 'file': '' } }
            )
            await ctx.message.clear_reaction(loading)
            return await ctx.reply(f"Background Corrupted. It is auto-removed. Please set again using `v.pbg`")
        if imgtype == "png":
            bgimage = bgimage.convert("RGBA").resize((1280, 720))
        hours, remainder = divmod(int(timeplayed), 3600)
        minutes, seconds = divmod(remainder, 60)
        days, hours = divmod(hours, 24)
        order = [[score, kills, deaths, kr, f"{days}d {hours}h {minutes}m", nukes],
                [played, wins, loses, wl, kdr, challenge],
                [mpk, spk, gpn, npd, kpm, kpg],
                [avgscore, accuracy, headshots, hps, melee, wallbangs]]

        if challenge > 20:
            fill = (255, 43, 43)
        elif challenge > 15:
            fill = (228, 70, 255)
        elif challenge > 10:
            fill = (255, 130, 58)
        else:
            fill = (36, 36, 36)
        user = await bot.database.links.find_one({ 'main': re.compile(ign, re.IGNORECASE) })
        if user:
            userid = user['id']
            isIncognito = (await bot.getUserData(userid) or {}).get('incognito', False)
            if not isIncognito:
                user = bot.get_user(userid) or await bot.fetch_user(userid)
                if user:
                    user = f"{user.name}#{user.discriminator}"
                else:
                    user = "Deleted User#0000"
            else:
                user = "???"
        else:
            user = "???"
        
        yloc = 191
        for row in order:
            xloc = 104
            for stat in row:
                size = font.getsize(str(stat))[0]
                draw2.text((xloc-(size/2), yloc), str(stat), font=font, fill=(0,0,0))
                xloc += 214
            yloc += 119

        shadow = shadow.filter(ImageFilter.GaussianBlur(radius=2))
        shadow = shadow.filter(ImageFilter.GaussianBlur(radius=4))
        frm = []
        if imgtype == "png":
            bgimage = Image.alpha_composite(bgimage, shadow)
        else:
            for fr in ImageSequence.Iterator(bgimage):
                fr = fr.convert("RGBA")
                fr = fr.resize((1280, 720))
                frm.append(Image.alpha_composite(fr, shadow))

        yloc = 191
        for row in order:
            xloc = 104
            for stat in row:
                size = font.getsize(str(stat))[0]
                draw.text((xloc - (size / 2), yloc), str(stat), font=font, fill=tuple(bgdata["st"]))
                xloc += 214
            yloc += 119
        rank = userdata["clanRank"]
        if rank == 1:
            clancolor = (162, 255, 74)
        elif rank <= 3:
            clancolor = (50, 50, 50)
        elif rank <= 10:
            clancolor = (255, 50, 50)
        elif rank <= 20:
            clancolor = (255, 255, 70)
        elif rank <= 30:
            clancolor = (224, 64, 255)
        elif rank <= 50:
            clancolor = (46, 155, 254)
        else:
            clancolor = (180, 180, 180)
        if clan == "VIP":
            clancolor = (68, 255, 25)
        elif clan == "DEV":
            clancolor = (25, 191, 255)
        draw.text((1173-font3.getsize(bgdata['mt'])[0], 655), bgdata["mt"], fill=tuple(bgdata.get("bt", [0,0,0])), font=font3)
        draw.text((35, 32), str(level), fill=fill, font=font2)
        draw.text((65+font2.getsize(str(level))[0], 32), str(username), fill=tuple(bgdata["us"]), font=font2)
        draw.text((85+font2.getsize(str(level))[0]+font2.getsize(str(username))[0], 32), f"[{clan}]", fill=clancolor, font=font2)
        draw.text((120, 655), user, font=font3, fill=tuple(bgdata.get("bt", [0,0,0])))
        dis_logo = Image.open("images/discord.png").resize((69, 69))
        statsoverlay.paste(dis_logo, (30, 639))

        image_bytes = BytesIO()
        if imgtype == "png":
            bgimage = Image.alpha_composite(bgimage, statsoverlay)
            bgimage.save(image_bytes, 'PNG')
            image_bytes.seek(0)
        else:
            final = []
            for i in frm:
                final.append(Image.alpha_composite(i, statsoverlay))
            final[0].save(
                image_bytes,
                format='GIF',
                save_all=True,
                append_images=final[1:],
                loop=0
            )
            image_bytes.seek(0)
        statsoverlay.close()
        bgimage.close()
        await ctx.message.clear_reaction(loading)
        file=discord.File(image_bytes, filename=f"profile.{imgtype}")
        if not via:
            await ctx.send(file=file)
        else:
            return file
    
    @commands.command(aliases=["incog"])
    async def incognito(
        self,
        ctx: commands.Context,
    ):
        data = await bot.getUserData(ctx.author.id) or {}
        if data.get('incognito', False):
            data["incognito"] = False
            embed=discord.Embed(description=f"{economysuccess} You are **no longer** in incognito mode", color=success_embed)
        else:
            data["incognito"] = True
            embed = discord.Embed(description=f"{economysuccess} You are in incognito mode", color=success_embed)
        
        await bot.database.userdata.update_one({"id": ctx.author.id}, {"$set": data}, upsert=True)
        await ctx.reply(embed=embed)
    
    @commands.command()
    async def main(self,
        ctx: commands.Context,
        *,
        ign: str
    ):
        d = await bot.getAccounts(ctx.author.id)
        if d is None:
            return await ctx.send("You have no accounts linked. Use `v.link <ign>` to link an account first")
        if ign.lower() not in [x.lower() for x in d["all"]]:
            return await ctx.send("This account isnt linked to you")

        d["main"] = ign
        await bot.database.links.update_one({"id": ctx.author.id}, {"$set": d})
        embed=discord.Embed(description=f"{economysuccess} Done! `{ign}` is now your main account", color=success_embed)
        await ctx.reply(embed=embed)
    
    @commands.command()
    async def alts(
        self,
        ctx: commands.Context,
        mem: discord.Member = None
    ):
        aut = mem or ctx.author
        d = await bot.getAccounts(aut.id)
        if d is None:
            return await ctx.send("You have no accounts linked. Use `v.link <ign>` to link an account first")
        else:
            isIncognito = (await bot.getUserData(aut.id) or {}).get('incognito', False)
            if isIncognito and ctx.author.id != mem.id:
                return await ctx.send("You have no accounts linked. Use `v.link <ign>` to link an account first")
        
        altslist = "\n".join(list(set(d["all"])))
        s = f"```css\n{altslist}```"
        embed= discord.Embed(title="Linked Accounts", description=s, color=embedcolor)
        await ctx.send(embed=embed)

    @commands.command()
    async def pbg(
        self,
        ctx: commands.Context,
        *,
        ign: str = None
    ):
        if ign is not None and ctx.author.id in devs:
            ign = {"main": ign}
        else:
            ign = await bot.getAccounts(ctx.author.id)
        if ign is None:
            return await ctx.reply("You need to be linked to get a custom background")

        ign = ign["main"].lower()
        if bot.apidown:
            return await apiError(ctx)

        if ign not in bot.vntapeeps and ign not in bot.excl:
            return await ctx.send(
                "Only VNTA clan members or people with exculsive permission from developer can use this command"
            )

        if ign in bot.already:
            return await ctx.reply("Someone is already editing this background. Please wait")

        bot.already.append(ign)
        defaultBgData = {
            "file":"",
            "hd":[0,0,0],
            "st":[222, 222, 222],
            "mt":"",
            "us":[30, 30, 36],
            "ov":True
        }
        bot.unsaved[ign] = copy.copy(await bot.getBgData(ign) or defaultBgData)
        await self.sendnew(ctx, bot.unsaved[ign], ign)
        def check(msg):
            return msg.author == ctx.author and msg.channel == ctx.channel
        try:
            while True:
                mainmsg = await bot.wait_for("message", check=check, timeout=180)
                msgc = mainmsg.content.lower()
                if msgc == "cancel":
                    await mainmsg.add_reaction(economysuccess)
                    bot.already.remove(ign)
                    break
                elif msgc == "save":
                    await bot.database.bgdata.update_one({"id": ign}, {"$set": bot.unsaved[ign]}, upsert=True)
                    bot.already.remove(ign)
                    await ctx.send(f"{economysuccess} Saved Successfully!")
                elif msgc == "modify 1":
                    try:
                        embed = discord.Embed(
                            description="Upload the `PNG` file from your PC to set as background.\n"
                                        "**Dont send a link to the image! Upload the file**",
                            color=embedcolor
                        )
                        embed.set_footer(text="Recommended Size: 1280x720")
                        await ctx.send(embed=embed)

                        msg = await bot.wait_for("message", check=check, timeout=180)
                        try:
                            image = msg.attachments[0].url
                            if image[-3:].lower() not in ["png"]:
                                await ctx.send(f"{ctx.author.mention} The image should be `.PNG` file only! For `.GIF`s, ask AwesomeSam ;)")
                                continue
                            else:
                                async with aiohttp.ClientSession(auto_decompress=False) as session:
                                    async with session.get(image) as r:
                                        if r.status == 200:
                                            with open(f"images/{ctx.author.id}.{image[-3:].lower()}", 'wb') as f:
                                                f.write(await r.read())
                                            bgfile = await bot.get_channel(856723935357173780).send(
                                                file=discord.File(
                                                    f"images/{ctx.author.id}.{image[-3:].lower()}",
                                                    filename=f"{ctx.author.id}.{image[-3:].lower()}"
                                                )
                                            )
                                            bot.unsaved[ign]["file"] = bgfile.attachments[0].url
                                        else:
                                            raise Exception
                                    await ctx.send(f"Done!")
                                    await self.sendnew(ctx, bot.unsaved[ign], ign)
                        except Exception as e:
                            print(e)
                            await ctx.send("Bot didnt detect any attachments. Make sure you upload the image from your device!")
                    except asyncio.TimeoutError:
                        pass
                elif msgc in ["modify 2", "modify 3", "modify 5", "modify 6"]:
                    try:
                        embed = discord.Embed(
                            description="Enter the `R, G, B` code or `#Hex` value of the color.\n"
                                        "Trouble choosing? [Click Here](https://htmlcolorcodes.com/)\n",
                            color=embedcolor
                        )
                        await ctx.send(embed=embed)
                        try:
                            msg = await bot.wait_for("message", check=check, timeout=180)
                            if msg.content[0] == "#":
                                h = msg.content.lower()
                                r, g, b = ImageColor.getcolor(h, "RGB")
                            else:
                                r, g, b = msg.content.replace(" ", "").split(",")
                            r = int(r)
                            g = int(g)
                            b = int(b)
                            if (r>255 or r<0) or (g>255 or g<0) or (b>255 or b<0): raise ValueError

                            types = {2: "hd", 3: "st", 5: "us", 6:"bt"}
                            bot.unsaved[ign][types[int(msgc[-1])]] = [r, g, b]
                            await ctx.send("Done!")
                            await self.sendnew(ctx, bot.unsaved[ign], ign)
                        except:
                            await ctx.send("Incorrect `R, G, B` / `#Hex` code. Please retry")
                    except asyncio.TimeoutError:
                        pass
                elif msgc == "modify 4":
                    try:
                        embed = discord.Embed(
                            description="Enter the motto for your background. Make sure it is not NSFW type",
                            color=embedcolor
                        )
                        embed.set_footer(text="Type 'default' to remove")
                        await ctx.send(embed=embed)
                        try:
                            msg = await bot.wait_for("message", check=check, timeout=180)
                            if msg.content.lower() != "default":
                                bot.unsaved[ign]["mt"] = msg.content
                            else:
                                bot.unsaved[ign]["mt"] = ""
                            await ctx.send("Done!")
                            await self.sendnew(ctx, bot.unsaved[ign], ign)
                        except:
                            await ctx.send(f"Unknown error occured. Please contact {bot.dev}")
                    
                    except asyncio.TimeoutError:
                        pass

        except asyncio.TimeoutError:
            bot.already.remove(ign)

    
    @commands.command()
    async def cbg(
        self,
        ctx: commands.Context
    ):
        await self.pbg(ctx, ign='vntasam123')
    
    async def sendnew(self, ctx: commands.Context, data: dict, ign: str):
        curset = f"""
1. Headings Color- {data['hd']}
2. Stats Color- {data['st']}
3. Motto Text- {data['mt']}
4. Username Color- {data['us']}
5. Bottom Text Color- {data.get('bt', [0,0,0])}"""
        embed = discord.Embed(
            title="⚙️ VNTA Profile Background",
            description=f"""
Current Settings:
```less\n{curset}```
__Choose the below options to modify the background:__\n
`modify 1` - Change background image
`modify 2` - Change headings color
`modify 3` - Change stats color
`modify 4` - Change background motto
`modify 5` - Change username color
`modify 6` - Change bottom text color""",
            color=embedcolor
        )
        embed.set_image(url=f"attachment://profile.{data['file'].lower()[-3:]}")
        file = await self.profile(ctx, ign={"main":ign}, via=True)
        embed.set_footer(text="Type 'save' to save background\nType 'cancel' to cancel all changes")
        await ctx.send(embed=embed, file=file)

class LinkAccount(discord.ui.View):
    def __init__(
        self,
        userid: int,
        ign: str,
        flag: str
    ):
        super().__init__()
        self.userid = userid
        self.ign = ign
        self.flag = flag
        self.msg = None
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id == self.userid:
            return True
        else:
            await interaction.response.send_message(
                'You cannot control commands used by others.',
                ephemeral=True
            )
            return False

    @discord.ui.button(label='Done', style=discord.ButtonStyle.green)
    async def done(self, button, interaction: discord.Interaction):
        await interaction.response.defer()
        asyncio.create_task(self.msg.edit(view=None))
        apiReq = VntabotAPI()
        ign = self.ign
        data = await apiReq.get(ign)
        if data.status != 200:
            await apiError(interaction.channel)
            await apiReq.end()
            return
        else:
            data = await data.json()
            await apiReq.end()
        
        oldflag = data["data"]["stats"].get("flg", "a")
        if oldflag != self.flag:
            return await interaction.followup.send(
                f"{interaction.user.mention} The flag change wasn't detected. Make sure to stick to the end of the match\n"
                f"**Note: If you are linked with GameBot, ask a staff to forcelink you**"
            )
        # link account to user
        t = await bot.getAccounts(interaction.user.id)
        if t:
            t["all"] = list(set(t["all"]))
            if ign.lower() in [x.lower() for x in t["all"]]:
                return await interaction.followup(f"You are already linked with `{ign}`")
            t["all"].append(ign)
        else:
            t = {
                "all": [ign],
                "main": ign
            }
        await bot.database.links.update_one({'id': interaction.user.id}, {'$set': t}, upsert=True)
        await self.msg.edit(f'{economysuccess} **{interaction.user.name}** is now linked with **{ign}**', embed=None)
    
    @discord.ui.button(label='Cancel', style=discord.ButtonStyle.red)
    async def cancel(self, button, interaction: discord.Interaction):
        await interaction.response.send_message(
            f'{economyerror} **{interaction.user.name}** cancelled the linking process'
        )
        await self.msg.edit(view=None)


def setup(bot_: VntaBot):
    bot_.add_cog(Profile(bot_))