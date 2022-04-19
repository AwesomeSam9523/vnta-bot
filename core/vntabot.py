from typing import Optional
from discord.ext import commands
import discord
import time
import os
from .database import Database

__all__ = [
    'VntaBot',
]

class VntaBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix=["V.", "v."], case_insensitive=True, intents=intents)
        self.persistent_views_added = False
        self.session = None
        self.apikey = None
        self.remove_command("help")
        self.twitchapi = {"expiry": 0}
        self.unsaved = {}
        self.pendings = {}
        self.already = []
        self.vntapeeps = []
        self.excl = ['awesomesam']
        self.dcmds = []
        self.muted = []
        self.staff = [771601176155783198]
        self.dev: discord.User = None
        self.linkinglogs: discord.TextChannel = None
        self.starboards: discord.TextChannel = None
        self.interlist = []
        self.uptime = time.time()
        self.reqs = 0
        self.pause = False
        self.cwpause = True
        self.usage_ = True

        if os.path.exists("C:"):
            self.beta = True
        else:
            self.beta = False

        self.webworking = False
        self.apidown = False
        self.database = Database()
    
    async def on_ready(self):
        self.dev = self.get_user(771601176155783198)
        self.linkinglogs = self.get_channel(861463678179999784)
        self.starboards = self.get_channel(874717466134208612)

        
    
    async def getAccounts(self, id: int) -> Optional[dict]:
        return await self.database.links.find_one({ 'id': id })
    
    async def getBgData(self, ign: str) -> Optional[dict]:
        return await self.database.bgdata.find_one({ 'ign': ign.lower() })
    
    async def getUserData(self, id: int) -> Optional[dict]:
        return await self.database.userdata.find_one({ 'id': id })
    
    async def getReminders(self, id: int) -> Optional[dict]:
        return await self.database.reminders.find({ 'id': id }).to_list(length=None)
