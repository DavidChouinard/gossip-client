#import networking

import sys
import time
import tinydb

from pprint import pprint

db = tinydb.TinyDB('db/db.json')

def main():
    if len(sys.argv) == 1 or sys.argv[1] == "proximity":
        pprint(db.search(tinydb.where('seen') >= int(time.time()) - 60*15))
    elif sys.argv[1] == "hostnames":
        pprint(db.search(tinydb.where('hostname')))
    else:
        print("Unknown debug command")

if __name__ == "__main__":
    main()
