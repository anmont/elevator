#!/opt/local/bin/python3

# import the necessary packages
# dont forget to sudo apt-get install portaudio19-dev
from __future__ import print_function
from imutils.object_detection import non_max_suppression
from imutils import paths
import numpy as np
import argparse
import imutils
from datetime import datetime, timezone
import socket
import os
import subprocess
import cv2
import wave
import pyaudio
import sys
import time
import pytz
from matplotlib import pyplot as plt
from scipy.spatial import distance
import uuid
import ml_helper as mlh
import threading


filename = '._in_progress.avi'
frames_per_second = 25.0
res = '720p'
stream_source = 'none'

#collection event for opendoor
#begin counter / end counter
doorevent = False
event_begin = 0
event_in_prog = False
current_event_name = ""
status_door = False

#My recording parameters

TIME_TO_BUFFER = 10 #seconds to record before event
lastDoorEvent = 0
VIDEO_AFTER_EVENT = 10 #seconds to record after event

#audio params
audio_port = 554
ip = "admin:admin@192.168.1.108"
CHUNK = 1024
FORMAT = pyaudio.paInt16
WIDTH = 2
CHANNELS = 2
RATE = 44100
RECORD_SECONDS = 10
INPUT_IND = 6
RECORD = True

# Set resolution for the video capture
# Function adapted from https://kirr.co/0l6qmh
def change_res(cap, width, height):
    cap.set(3, width)
    cap.set(4, height)

# Standard Video Dimensions Sizes
STD_DIMENSIONS =  {
    "480p": (640, 480),
    "720p": (1280, 720),
    "1080p": (1920, 1080),
    "4k": (3840, 2160),
}

# grab resolution dimensions and set video capture to it.
def get_dims(cap, res='1080p'):
    width, height = STD_DIMENSIONS["480p"]
    if res in STD_DIMENSIONS:
        width,height = STD_DIMENSIONS[res]
    ## change the current caputre device
    ## to the resulting resolution
    change_res(cap, width, height)
    return width, height

# Video Encoding, might require additional installs
# Types of Codes: http://www.fourcc.org/codecs.php
VIDEO_TYPE = {
    'avi': cv2.VideoWriter_fourcc(*'MJPG'),
    #'mp4': cv2.VideoWriter_fourcc(*'H264'),
    #    'mp4': cv2.VideoWriter_fourcc(*'XVID'),
    'mp4': cv2.VideoWriter_fourcc(*'MJPG'),
}

def get_video_type(filename):
    filename, ext = os.path.splitext(filename)
    if ext in VIDEO_TYPE:
      return  VIDEO_TYPE[ext]
    return VIDEO_TYPE['avi']

# Function to get Distance between two points (Euclidean Distance)
def dist(x,y):
    return np.sqrt(np.sum((x-y)**2))

# Function to inform door status.... actually only when it opens
def sendDoorStatus():
    dataToSend = {
        "Description": "Door Opened",
        "Source": "door_opened"
    }
    sendStatus(dataToSend)

# Function to inform Person Detection
def sendPeople(description):
    dataToSend = {
        "Description": description,
        "Source": "people_detect"
    }
    sendStatus(dataToSend)

# Function to actually do the HTTP Post
def sendStatus(data):

    fmt = "%Y-%m-%d %H:%M:%S.%f"
    date = datetime.now(timezone.utc)

    data["TimeStamp"] = date.strftime(fmt)
    data["EVENT_ID"] = str(uuid.uuid4())

    print(data)

    '''
    import requests
    from json import dumps
    API_ENDPOINT = 'http://localhost:3002/events'
    r = requests.post(url = API_ENDPOINT, data = dumps(data))

    # extracting response text
    pastebin_url = r.text
    print(mlh.bcolors.OKGREEN + "Sent:%s"%pastebin_url + mlh.bcolors.ENDC)
    '''

# fuction to merge video and audio in a seperate thread so as to not lock
def mergeSources(name):
    #small race condition when releasing resources
    time.sleep(0.1)
    subprocess.call(['ffmpeg', '-loglevel', 'panic', '-i', name + '.avi', '-i', name + '.wav', '-c', 'copy', name + 'm.avi'])
    #NEED TO DELETE SOURCE FILES
    print("finished merging video")

