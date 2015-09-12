#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import subprocess
import socket

import time
import threading
import retrying
import tinydb

import netifaces
import netaddr
import nmap
from scapy.all import sniff, Dot11

from pprint import pprint

RSSI_THRESHOLD = -60
DEVNULL = open(os.devnull, 'wb')

db = tinydb.TinyDB('db/db.json')

def start_device_discovery():
    global my_mac_address

    # scan_network()

    if 'mon0' not in netifaces.interfaces():
        result = subprocess.call(['iw', 'phy', 'phy0', 'interface', 'add', 'mon0', 'type', 'monitor'])
        if result != 0:
            sys.stderr.write("Warning: error in putting interface in monitor mode\n")

    my_mac_address = netifaces.ifaddresses('wlan0')[netifaces.AF_LINK][0]['addr']

    #threading.Thread(target=sniff, kwargs={'iface': 'mon0', 'prn': packet_sniffed, 'stop_filter': keep_sniffing, 'store': 0}).start()
    threading.Timer(0.5, sniff, [], {'iface': 'mon0', 'prn': packet_sniffed, 'stop_filter': keep_sniffing, 'store': 0}).start()

stop_sniff = False
def keep_sniffing(_):
    global stop_sniff
    return stop_sniff

def stop_sniffing(_, __):
    print "* stopped sniffing"
    global stop_sniff
    stop_sniff = True
    exit(0)

def packet_sniffed(pkt):
    if pkt.haslayer(Dot11) and pkt.type == 0 and pkt.subtype == 4:
        mac = pkt.addr2
        rssi = (ord(pkt.notdecoded[-4:-3])-256)
        if my_mac_address != mac and rssi >= RSSI_THRESHOLD:
            data = {'rssi': rssi, 'mac': mac, 'seen': int(time.time()), 'updated': int(time.time())}
            print ("* captured probe: " + str(data))
            insert_or_update_device(data)

def scan_network():
    print("* starting network scan for devices")
    ipinfo = netifaces.ifaddresses("wlan0")[socket.AF_INET][0]
    cidr = netaddr.IPNetwork('%s/%s' % (ipinfo['addr'], ipinfo['netmask']))

    nm = nmap.PortScanner()
    nm.scan(hosts=str(cidr), arguments='-sn -n -e wlan0')
    for host in nm.all_hosts():
        data = {'ip': nm[host]['addresses']['ipv4'], 'updated': int(time.time())}

        hostname = get_hostname(nm[host]['addresses']['ipv4'], nm[host]['hostnames'])
        if hostname is not None:
            data["hostname"] = hostname

        data['mac'] = nm[host]['addresses']['mac']

        insert_or_update_device(data)

def get_hostname(ip, fallback_hostnames):
    response = subprocess.check_output(["avahi-resolve", "--address", ip], stderr=DEVNULL)

    if response != "":
        hostname = response.split('\t')[1].strip()

        if hostname.endswith(".local"):
              hostname = hostname[:-len(".local")]
        return hostname
    elif len(fallback_hostnames) >= 1:
        return fallback_hostnames[0]['name']
    else:
        return None

def devices_in_proximity():
    devices = db.search(tinydb.where('seen') >= int(time.time()) - 60*10)
    return map(lambda device: {k: v for k, v in device.items() if k in ['mac', 'vendor', 'hostname', 'useragent']}, devices)

def get_cached_mac_from_ip(ip):
    devices = db.search((tinydb.where('ip') == ip) & (tinydb.where('updated') >= int(time.time()) - 60*60))
    if devices:
        return devices[0]['mac']
    else:
        return None

def insert_or_update_device(data):
    if len(db.search(tinydb.where('mac') == data['mac'])) >= 1:
        db.update(data, tinydb.where('mac') == data['mac'])
    else:
        try:
            data['vendor'] = netaddr.EUI(data['mac']).oui.registration(0).org
        except netaddr.NotRegisteredError:
            pass

        db.insert(data)

