import pyaudio
import wave
import sys
import time
import argparse
import threading

#audio params
CHUNK = 1024
FORMAT = pyaudio.paInt16
WIDTH = 2
CHANNELS = 2
RATE = 44100
RECORD_SECONDS = 5
WAVE_OUTPUT_FILENAME = "voice.wav"
INPUT_IND = 6
RECORD = True


ap = argparse.ArgumentParser()
ap.add_argument("-a", "--audio", help="Choose a specific audio device. Or --audio list to list audio devices")
args = vars(ap.parse_args())

if args.get("audio", None) is not None:
    if args["audio"] == "list":
        try:
            p = pyaudio.PyAudio()
        except:

            pass
        info = p.get_host_api_info_by_index(0)
        numdevices = info.get('deviceCount')
        for i in range(0, numdevices):
            if (p.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0:
                print ("Input Device id ", i, " - ", p.get_device_info_by_host_api_device_index(0, i).get('name'))
        quit()
    else:
        print (args["audio"])
        INPUT_IND = args["audio"]

def recAudio(fnamea):
    p = pyaudio.PyAudio()
    stream = p.open(input_device_index=int(INPUT_IND), format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)

    print("* recording")
    
    frames = []

    while (RECORD):
        data = stream.read(CHUNK)
        frames.append(data)

    print("* done recording")
    stream.stop_stream()
    stream.close()
    p.terminate()

    wf = wave.open(WAVE_OUTPUT_FILENAME, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()


threading._start_new_thread(recAudio, ("fname", ))
time.sleep(5)
RECORD = False
#only here to wiat for the timer to close
time.sleep(1)

