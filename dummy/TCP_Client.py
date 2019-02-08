#!/usr/bin/env python
# coding: utf-8

import socket
from threading import Thread
import logging
import re
import time
import log_formatter as lf
import sys
import json

runningReading = True


class TCPClient:

    def __init__(self, client_name, ip="localhost", port=1111):
        # example of client in python
        # connectin to the server and receving the messages
        strLogFile = "logs/client-interactionmanager.log"# + sys.argv[1] + ".log"
        logging.basicConfig(filename=strLogFile, level=logging.DEBUG,
                            format='%(levelname)s %(relativeCreated)6d %(threadName)s %(message)s (%(module)s.%(lineno)d)',
                            filemode='w')
        self.logFormatter = lf.LogFormatter(strLogFile)
        self.logFormatter.start()

        logging.info("start the test script of the client")

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_address = (ip, port)
        self.sock.connect(server_address)

        self.aMessages = []
        self.t = Thread(target=self.readMessages, args=(self.sock, self.aMessages))
        self.t.start()

        logging.info("register " + client_name)
        self.sendMessage("register:" + client_name)

    @staticmethod
    def readMessages(_socket, aMessages):
        # while 1 loop, feeling aMessages
        while runningReading:
            strReceive = _socket.recv(1024)
            strReceive = strReceive.split("#")
            aMessages += strReceive
            # if len(aMessages) > 0:
            #     print aMessages
            time.sleep(1)

    def sendMessage(self, strMessage):
        # send the message in parameter
        print "send message", strMessage
        self.sock.sendall(strMessage + "#")

######################################################
### Functions for requesting data ####################
######################################################

    def get_message(self):
        while len(self.aMessages) <= 0:
            time.sleep(0.1)
        data = self.aMessages[:]
        del self.aMessages[:]
        return data

######################################################
    def close_connection(self):
        global runningReading
        logging.info("Stope the client")
        runningReading = False
        self.t.join()
        self.sock.close()
        self.logFormatter.stopReadingLogs()

if __name__ == "__main__":
    obj = TCPClient("outputManager")
    try:
        while True:
            print obj.get_message()
            time.sleep(1)

    except KeyboardInterrupt:
        obj.close_connection()
