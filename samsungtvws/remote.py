"""
SamsungTVWS - Samsung Smart TV WS API wrapper

Copyright (C) 2019 Xchwarze

    This library is free software; you can redistribute it and/or
    modify it under the terms of the GNU Lesser General Public
    License as published by the Free Software Foundation; either
    version 2.1 of the License, or (at your option) any later version.

    This library is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
    Lesser General Public License for more details.

    You should have received a copy of the GNU Lesser General Public
    License along with this library; if not, write to the Free Software
    Foundation, Inc., 51 Franklin Street, Fifth Floor,
    Boston, MA  02110-1335  USA

"""
import base64
import json
import logging
import threading
import time
import ssl
import websocket
from . import shortcuts
from .simple_pub_sub import SimplePubSub

_LOGGING = logging.getLogger(__name__)

class SamsungTVWS:
    _URL_FORMAT = 'ws://{host}:{port}/api/v2/channels/samsung.remote.control?name={name}'
    _SSL_URL_FORMAT = 'wss://{host}:{port}/api/v2/channels/samsung.remote.control?name={name}&token={token}'

    def __init__(self, host, token=None, token_file=None, port=8001, timeout=None, key_press_delay=1,
                 name='SamsungTvRemote'):
        self.host = host
        self.token = token
        self.token_file = token_file
        self.port = port
        self.timeout = None if timeout == 0 else timeout
        self.key_press_delay = key_press_delay
        self.name = name
        self.connection = None
        self._app_list = None
        self._app_list_updated = False
        self.listen_thread = None
        self.should_continue_listening = True
        self.events = SimplePubSub()
        self.events.subscribe('ed.installedApp.get', self._set_app_list)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def _serialize_string(self, string):
        if isinstance(string, str):
            string = str.encode(string)

        return base64.b64encode(string).decode('utf-8')

    def _is_ssl_connection(self):
        return self.port == 8002

    def _format_websocket_url(self, is_ssl=False):
        params = {
            'host': self.host,
            'port': self.port,
            'name': self._serialize_string(self.name),
            'token': self._get_token(),
        }

        if is_ssl:
            return self._SSL_URL_FORMAT.format(**params)
        else:
            return self._URL_FORMAT.format(**params)

    def _get_token(self):
        if self.token_file is not None:
            try:
                with open(self.token_file, 'r') as token_file:
                    return token_file.readline()
            except:
                return ''
        else:
            return self.token

    def _set_token(self, token):
        if self.token_file is not None:
            with open(self.token_file, 'w') as token_file:
                token_file.write(token)
        else:
            _LOGGING.info('New token %s', token)

    def _set_app_list(self, new_app_list):
        self._app_list = new_app_list
        self._app_list_updated = True

    def _ws_send(self, payload):
        if self.connection is None:
            self.connect()

        self.connection.send(payload)
        time.sleep(self.key_press_delay)

    def connect(self):
        if self.connection:
            # someone else already created a new connection
            return

        is_ssl = self._is_ssl_connection()
        url = self._format_websocket_url(is_ssl)
        sslopt = {'cert_reqs': ssl.CERT_NONE} if is_ssl else {}

        _LOGGING.debug('WS url %s', url)

        self.connection = websocket.create_connection(
            url,
            self.timeout,
            sslopt=sslopt
        )

        response = json.loads(self.connection.recv())

        if response.get('data') and response.get('data').get('token'):
            token = response.get('data').get('token')
            _LOGGING.debug('Got token %s', token)
            self._set_token(token)

        if response['event'] != 'ms.channel.connect':
            self.close()
            raise Exception(response)

        self._do_after_connect()
        
    def _start_listening(self):
        self.listen_thread = threading.Thread(target=self._listen_to_messages_loop)
        self.listen_thread.start()

    def _listen_to_messages_loop(self):
        if not self.connection:
            self.connect()

        while self.connection and self.should_continue_listening:
            raw_msg = None
            try:
                raw_msg = self.connection.recv()
                msg = json.loads(raw_msg)
                if 'event' in msg:
                    topic = msg['event']
                    data = msg['data'] if 'data' in msg else None
                    self.events.publish(topic, data)
                else:
                    self.events.publish('*', msg)

            except ValueError as ex:
                print("Error parsing message %s. Error: %s", raw_msg, ex)
            except Exception as ex:
                print("Error reading message from TV. Error: %s", ex)
                time.sleep(3)

    def close(self):
        if self.connection:
            self.connection.close()

        self.connection = None
        _LOGGING.debug('Connection closed.')

        self.listen_thread.join()

    def send_key(self, key, repeat=1):
        for _ in range(repeat):
            payload = json.dumps({
                'method': 'ms.remote.control',
                'params': {
                    'Cmd': 'Click',
                    'DataOfCmd': key,
                    'Option': 'false',
                    'TypeOfRemote': 'SendRemoteKey'
                }
            })

            _LOGGING.info('Sending key %s', key)
            self._ws_send(payload)

    def run_app(self, app_id, app_type='DEEP_LINK', meta_tag=''):
        payload = json.dumps({
            'method': 'ms.channel.emit',
            'params': {
                'event': 'ed.apps.launch',
                'to': 'host',
                'data': {
                    # action_type: NATIVE_LAUNCH / DEEP_LINK
                    # app_type == 2 ? 'DEEP_LINK' : 'NATIVE_LAUNCH',
                    'action_type': app_type,
                    'appId': app_id,
                    'metaTag': meta_tag
                }
            }
        })

        _LOGGING.info('Sending run app app_id: %s app_type: %s meta_tag: %s', app_id, app_type, meta_tag)
        self._ws_send(payload)

    def open_browser(self, url):
        _LOGGING.info('Opening url in browser %s', url)
        self.run_app(
            'org.tizen.browser',
            'NATIVE_LAUNCH',
            url
        )

    def update_app_list(self):
        payload = json.dumps({
            'method': 'ms.channel.emit',
            'params': {
                'event': 'ed.installedApp.get',
                'to': 'host'
            }
        })
        _LOGGING.info('request app list')
        self._ws_send(payload)

    def app_list(self):
        self._app_list_updated = False
        self.update_app_list()

        attemps_left = 10
        while not self._app_list_updated and attemps_left:
            time.sleep(1)
            attemps_left -= 1

        return self._app_list

    def shortcuts(self):
        return shortcuts.SamsungTVShortcuts(self)

    def _do_after_connect(self):
        self._start_listening()
        self.update_app_list()
