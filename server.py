#!/usr/bin/env python
# -*- coding: utf-8 -*-

import bottle

import subprocess

import re

import sys
reload(sys)
sys.setdefaultencoding('utf-8')

bottle.TEMPLATE_PATH[:] = ['templates']

@bottle.route('/')
@bottle.jinja2_view('register.html')
def index():
    mac = get_mac_address(bottle.request.get('REMOTE_ADDR'))

    if mac is None:
        return {'error': "Error: Can't detect your MAC address from this page. <br>I`m sorry: this is a beta product, message david@davidchouinard.com for help.", 'hide_form': True}
    else:
        return {'mac': mac}

@bottle.post('/')
@bottle.jinja2_view('register.html')
def register_device():
    mac = get_mac_address(bottle.request.get('REMOTE_ADDR'))

    if mac is None:
        return {'error': "Error: Can't detect your MAC address from this page. <br>I`m sorry: this is a beta product, message david@davidchouinard.com for help."}

    name = bottle.request.forms.get('name')
    email = bottle.request.forms.get('email')

    print name, email

    if email is None:
        return {'error': "Email is required"}

    return {'success': "You'll get new snippets from now on 👻"}

@bottle.route('/assets/<path:path>')
def static(path):
    return bottle.static_file(path, root='assets')

def get_mac_address(ip):
    subprocess.call(['ping', '-c', '1', ip])
    response = subprocess.check_output(["arp", "-n", ip])
    search = re.search(r"(([a-f\d]{1,2}\:){5}[a-f\d]{1,2})", response)

    if search is None:
        return None
    else:
        return search.groups()[0]

def start():
    print("* starting server")
    bottle.run(host='0.0.0.0', port=80)
