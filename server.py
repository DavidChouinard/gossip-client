import bottle

import subprocess

import re

@bottle.route('/')
def index():
    ip = bottle.request.get('REMOTE_ADDR')
    print ip
    subprocess.call(['ping', '-c', '1', ip])
    response = subprocess.check_output(["arp", "-n", ip])
    search = re.search(r"(([a-f\d]{1,2}\:){5}[a-f\d]{1,2})", response)

    if search is None:
        return "Mac address not found"
    else:
        mac = search.groups()[0]
        return bottle.template("Your mac address is: {{mac}}", mac=mac)

def start():
    print("* starting server")
    bottle.run(host='0.0.0.0', port=80)
