#!/opt/local/bin/python3

# import the necessary packages
# dont forget to sudo apt-get install portaudio19-dev

import wave
#import pyaudio
import sys
import time
import ffmpeg



#audio stream defaults
#audiofilename = "default.wav"
#CHUNK = 1024
#WIDTH = 2
#FORMAT = pyaudio.paInt16
#CHANNELS = 2
#RATE = 44100
#RECORD_SECONDS = 5



#p = pyaudio.PyAudio()
#for i in range(p.get_device_count()):
#    print (p.get_device_info_by_index(i))

#def callback(in_data, frame_count, time_info, status):
#    return (in_data, pyaudio.paContinue)
#stream = p.open(format=p.get_format_from_width(WIDTH), input_device_index = 0, channels=CHANNELS, rate=RATE, input=True, output=True, stream_callback=callback)
#stream.start_stream()
#while stream.is_active():
#    time.sleep(0.1)

#vout = cv2.VideoWriter(filename, get_video_type(filename), 25, get_dims(camera, res))

#stream.stop_stream()
#stream.close()


process1 = (
    ffmpeg
    .audio()
    #.input((in_filename)
    .output('pipe:', format='rawvideo', pix_fmt='rgb24', vframes=8)
    .run_async(pipe_stdout=True)
)

while True:
    in_bytes = process1.stdout.read(width * height * 3)
    if not in_bytes:
        break
    in_frame = (
        np
        .frombuffer(in_bytes, np.uint8)
        .reshape([height, width, 3])
    )

    # See examples/tensorflow_stream.py:
    out_frame = deep_dream.process_frame(in_frame)

    process2.stdin.write(
        in_frame
        .astype(np.uint8)
        .tobytes()
    )
process1.wait()