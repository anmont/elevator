
FROM python:3.7.4

#ARG EXECUTABLE
#ENV EXECUTABLE ${EXECUTABLE}
ENV RTSP='rtsp://admin:admin@192.168.1.108:554/live'
# Update Software repository
RUN apt-get update
RUN apt-get -y install portaudio19-dev
RUN apt-get -y install ffmpeg
RUN apt-get install -y libasound2 libasound-dev libssl-dev 

RUN pip3 install imutils
RUN pip3 install numpy
RUN pip3 install opencv-python
RUN pip3 install pyaudio
RUN pip3 install matplotlib
RUN pip3 install pytz
RUN pip3 install scipy

COPY . /app
WORKDIR /app
CMD ["python3", "docker.py"]