def drawSafeZones(cv2):
    cv2.polylines(image, np.array([danger_area_pts1]), True, (0,0,255), 2)
    cv2.polylines(image, np.array([danger_area_pts2]), True, (0,0,255), 2)

    if status_door:
        cv2.polylines(image, np.array([exit_area_pts]), True, (0,255,0), 2)
    else:
        cv2.polylines(image, np.array([exit_area_pts]), True, (0,0,255), 2)

    cv2.imshow("After", image)

def doorDetection(avg):
    if avg < 100:
        #Register globals (sadly)
        global event_in_prog
        global current_event_name
        global lastDoorEvent
        global status_door
        global door_status_sent
        
        #signal an event
        if event_in_prog == False:
            event_in_prog = True
            #print("starting audio recorder thread")
            #starting a new door event
            fmt = "%Y%m%d%H%M%S%f"
            date = datetime.now(timezone.utc)
            current_event_name = "cv" + date.strftime(fmt)

        lastDoorEvent = time.time()
        
        if not status_door:
            print("\n")
            print(mlh.bcolors.WARNING + "Door Open" + mlh.bcolors.ENDC)
            sendDoorStatus()
            door_status_sent = True
        status_door = True
    else:
        status_door = False
        door_status_sent = False

# function to record audio and write it to a file
def recAudio(name):
    p = pyaudio.PyAudio()
    p.open()

    stream = p.open(input_device_index=int(INPUT_IND), format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)

    print("* audio recording")

    RECORDING = False
    framebuffer = []
    recorderframes = []

    #for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
    while (True):
        #case 1 alwasy recording
        data = stream.read(CHUNK)
        framebuffer.append(data)

        #print(framebuffer.count)
        if (framebuffer.count > int(RATE / CHUNK * RECORD_SECONDS)):
            del framebuffer[0]

        #case 2 recording started
        if (event_in_prog and not RECORDING):
            recorderframes = framebuffer.copy()
            print("* start audio recording")
            RECORDING = True
            #framebuffer.append(data) not sure... the copy shouldnt take a chunk time so leaving out now

        #case 3 recording in progress
        if (event_in_prog and RECORDING):
            recorderframes.append(data)
            #framebuffer.append(data) 
        
        #case 4 wrap up recording
        if (not event_in_prog and RECORDING):
            #stream.stop_stream()
            #stream.close()
            wf = wave.open(current_event_name + ".wav", 'wb')
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(p.get_sample_size(FORMAT))
            wf.setframerate(RATE)
            wf.writeframes(b''.join(recorderframes))
            wf.close()
            recorderframes.clear()
            RECORDING = False
            print("* done audio recording")

    #while (event_in_prog):
    #    data = stream.read(CHUNK)
    #    frames.append(data)

    

# construct the argument parse and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument("-v", "--video", help="path to the video file")
ap.add_argument("-a", "--audio", help="Choose a specific audio device. Or --audio list to list audio devices")
args = vars(ap.parse_args())

# initialize the HOG descriptor/person detector
hog = cv2.HOGDescriptor()
hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())


# These arg handle the audo options audio list and audio selection
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
        INPUT_IND = int(args["audio"])

# if the video argument is None, then we are reading from webcam
if args.get("video", None) is None:
    stream_source = 'live'
    #camera = cv2.VideoCapture(0)
    camera = cv2.VideoCapture("rtsp://admin:admin@192.168.1.108:554/live")
    #camera.set(CV_CAP_PROP_BUFFERSIZE, 250)
    time.sleep(0.25)
# otherwise, we are reading from a video file
else:
    camera = cv2.VideoCapture(args["video"])
    #camera.set(CAP_PROP_BUFFERSIZE, 250)
# here I think we should add rtsp as well i.e. camera = cv2.VideoCapture("rtsp://admin:@192.168.3.231")


get_dims(camera, res)

