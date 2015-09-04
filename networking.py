import signal
import subprocess

import time
import threading
import tinydb

import netifaces
import netaddr
from scapy.all import sniff, Dot11

from pprint import pprint

RSSI_THRESHOLD = -60

db = tinydb.TinyDB('db/db.json')

def start_sniffing_wifi_probes():
    global my_mac_address

    if 'mon0' not in netifaces.interfaces():
        result = subprocess.call(['iw', 'phy', 'phy0', 'interface', 'add', 'mon0', 'type', 'monitor'])
        if result != 0:
            sys.stderr.write("Warning: error in putting interface in monitor mode\n")

    my_mac_address = netifaces.ifaddresses('wlan0')[netifaces.AF_LINK][0]['addr']

    signal.signal(signal.SIGINT, stop_sniffing)
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
            data = {'rssi': rssi, 'seen': int(time.time()), 'updated': int(time.time())}
            if len(db.search(tinydb.where('mac') == mac)) >= 1:
                db.update(data, tinydb.where('mac') == mac)
            else:
                data['mac'] = mac
                data['vendor'] = netaddr.EUI(mac).oui.registration(0).org
                db.insert(data)

            pprint(db.all())

def promximity_devices():
    return db.search(tinydb.where('seen') >= int(time.time()) - 60*15)
