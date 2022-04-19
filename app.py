import os
from re import A
from quart import Quart, g, session, redirect, request, url_for, render_template
from requests_oauthlib import OAuth2Session
import winerp

OAUTH2_CLIENT_ID = "853971223682482226"
OAUTH2_CLIENT_SECRET = os.getenv('OAUTH2_CLIENT_SECRET')
OAUTH2_REDIRECT_URI = 'https://vnta.herokuapp.com/callback'

API_BASE_URL = 'https://discordapp.com/api'
AUTHORIZATION_BASE_URL = API_BASE_URL + '/oauth2/authorize'
TOKEN_URL = API_BASE_URL + '/oauth2/token'


app = Quart(__name__)
app.debug = True
app.config['SECRET_KEY'] = OAUTH2_CLIENT_SECRET

client = winerp.Client('server', port=8080)

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

def token_updater(token):
    session['oauth2_token'] = token

@app.before_first_request
async def start_ipc_client():
    print('Webserver is starting the IPC client.')
    try:
        await client.start()
        await client.wait_until_ready()
    except Exception as e:
        print(f'Webserver failed to start the IPC client.:\n\n {e}')

def make_session(token=None, state=None, scope=None):
    return OAuth2Session(
        client_id=OAUTH2_CLIENT_ID,
        token=token,
        state=state,
        scope=scope,
        redirect_uri=OAUTH2_REDIRECT_URI,
        auto_refresh_kwargs={
            'client_id': OAUTH2_CLIENT_ID,
            'client_secret': OAUTH2_CLIENT_SECRET,
        },
        auto_refresh_url=TOKEN_URL,
        token_updater=token_updater
    )


@app.route('/')
async def index():
    scope = request.args.get(
        'scope',
        'identify connections'
    )
    discord = make_session(scope=scope.split(' '))
    authorization_url, state = discord.authorization_url(AUTHORIZATION_BASE_URL)
    session['oauth2_state'] = state
    return redirect(authorization_url)


@app.route('/callback')
async def callback():
    data = await request.values
    if data.get('error'):
        return data['error']
    discord = make_session(state=session.get('oauth2_state'))
    token = discord.fetch_token(
        TOKEN_URL,
        client_secret=OAUTH2_CLIENT_SECRET,
        authorization_response=request.url
    )
    session['oauth2_token'] = token
    return redirect(url_for('.me'))


@app.route('/me')
async def me():
    discord = make_session(token=session.get('oauth2_token'))
    user = discord.get(API_BASE_URL + '/users/@me').json()
    connections = discord.get(API_BASE_URL + '/users/@me/connections').json()
    
    await client.inform({'user': user, 'connections': connections}, ['bot'])
    return render_template("success.html")

@app.route("/ping")
async def pong():
    return "Pong", 200

if __name__ == '__main__':
    app.run()
