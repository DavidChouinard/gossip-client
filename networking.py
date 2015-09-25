#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import subprocess
import socket
import random

import time
import threading
import retrying
import tinydb

import netifaces
import netaddr
import nmap
from scapy.all import sniff, Dot11

RSSI_THRESHOLD = int(os.environ.get("RSSI_THRESHOLD", -60))
DEVNULL = open(os.devnull, 'wb')

db = tinydb.TinyDB('db/db.json')

def start_device_discovery():
    global my_mac

    my_mac = [get_interface_mac('wlan0')]

    if 'wlan1' in netifaces.interfaces():
        my_mac.append(get_interface_mac('wlan1'))

        threading.Thread(target=scan_network, args=('wlan1',)).start()
        start_sniffing('wlan0')

def get_interface_mac(interface):
    return netifaces.ifaddresses(interface)[netifaces.AF_LINK][0]['addr']

@retrying.retry(wait_exponential_multiplier=1000, stop_max_attempt_number=5)
def start_sniffing(interface):
    #result = subprocess.call(['iw', 'phy', 'phy0', 'interface', 'add', 'mon0', 'type', 'monitor'])
    result = subprocess.call("sudo ifconfig " + interface + " down; sudo iwconfig " + interface + " mode monitor;", shell=True)

    assert(result == 0)

    threading.Timer(4.0, sniff, [], {'iface': 'wlan0', 'prn': packet_sniffed, 'stop_filter': keep_sniffing, 'store': 0}).start()
    threading.Thread(target=channel_hopper, args=('wlan0',)).start()

stop_sniff = False
def keep_sniffing(_):
    global stop_sniff
    return stop_sniff

def stop_sniffing(_, __):
    print "* stopped sniffing"
    global stop_sniff
    stop_sniff = True
    exit(0)

def channel_hopper(interface):
    while True:
        time.sleep(1)
        channel = random.randrange(1,14)
        subprocess.call(["iwconfig", interface, "channel", str(channel)])

def packet_sniffed(pkt):
    if pkt.haslayer(Dot11) and pkt.type == 0 and pkt.subtype == 4:
        mac = pkt.addr2
        rssi = (ord(pkt.notdecoded[-4:-3])-256)
        if mac not in my_mac and rssi >= RSSI_THRESHOLD:
            data = {'rssi': rssi, 'mac': mac, 'seen': int(time.time())}

            if not os.environ.get("RECAP_ENV") == "PRODUCTION":
                print ("* captured probe: " + str(data))

            insert_or_update_device(data)

def scan_network(interface):
    print("* starting network scan for devices")

    ifaces = netifaces.ifaddresses(interface)

    if socket.AF_INET not in ifaces:
        # we don't have an IP address, try again in an hour
        threading.Timer(60*60, scan_network, [interface]).start()
        return

    ipinfo = ifaces[socket.AF_INET][0]
    cidr = netaddr.IPNetwork('%s/%s' % (ipinfo['addr'], ipinfo['netmask']))

    nm = nmap.PortScanner()
    nm.scan(hosts=str(cidr), arguments='-sn -n -e ' + interface)
    for host in nm.all_hosts():
        data = {'ip': nm[host]['addresses']['ipv4'], 'mac': nm[host]['addresses']['mac'].lower()}

        hostname = get_hostname(nm[host]['addresses']['ipv4'], nm[host]['hostnames'])
        if hostname is not None:
            data["hostname"] = hostname

            if not os.environ.get("RECAP_ENV") == "PRODUCTION":
                print("* found hostname " + str(data))

        insert_or_update_device(data)

    # scan again at some random time tomorrow
    interval = random.randrange(12*60*60, 36*60*60)
    threading.Timer(interval, scan_network, [interface]).start()


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
    devices = db.search(tinydb.where('seen') >= int(time.time()) - 60*15)
    return map(lambda device: {k: v for k, v in device.items() if k in ['mac', 'vendor', 'hostname', 'useragent']}, devices)

def get_cached_mac_from_ip(ip):
    devices = db.search((tinydb.where('ip') == ip) & (tinydb.where('updated') >= int(time.time()) - 60*60))
    if devices:
        return devices[0]['mac']
    else:
        return None

def insert_or_update_device(data):
    data['updated'] = int(time.time())
    data['mac'] = data['mac'].lower()

    if len(db.search(tinydb.where('mac') == data['mac'])) >= 1:
        db.update(data, tinydb.where('mac') == data['mac'])
    else:
        try:
            data['vendor'] = netaddr.EUI(data['mac']).oui.registration(0).org
        except netaddr.NotRegisteredError:
            pass

        db.insert(data)

