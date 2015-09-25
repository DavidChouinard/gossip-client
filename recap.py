#!/usr/bin/env python
# -*- coding: utf-8 -*-

import io
import os
import sys
import socket
import requests
import threading
import requests
import time
import retrying

import RPi.GPIO as GPIO

import neopixel
import gaugette.rotary_encoder

import networking
import server
import audio

from setproctitle import setproctitle

# CONSTANTS

MAIN_BUTTON_PIN = 21
UNDO_BUTTON_PIN = 5

UNDO_LED_PIN = 11

ROTARY_A_PIN = 27
ROTARY_B_PIN = 23

LOW_BATTERY_PIN = 6

# Neopixel LED strip configuration
LED_COUNT      = 24
LED_PIN        = 18
LED_FREQ_HZ    = 800000
LED_DMA        = 5
LED_BRIGHTNESS = 255
LED_INVERT     = False

COLOR = neopixel.Color(255, 128, 8)

strip = neopixel.Adafruit_NeoPixel(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS)

# SETUP

GPIO.setmode(GPIO.BCM)
GPIO.setup(MAIN_BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(UNDO_BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(LOW_BATTERY_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(UNDO_LED_PIN, GPIO.OUT)

# this fails arbitrarly hours or days out...
#GPIO.add_event_detect(MAIN_BUTTON_PIN, GPIO.BOTH, callback=button_event)

time_marker_start = 0
time_marker_size = 6

encoder = None

button_press_start = 0

def main():
    global time_marker_start

    if os.geteuid() != 0:
        exit("You need to have root privileges to run this script: rerun it using 'sudo'. Exiting.")

    if "BASE_ID" not in os.environ:
        sys.stderr.write("Error: unknown base station ID\n")
        sys.exit(1)

    setproctitle("recap")

    GPIO.output(UNDO_LED_PIN, False)

    # Startup animation
    strip.begin()
    theaterChaseAnimation()
    #threading.Thread(target=bootupAnimation).start()

    th = threading.Thread(target=networking.start_device_discovery)
    th.daemon = True
    th.start()

    th = threading.Thread(target=server.start_server)
    th.daemon = True
    th.start()

    th = threading.Thread(target=audio.start_recording)
    th.daemon = True
    th.start()

    encoder = gaugette.rotary_encoder.RotaryEncoder.Worker(ROTARY_A_PIN, ROTARY_B_PIN)
    encoder.start()

    start = time.time()
    last_button_press = 0

    try:
        while True:
            if not GPIO.input(MAIN_BUTTON_PIN) and time.clock() - last_button_press > 0.1:
                print("* button pressed")

                last_button_press = time.clock()
                snapshot = audio.get_buffer()

                threading.Thread(target=theaterChaseAnimation).start()
                threading.Thread(target=do_button_press_actions, args=(snapshot,)).start()

            time.sleep(0.1)

            #delta = encoder.get_delta()
            #if delta != 0 and GPIO.input(MAIN_BUTTON_PIN):
            #    if time_marker_start + time_marker_size + delta > LED_COUNT:
            #        time_marker_start = LED_COUNT - time_marker_size
            #    elif time_marker_start + delta < 0:
            #        time_marker_start = 0
            #    else:
            #        time_marker_start += delta
            #    updateStrip()
    except (KeyboardInterrupt, SystemExit):
        raise
    except Exception as e:
        sys.stderr.write(str(e))

    stream.stop_stream()
    stream.close()

last_button_press = 0
last_button_release = 0
def button_event(pin):
    global last_button_press, last_button_release

    if GPIO.input(pin):
        if time.clock() - last_button_release < 0.1:
            return

        last_button_release = time.clock()
        button_released()
    else:
        if time.clock() - last_button_press < 0.05:
            return

        last_button_press = time.clock()
        button_pressed()

def button_pressed():
    print("* button pressed")
    grow_marker_until_button_released()

def grow_marker_until_button_released():
    global time_marker_size

    if not GPIO.input(MAIN_BUTTON_PIN):
        if time_marker_start + time_marker_size + 1 <= LED_COUNT:
            time_marker_size += 1
            threading.Timer(0.1, grow_marker_until_button_released).start()

    updateStrip()

def button_released():
    global time_marker_start, time_marker_size

    button_press_start = time.time()
    print("* saving buffer")

    snapshot = audio.get_buffer()

    time_marker_start = 1
    time_marker_size = 6

    threading.Thread(target=theaterChaseAnimation).start()
    threading.Thread(target=do_button_press_actions, args=(snapshot,)).start()

def do_button_press_actions(snapshot):

    virtual_file = io.BytesIO('snippet')
    wf = wave.open(virtual_file, 'wb')
    wf.setnchannels(1)
    wf.setsampwidth(2)
    wf.setframerate(RATE)
    wf.writeframes(snapshot)
    wf.close()

    GPIO.output(UNDO_LED_PIN, True)
    for times in range(1, 101):
        if not GPIO.input(UNDO_BUTTON_PIN):
            print("* undo buffer catpure")
            GPIO.output(UNDO_LED_PIN, False)
            audio.clear_buffer()
            return  # undo button was pressed, don't save snippet

        if times < 95:
            time.sleep(0.1)
        else:
            GPIO.output(UNDO_LED_PIN, True)
            time.sleep(0.1)

            GPIO.output(UNDO_LED_PIN, False)
            time.sleep(0.1)

    virtual_file.seek(0)
    data_uri = "data:audio/wav;base64,{0}".format(virtual_file.read().encode("base64").replace("\n", ""))

    devices = networking.devices_in_proximity()

    payload = {"base_id": os.environ["BASE_ID"], "audio": data_uri, "devices": devices}

    upload_snippet(payload)

    # save to disk just to be sure
    #virtual_file.seek(0)
    #with open('snippets/' + str(int(time.time())) + '.wav','wb') as f:
    #    f.write(virtual_file.read())

@retrying.retry(wait_exponential_multiplier=1000, stop_max_attempt_number=5)
def upload_snippet(payload):
    response = requests.post(
            'https://getrecap.herokuapp.com/snippets',
            headers={'Content-type': 'application/json', 'Accept': 'application/json'},
            json=payload, timeout=120)

    #print(response.text)

    response.raise_for_status()

    print("* uploaded snippet")

def updateStrip():
    for n in range(0, strip.numPixels()):
        if n >= time_marker_start and n < time_marker_start + time_marker_size:
            strip.setPixelColor(n, COLOR)
        else:
            strip.setPixelColor(n, 0)

    strip.show()

def bootupAnimation():
    for i in range(0, strip.numPixels()/2 + 1):
        print i, strip.numPixels() - i

        strip.setPixelColor(i, COLOR)
        strip.setPixelColor(strip.numPixels() - i, COLOR)
        strip.show()
        time.sleep(200/1000.0)

    time.sleep(500/1000.0)

    fadeoutStrip()
    #for _ in range(5):
    #    time.sleep(100/1000.0)
    #    for i in range(strip.numPixels()):
    #        strip.setPixelColor(strip.numPixels() - i, COLOR)
    #    strip.show()
    #    time.sleep(100/1000.0)
    #    eraseStrip()

def wheel(pos):
    """Generate rainbow colors across 0-255 positions."""
    if pos < 85:
        return neopixel.Color(pos * 3, 255 - pos * 3, 0)
    elif pos < 170:
        pos -= 85
        return neopixel.Color(255 - pos * 3, 0, pos * 3)
    else:
        pos -= 170
        return neopixel.Color(0, pos * 3, 255 - pos * 3)

def theaterChaseAnimation(wait_ms=50, iterations=5):
    for j in range(iterations):
        for q in range(3):
            for i in range(0, strip.numPixels(), 3):
                strip.setPixelColor(i+q, COLOR)
            strip.show()
            time.sleep(wait_ms/1000.0)
            for i in range(0, strip.numPixels(), 3):
                strip.setPixelColor(i+q, 0)

    eraseStrip()

def fadeoutStrip(iterations=5):
    colors = [strip.getPixelColor(n) for n in range(strip.numPixels())]
    start = [[(color >> 16) & 0xff, (color >> 8) & 0xff, color & 0xff] for color in colors]
    for i in range(1, iterations + 1):
        for n in range(strip.numPixels()):
            # quadratic ease out
            rgb = [int(color - color * pow(i/float(iterations), 2)) for color in start[n]]

            strip.setPixelColor(n, neopixel.Color(rgb[0],rgb[1],rgb[2]))
        strip.show()
        time.sleep(0.01)

    # make sure pixels are truly at 0
    eraseStrip()

def eraseStrip():
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, 0)
    strip.show()


if __name__ == "__main__":
    main()
