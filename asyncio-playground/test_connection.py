
import asyncio
import json
import ssl

import websockets

token = ''
async def connect():
	url = 'wss://192.168.0.208:8002/api/v2/channels/samsung.remote.control?name=python-async&token={}'

	ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
	ssl_context.check_hostname = False
	ssl_context.verify_mode = ssl.CERT_NONE

	async with websockets.connect(url, ssl=ssl_context) as websocket:
		raw_msg = await websocket.recv()
		msg = json.loads(raw_msg)
		if 'token' in msg:
			token = msg['token']
			print('Got Token {}'.format(token))

asyncio.get_event_loop().run_until_complete(connect())
