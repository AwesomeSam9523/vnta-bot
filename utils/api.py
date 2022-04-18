import aiohttp
from urllib.parse import quote as URL_quoater

class VntabotAPI:
    def __init__(self, type=1):
        if type == 1:
            self.url = 'https://kr.vercel.app/api/profile?username='
        else:
            self.url = 'https://kr.vercel.app/api/clan?clan='
        self.session = aiohttp.ClientSession()
        self._response = None
    
    @property
    def response(self):
        '''
        Returns back `aiohttp.ClientResponse` against the last request.
        '''
        return self._response

    @property
    def headers(self):
        headers = {
            'method': 'GET',
            'accept': 'application/json, text/plain, */*',
            'scheme': 'https',
            'User-Agent': 'Mozilla/5.0 Chrome/92.0.4515.107 Safari/537.36 Edg/92.0.902.62',
            'From': 'vntabot@awesomesam.com',
        }
        
        return headers

    async def get(
        self,
        query: str,
        **kwargs
    ):
        _path = URL_quoater(query, safe='')
        url: str = kwargs.pop('url', self.url)
        self._response = await self.session.get(url + _path, headers=self.headers)
        return self._response
    
    async def end(self):
        '''
        Marks end to the request. After this a new session will be inited.
        '''
        await self.session.close()
