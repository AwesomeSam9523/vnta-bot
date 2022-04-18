import discord
from discord.ext import commands
from .consts import economyerror, error_embed

__all__ = ['apiError']

async def apiError(ctx: commands.Context):
    embed = discord.Embed(
        title=f"{economyerror} Error",
        description="API didnt respond in time",
        color=error_embed
    )
    embed.set_footer(text="Please try again later")
    return await ctx.send(embed=embed)

async def noProfileFound(ctx: commands.Context):
    embed = discord.Embed(
        title=f"{economyerror} No profile found.",
        color=error_embed
    )
    return await ctx.send(embed=embed)

async def notLinkedYet(ctx: commands.Context):
    embed = discord.Embed(
        description="You aren't linked yet. Use `v.link <ign>` to get linked.\nOr use `v.pf <ign>` to view",
        color=error_embed
    )
    return await ctx.reply(embed=embed)

async def userNotLinkedYet(ctx: commands.Context):
    embed = discord.Embed(
        description="User not linked yet.",
        color=error_embed
    )
    return await ctx.reply(embed=embed)