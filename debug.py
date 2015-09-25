import networking
import sys

from pprint import pprint

def main():
    if len(sys.argv) == 1 or sys.argv[1] == "proximity":
        pprint(networking.devices_in_proximity())
    else:
        print("Unknown debug command")

if __name__ == "__main__":
    main()
