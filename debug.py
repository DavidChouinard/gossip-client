import networking

import sys
import tinydb

from pprint import pprint

def main():
    if len(sys.argv) == 1 or sys.argv[1] == "proximity":
        pprint(networking.devices_in_proximity())
    elif sys.argv[1] == "hostnames":
        db = tinydb.TinyDB('db/db.json')
        pprint(db.search(tinydb.where('hostname')))
    else:
        print("Unknown debug command")

if __name__ == "__main__":
    main()
