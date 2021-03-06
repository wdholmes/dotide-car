import json
import serial
import requests
from datetime import datetime
import time
import threading
import Queue


API_KEY = ''
X_URL = ''
Y_URL = ''
CONTROL_URL = ''
SERIAL_PORT = 6


class ReadWorker(threading.Thread):
    def __init__(self, queue, serial):
        super(ReadWorker, self).__init__()
        self.queue = queue
        self.ser = serial

    def run(self):
        while True:
            print 'Read from car'
            data = (self.ser.readline()).split(',')
            self.queue.put({'at': datetime.now().isoformat(),
                            'x': float(data[0]),
                            'y': float(data[1])})


class PostWorker(threading.Thread):
    def __init__(self, queue):
        super(PostWorker, self).__init__()
        self.queue = queue

    def run(self):
        headers = {'ApiKey': API_KEY, 'content-type': 'application/json'}
        while True:
            payload_x = {'datapoints': []}
            payload_y = {'datapoints': []}
            for x in range(10):
                item = self.queue.get()
                payload_x['datapoints'].append({'at': item['at'], 'value': item['x']})
                payload_y['datapoints'].append({'at': item['at'], 'value': item['y']})
                self.queue.task_done()

            print 'post to web'
            requests.post(X_URL, data=json.dumps(payload_x), headers=headers)
            requests.post(Y_URL, data=json.dumps(payload_y), headers=headers)


class ControlWorker(threading.Thread):
    def __init__(self, serial):
        super(ControlWorker, self).__init__()
        self.ser = serial

    def run(self):
        headers = {'ApiKey': API_KEY, 'content-type': 'application/json'}
        while True:
            print 'GetAndWrite to car'
            res = requests.get(CONTROL_URL, headers=headers)
            print 'get info '
            data = res.json()
            self.command = data['current_value']
            print self.command
            self.ser.write(self.command)
            time.sleep(1)


def main():
    ser = serial.Serial()
    ser.port = SERIAL_PORT
    ser.baudrate = 9600
    ser.open()
    time.sleep(1)
    q = Queue.Queue()

    read_thread = ReadWorker(q, ser)
    read_thread.setDaemon(True)
    read_thread.start()

    post_thread = PostWorker(q)
    post_thread.setDaemon(True)
    post_thread.start()

    control_thread = ControlWorker(ser)
    control_thread.setDaemon(True)
    control_thread.start()

    read_thread.join()
    post_thread.join()
    control_thread.join()


if __name__ == '__main__':
    main()
