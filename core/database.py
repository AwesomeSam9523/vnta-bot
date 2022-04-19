from motor.motor_asyncio import *
import os

class Database:
    def __init__(self):
        self._database_connecter = AsyncIOMotorClient(os.getenv('MONGO'))
        self._database = self._database_connecter['vnta']
    
    def __getitem__(self, _name: str):
        return self._database[_name]
    
    @property
    def links(self):
        return self._database['links']
    
    @property
    def bgdata(self):
        return self._database['bgdata']
    
    @property
    def userdata(self):
        return self._database['userdata']
    
    @property
    def reminders(self):
        return self._database['reminders']
    
    @property
    def staff(self):
        return self._database['staff']
    
    @property
    def socials(self):
        return self._database['socials']
    
    @property
    def posts(self):
        return self._database['posts']
    
    @property
    def starboard(self):
        return self._database['starboard']
