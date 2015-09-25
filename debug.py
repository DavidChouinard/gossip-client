import networking

import sys
import tinydb

from pprint import pprint

db = tinydb.TinyDB('db/db.json')

def main():
    if len(sys.argv) == 1 or sys.argv[1] == "proximity":
        pprint(networking.devices_in_proximity())
    elif sys.argv[1] == "hostnames":
        pprint(db.search(tinydb.where('hostname')))
    else:
        print("Unknown debug command")

if __name__ == "__main__":
    main()
