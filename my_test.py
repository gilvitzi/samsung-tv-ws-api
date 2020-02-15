import sys
import os
import time

import wakeonlan

sys.path.append('../')

from samsungtvws import SamsungTVWS


from getmac import get_mac_address

ip_mac = get_mac_address(ip='192.168.0.208')
print(ip_mac)

wakeonlan.send_magic_packet(ip_mac)

# Autosave token to file 
token_file = os.path.dirname(os.path.realpath(__file__)) + '/tv-token.txt'
tv = SamsungTVWS(host='192.168.0.208', port=8002, token_file=token_file)

def handle_message(msg):
    print(msg)

def handle_app_list(msg):
    print('APP LIST len = %s' % len(msg['data']['data']))

tv.events.subscribe('*', handle_message)
tv.events.subscribe('ed.installedApp.get', handle_app_list)

tv.shortcuts().power()

app_list = tv.app_list()
tv.shortcuts().power()
tv.shortcuts().menu()
tv.shortcuts().source()
tv.shortcuts().source()
# Toggle power


#tv.shortcuts().power()

#tv.shortcuts().power()
# Power On


# Open web in browser
tv.open_browser('https://192.168.0.100:8123/lovelace/default_view')

# View installed apps (Spotify)
app_list = tv.app_list()
print(app_list)
# Open apps (Spotify)
#tv.run_app('3201606009684')

while True:
    time.sleep(1)
    app_list = tv.app_list()