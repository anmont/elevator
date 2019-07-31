import pyaudio
import wave
import sys
import time
import argparse
import threading

CHUNK = 1024
FORMAT = pyaudio.paInt16
WIDTH = 2
CHANNELS = 2
RATE = 44100
RECORD_SECONDS = 5
WAVE_OUTPUT_FILENAME = "voice.wav"
INPUT_IND = 6


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


class RecordAudio():
    def __init__(self):
        self.open = True
        self.rate = 44100
        self.frames_per_buffer = 1024
        self.channels = 2
        self.format = pyaudio.paInt16
        self.audio_filename = "temp_audio.wav" #todo
        self.audio = pyaudio.PyAudio()
        self.stream = self.audio.open(input_device_index=int(INPUT_IND),
                                    format=self.format,
                                    channels=self.channels,
                                    rate=self.rate,
                                    input=True,
                                    frames_per_buffer = self.frames_per_buffer)
        self.audio_frames = []


    # Audio starts being recorded
    def record(self):
        self.stream.start_stream()
        while(self.open == True):
            data = self.stream.read(self.frames_per_buffer) 
            self.audio_frames.append(data)
            if self.open==False:
                break


    # Finishes the audio recording therefore the thread too    
    def stop(self):

        if self.open==True:
            self.open = False
            self.stream.stop_stream()
            self.stream.close()
            self.audio.terminate()
            waveFile = wave.open(self.audio_filename, 'wb')
            waveFile.setnchannels(self.channels)
            waveFile.setsampwidth(self.audio.get_sample_size(self.format))
            waveFile.setframerate(self.rate)
            waveFile.writeframes(b''.join(self.audio_frames))
            waveFile.close()
        pass

    # Launches the audio recording function using a thread
    def start(self):
        audio_thread = threading.Thread(target=self.record)
        audio_thread.start()


# =================================================================================================





#stream = p.open(input_device_index=int(INPUT_IND), format=FORMAT,
#                channels=CHANNELS,
#                rate=RATE,
#                input=True,
#                frames_per_buffer=CHUNK)

#print("* recording")
#p = pyaudio.PyAudio()
#frames = []

#for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
#    data = stream.read(CHUNK)
#    frames.append(data)

#while record = True
#    data = stream.read(CHUNK)
#    frames.append(data)

#print("* done recording")

#stream.stop_stream()
#stream.close()
#p.terminate()

#wf = wave.open(WAVE_OUTPUT_FILENAME, 'wb')
#wf.setnchannels(CHANNELS)
#wf.setsampwidth(p.get_sample_size(FORMAT))
#wf.setframerate(RATE)
#wf.writeframes(b''.join(frames))
#wf.close()

global audio_thread

audio_thread = RecordAudio()
audio_thread.start()
time.sleep(5)
audio_thread.stop()