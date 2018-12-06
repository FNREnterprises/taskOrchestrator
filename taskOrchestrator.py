
import time
import datetime

import rpyc
from rpyc.utils.server import ThreadedServer
import psutil
import subprocess


MY_IP = "192.168.0.17"
taskPath = "c:/Projekte/InMoov"

inmoovTasks = {'cartControl':  {'port': 20001, 'startFile': 'cartControl.py'},
               'aruco':        {'port': 20002, 'startFile': 'aruco.py'},
               'kinect':       {'port': 20003, 'startFile': 'kinect.py'},
               'servoControl': {'port': 20004, 'startFile': 'servoControl.py'}}

clientList = []
clientName = []

def log(msg):
    logtime = str(datetime.datetime.now())[11:]
    print(f"{logtime} - {msg}")
    for i, c in enumerate(clientList):
        try:
            c.root.exposed_log("taskOrchestrator - " + msg)
        except Exception as e:
            print(f"can not log to {clientName[i]}, trying to remove client")
            try:
                del clientList[i]
                del clientName[i]
            except Exception as e:
                print(f"error trying to remove client {i}, {clientName[i]} from list, {e}")

class taskOrchestratorListener(rpyc.Service):

    global clientList, clientName

    persistConn = None

    def on_connect(self, conn):
        print(f"taskOrchestrator: on_connect triggered")
        callerName = conn._channel.stream.sock.getpeername()
        self.persistConn = conn
        if conn not in clientList:
            clientList.append(conn)
            clientName.append(callerName)
        log(f"on_connect in taskOrchestrator with {callerName}")

    def on_disconnect(self, conn):
        callerName = conn._channel.stream.sock.getpeername()
        print(f"on_disconnect triggered with {callerName}")


    def exposed_getLifeSignal(self):
        log(f"getLifeSignal request received")
        return True


    def exposed_startTask(self, task):

        log(f"startTask for {task} received")

        # only 1 instance allowed
        taskAlreadyRunning = False
        for process in psutil.process_iter():
            try:
                # find processes started with debugger too
                if 'python' in process.cmdline()[0]:
                    if inmoovTasks[task]['startFile'] in ''.join(process.cmdline()):
                        print(f'{time.time()} - an instance of {task} is already running')
                        taskAlreadyRunning = True

            except Exception as e:  # some processes do not allow inquiries
                pass


        if not taskAlreadyRunning:
            # e.g. C:/Projekte/InMoov/start_CartControl.bat
            print(f"{time.time()} - restart task {task}")
            taskBatch = f"c:/projekte/inmoov/start_{task}.bat"
            print(f"{time.time()} - subprocess.call({taskBatch})")
            subprocess.call(taskBatch)

        return MY_IP, inmoovTasks[task]['port'], taskAlreadyRunning


    def exposed_stopTask(self, task):

        print(f"request for terminating task '{task}' received")

        for process in psutil.process_iter():
            try:
                # find processes started with debugger too
                if 'python' in process.cmdline()[0]:
                    if inmoovTasks[task]['startFile'] in ''.join(process.cmdline()):
                        print(f'{time.time()} - an instance of {task} found, killing it')
                        process.kill()
                        return

            except Exception as e:  # some processes do not allow inquiries, ignore them
                pass
        print(f"task '{task}' not found in process list")



if __name__ == "__main__":

    print(f"start listening on port 20000")
    server = ThreadedServer(taskOrchestratorListener, port=20000)
    server.start()