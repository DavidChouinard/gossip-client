
import alsaaudio
import wave

RATE = 44100/2

BUFFER_SIZE = 30;  # in seconds

buffer = []

def start_recording():
    mixer = alsaaudio.Mixer(control="Mic")
    mixer.setvolume(90, 0, alsaaudio.PCM_CAPTURE)

    inp = alsaaudio.PCM(alsaaudio.PCM_CAPTURE, alsaaudio.PCM_NONBLOCK)

    inp.setchannels(1)
    inp.setrate(RATE)
    inp.setformat(alsaaudio.PCM_FORMAT_S16_LE)
    inp.setperiodsize(160)

    print("* starting recording")

    while True:
        if (len(buffer) > int(RATE / 920 * BUFFER_SIZE)):
            buffer.pop(0);

        l, data = inp.read()

        if l > 0:
            buffer.append(data)

def clear_buffer():
    buffer = []  # flush buffer

def get_buffer():
    return b''.join(buffer)
