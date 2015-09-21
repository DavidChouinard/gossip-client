#!/usr/bin/env python
# -*- coding: utf-8 -*-

import bottle

import os
import subprocess
import requests

import dateutil.parser
import re

import networking

import sys
reload(sys)
sys.setdefaultencoding('utf-8')

bottle.TEMPLATE_PATH[:] = ['templates']

@bottle.route('/')
@bottle.jinja2_view('register.html')
def index():
    mac = get_mac_address(bottle.request.get('REMOTE_ADDR'))

    if mac is None:
        return {'error': "Can't detect your MAC address from this page. Sorry. This is a beta product, message david@davidchouinard.com for help.", 'hide_form': True}
    else:
        r = requests.get('https://gogossip.herokuapp.com/devices/' + mac, params={"base_id": os.environ["BASE_ID"]}, headers={'Accept': 'application/json'})

        if r.status_code >= 200 and r.status_code <= 299:
            context = r.json()
            context['is_registered'] = True
            context['snippets'] = get_snippets(mac)
            return context
        else:
            return {}

@bottle.post('/')
@bottle.jinja2_view('register.html')
def register_device():
    mac = get_mac_address(bottle.request.get('REMOTE_ADDR'))

    if mac is None:
        return {'error': "Can't detect your MAC address from this page. Sorry. This is a beta product, message david@davidchouinard.com for help.", 'hide_form': True}

    data = {
        'user':{'email': bottle.request.forms.getunicode('email'), 'name': bottle.request.forms.getunicode('name')},
        'device': {'mac': mac, 'useragent': bottle.request.get('HTTP_USER_AGENT')}
    }

    if data['user']['email'] is None:
        return {'error': "Email is required"}

    r = requests.post('https://gogossip.herokuapp.com/devices', json=data, headers={'Accept': 'application/json'})

    if r.status_code >= 200 and r.status_code <= 299:
        context = r.json()
        context.update(data['user'])
        context['is_registered'] = True
        context['snippets'] = get_snippets(mac)
        return context
    else:
        context = {'error': "Can't connect to server to register your device. Sorry. This is a beta product, message david@davidchouinard.com for help."}
        context.update(data['user'])
        return context

@bottle.route('/assets/<path:path>')
def static(path):
    return bottle.static_file(path, root='assets')

def get_mac_address(ip):
    cache = networking.get_cached_mac_from_ip(ip)
    if cache is not None:
        return cache

    subprocess.call(['ping', '-c', '1', ip])
    response = subprocess.check_output(["arp", "-n", ip])
    search = re.search(r"(([a-f\d]{1,2}\:){5}[a-f\d]{1,2})", response)

    if search is None:
        return None
    else:
        mac = search.groups()[0]
        networking.insert_or_update_device({'mac': mac, 'ip': ip})
        return mac

def get_snippets(mac):
    r = requests.get('https://gogossip.herokuapp.com/snippets', params={"base_id": os.environ["BASE_ID"], "mac": mac}, headers={'Accept': 'application/json'})

    if r.status_code >= 200 and r.status_code <= 299:
        data = r.json()
        for i in xrange(len(data)):
            data[i]['transcription_html'] = " ".join(map(lambda s: s['alternatives'][0]['transcript'], data[i]['transcription'])).strip()
            if data[i]['transcription_html'] == "":
                data[i]['transcription_html'] = "—"

        return data
    else:
        return []

def format_date(isodate):
    return dateutil.parser.parse(isodate).strftime('%B %-d, %Y')

bottle.Jinja2Template.defaults['format_date'] = format_date

def start_server():
    print("* starting server")

    if "RECAP_ENV" in os.environ and os.environ["RECAP_ENV"] == "PRODUCTION":
        bottle.run(host='0.0.0.0', port=80, server='cherrypy', quiet=True, debug=False)
    else:
        bottle.run(host='0.0.0.0', port=80, server='cherrypy', debug=True)
