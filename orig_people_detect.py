#!/opt/local/bin/python3

# import the necessary packages
from __future__ import print_function
from imutils.object_detection import non_max_suppression
from imutils import paths
import numpy as np
import argparse
import imutils
from datetime import datetime, timezone
import os
import cv2
import sys
import time
import pytz
from matplotlib import pyplot as plt
from scipy.spatial import distance
import uuid
import ml_helper as mlh


filename = '._in_progress.avi'
frames_per_second = 25.0
res = '720p'
stream_source = 'none'

#collection event for opendoor
#begin counter / end counter
doorevent = False
event_begin = 0


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
    'avi': cv2.VideoWriter_fourcc(*'XVID'),
    #'mp4': cv2.VideoWriter_fourcc(*'H264'),
    'mp4': cv2.VideoWriter_fourcc(*'XVID'),
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

# construct the argument parse and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument("-v", "--video", help="path to the video file")
args = vars(ap.parse_args())

# initialize the HOG descriptor/person detector
hog = cv2.HOGDescriptor()
hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())

# if the video argument is None, then we are reading from webcam
if args.get("video", None) is None:
    stream_source = 'live'
    camera = cv2.VideoCapture(0)
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
status_crash = False

exit_area_pts = np.array([[72,1],[536,1],[536,356],[132,356]], np.int32)

# define where we do the person detection
exit_area_detection = (180,00,371,154)

# our "Marker" for detecting open door... 
coord_door_open = (175, 118, 178, 122)
status_door = False

cv2.setMouseCallback('After',getMousePoint)
numPeople = 0
frame_counter = 0
lastFound = np.array((0,0,0))
door_status_sent = False

# this is part of the hack for not sending multiple HTTP Posts for the same
# person
personSentAt = time.time()
last_rec_period = time.time()
event_in_prog = False

vout = cv2.VideoWriter(filename, get_video_type(filename), 25, get_dims(camera, res))

while(True):

    cur_time = time.time()
    ret, frame = camera.read()

    if (cur_time - last_rec_period) <= 10 :
        vout.write(frame)
    else:
        if event_in_prog == False:
            last_rec_period = cur_time
            vout.release()
            vout = cv2.VideoWriter(filename, get_video_type(filename), 25, get_dims(camera, res))
        else:
            vout.write(frame)
            if (cur_time - last_rec_period) > 20:
                fmt = "%Y%m%d%H%M%S%f"
                date = datetime.now(timezone.utc)
                new_filename = "cv-%s.avi" % date.strftime(fmt)
                last_rec_period = cur_time
                vout.release()
                os.rename(filename, new_filename)
                event_in_prog = False
                vout = cv2.VideoWriter(filename, get_video_type(filename), 25, get_dims(camera, res))

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

    if avg < 100:
        event_in_prog = True
        status_door = True
        if not door_status_sent:
            print("\n")
            print(mlh.bcolors.WARNING + "Door Open" + mlh.bcolors.ENDC)
            sendDoorStatus()
            door_status_sent = True
    else:
        status_door = False
        door_status_sent = False


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
    cv2.polylines(image, np.array([danger_area_pts1]), True, (0,0,255), 2)
    cv2.polylines(image, np.array([danger_area_pts2]), True, (0,0,255), 2)

    if status_door:
        cv2.polylines(image, np.array([exit_area_pts]), True, (0,255,0), 2)
    else:
        cv2.polylines(image, np.array([exit_area_pts]), True, (0,0,255), 2)

    cv2.imshow("After", image)

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