# Set some camera parameters
cam_params = {
    'brightness': camera.get(11), #32.0,
    'contrast': camera.get(12), #64.0,
    'saturation': camera.get(13), #0.0,
    'hue' : camera.get(14), #,
    'gain': camera.get(15), #,
    'exposure': camera.get(16), #,
    }

cv2.namedWindow('After', cv2.WINDOW_NORMAL)

# These will store the place where the user last clicked
ix,iy = -1,-1
# mouse callback function
def getMousePoint(event,x,y,flags,param):
    global ix,iy, selectedPoint
    if event == cv2.EVENT_LBUTTONDBLCLK:
        ix,iy = x,y
        danger_area_pts1[selectedPoint - 1, 0] = x
        danger_area_pts1[selectedPoint - 1, 1] = y
        selectedPoint += 1
        if selectedPoint > len(danger_area_pts1):
            selectedPoint = 0

        print(danger_area_pts1)

selectedPoint = 1

# let the hardcoding begin...
# define danger / safe areas ... will use later on

print (STD_DIMENSIONS[res][0])
danger_area_pts1 = np.array([[6,1],[70,1],[126,358],[4,358]], np.int32)
danger_area_pts2 = np.array([[531,1],[640,1],[640,356],[537,356]], np.int32)
danger_area_pts3 = (381,1,497,248)

#danger_area_pts1 = np.array([[0,0],[0,1],[0,1135],[154,1135]], np.int32)
#danger_area_pts2 = np.array([[0,1],[557,1],[154,1135],[453,1135]], np.int32)
#danger_area_pts3 = (381,1,497,248)
status_crash = False
#exit_area_pts = np.array([[557,1],[630,1],[453,1135],[630,1135]], np.int32)
exit_area_pts = np.array([[72,1],[536,1],[536,356],[132,356]], np.int32)
# define where we do the person detection
exit_area_detection = (180,00,371,154)

# our "Marker" for detecting open door... 
coord_door_open = (175, 118, 178, 122)


cv2.setMouseCallback('After',getMousePoint)
numPeople = 0
frame_counter = 0
lastFound = np.array((0,0,0))
door_status_sent = False

# this is part of the hack for not sending multiple HTTP Posts for the same
# person
personSentAt = time.time()
last_rec_period = time.time()

#cv2.size::Size S = cv::Size((int) vcap.get(CV_CAP_PROP_FRAME_WIDTH), (int) vcap.get(CV_CAP_PROP_FRAME_HEIGHT));

frame_width = int( camera.get(cv2.CAP_PROP_FRAME_WIDTH))
frame_height =int( camera.get( cv2.CAP_PROP_FRAME_HEIGHT))
incoming_FPS = int(camera.get(cv2.CAP_PROP_FPS))
fourcc = cv2.VideoWriter_fourcc(*'MJPG')
#We dont want to start recording audio thread if its from a file
if (stream_source == "live"):
    threading._start_new_thread(recAudio, ("fname", ))

vout = cv2.VideoWriter(filename, fourcc, incoming_FPS, (frame_width, frame_height))
#vout = cv2.VideoWriter(filename, cv2.VideoWriter_fourcc(*'MJPG'), 25, get_dims(camera, res))

#int(vout.get(CV_CAP_PROP_FRAME_WIDTH)), int(vout.get(CV_CAP_PROP_FRAME_HEIGHT))
while(True):
    cur_time = time.time()
    ret, frame = camera.read()
    #handle buffer

    #create recording buffer
    #create framebuffer
    
    videoframebuffer = []
    recorderframebuffer = []


    #TODO stabilize the frames per second in the video recording

    if (cur_time - last_rec_period) <= 10 :
        vout.write(frame)
    else:
        if event_in_prog == False:
            last_rec_period = cur_time
        else:
            vout.write(frame)
            if (cur_time - lastDoorEvent) > 10:
                last_rec_period = cur_time
                vout.release()
                os.rename(filename, current_event_name + ".avi")
                event_in_prog = False
                vout = cv2.VideoWriter(filename, fourcc, incoming_FPS, (frame_width, frame_height))
                #ONCE THIS IS DONE WE NEED TO MERGE WITH FFMPEG IN A NEW PROC
                threading._start_new_thread(mergeSources, (current_event_name, ))

    # little code for looping on the video
    frame_counter += 1
    if stream_source != 'live': #cause there is no framecounter on live video
        if frame_counter == camera.get(cv2.CAP_PROP_FRAME_COUNT):
            frame_counter = 0 #Or whatever as long as it is the same as next line
            camera.set(cv2.CAP_PROP_POS_FRAMES, 0)

    #should handle null case > likely end of event/steam/video
    image = imutils.resize(frame, width=640)
    
    #image = frame
    door_handle_gray = image[coord_door_open[1]:coord_door_open[3], coord_door_open[0]:coord_door_open[2]]
    avg = door_handle_gray.mean()

    #attempt to move actions off main thread for more logic
    doorDetection(avg)
    # end Door Open Detection

    # begin People Detection
    image_for_detection = image[exit_area_detection[1]:exit_area_detection[3], exit_area_detection[0]:exit_area_detection[2]]
    (rects, weights) = hog.detectMultiScale(image_for_detection, winStride=(2, 2),
    padding=(2, 2), scale=1.05)

    rects = np.array([[x + exit_area_detection[0],
                       y + exit_area_detection[1],
                       x  + exit_area_detection[0] + w,
                       y + exit_area_detection[1] + h] for (x, y, w, h) in rects])

    pick = non_max_suppression(rects, probs=None, overlapThresh=0.05)
    # end People Detection

    cnts = np.array([exit_area_pts])

    for (xA, yA, xB, yB) in pick:
        cv2.rectangle(image, (xA, yA), (xB, yB), (250, 255, 100), 2)
        cv2.circle(image, (xA+int((xB-xA)/2) , yA+int((yB-yA)/2)), 10, (250, 250, 250), -1 )

        # Check to see if the person was at the indicated zone
        coef = int((yB-yA) * 0.2)
        ret = cv2.pointPolygonTest(cnts, (xA + int((xB-xA) / 2), yB-coef), False)
        if ret > 0:
            # Check to see is not too soon to send a new HTTP Post (If it is,
            # it means is the same person)
            if (time.time() - personSentAt) > 2:
                cv2.rectangle(image, (xA, yA), (xB, yB), (0, 0, 255), 2)
                lastFound = np.array((xA, yA,0))
                numPeople += 1
                print("\n")
                print(mlh.bcolors.WARNING + "Person Detected ({})".format(numPeople) + mlh.bcolors.ENDC)

                personSentAt = time.time()
                event_in_prog = True
                sendPeople("Person detected on video")

        cv2.rectangle(image, (xA, yA), (xB, yB), (100, 255, 100), 1)

    # Draw Danger / Safe zones
    drawSafeZones(cv2)
    #cv2.polylines(image, np.array([danger_area_pts1]), True, (0,0,255), 2)
    #cv2.polylines(image, np.array([danger_area_pts2]), True, (0,0,255), 2)

    #if status_door:
    #    cv2.polylines(image, np.array([exit_area_pts]), True, (0,255,0), 2)
    #else:
    #    cv2.polylines(image, np.array([exit_area_pts]), True, (0,0,255), 2)

    #cv2.imshow("After", image)

    k = cv2.waitKey(1)
    if k==27:
        break
    elif k==ord('q'):
        break
    elif k == ord('d'):
        if debug:
            debug = False
            printCamStats = False
        else:
            debug = True
            printCamStats = True
    elif k == ord('1'):
        selectedPoint = 1
    elif k == ord('2'):
        selectedPoint = 2
    elif k == ord('3'):
        selectedPoint = 3
    elif k == ord('4'):
        selectedPoint = 4
    elif k == ord('5'):
        selectedPoint = 5
    elif k == ord('6'):
        selectedPoint = 6
    elif k == ord('7'):
        selectedPoint = 7

if vout.isOpened:
    vout.release()

camera.release()
cv2.destroyAllWindows()
