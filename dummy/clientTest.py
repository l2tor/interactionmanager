#!/usr/bin/env python
# coding: utf-8 

import threading
import socket
from threading import Thread
import logging
import re
import time
import log_formatter as lf
import sys

runningReading = True

class Test:
    def __init__(self):
        pass

    def init(self,params):
        logging.info("init method called with: " + params)

    def paf(self,params):
        logging.info("paf method called with: " + params)

    def pif(self,params):
        logging.info("pif method called with: " + params)

def readMessages(sock,aMessages):
    #while 1 loop, feeling aMessages
    while runningReading == True:
        try:
            strReceive = sock.recv(1024)
            strReceive = strReceive.split("#")
            aMessages += strReceive
            time.sleep(1)
        except socket.error, e:
            logging.debug("error on socket: " + str(e))
            pass

def sendMessage(socket,strMessage):
    #send the message in parameter
    socket.sendall(strMessage + "#")
    time.sleep(0.1)


def main():
    #example of client in python
    #connectin to the server and receving the messages
    strLogFile = "logs/client-test.log"
    logging.basicConfig(filename=strLogFile, level=logging.DEBUG, format='%(levelname)s %(relativeCreated)6d %(threadName)s %(message)s (%(module)s.%(lineno)d)',filemode='w')
    logFormatter = lf.LogFormatter(strLogFile)
    logFormatter.start()

    logging.info("start the test script of the client")

    ip   = "127.0.0.1"
    port = 1111

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
    server_address = ('localhost', 1111)
    sock.connect(server_address) 
    sock.settimeout(1)
    
    aMessages = []
    t = threading.Thread(target=readMessages, args=(sock, aMessages))
    t.start()

    logging.info("register outputManager")
    sendMessage(sock,"register:outputManager")
    myTest = Test()

    try:
        while True:
            for strMessage in aMessages:
                if strMessage != "":
                    fields = strMessage.split(" ")
                    logging.info("received message from " + str(fields[0])) 
                    method = fields[1]
                    params = fields[2]
                    getattr(myTest,method)(params)
            del aMessages[:]

            logging.debug("send message")
            #sendMessage(sock,"call:tablet.stuff.stuff 0.5")
            #sendMessage(sock,"call:tablet.stuff.stuff")
            #sendMessage(sock,"call:nao.ALTextToSpeech.fake 'test'")
            #sendMessage(sock,"call:nao.fake.fake 'test'")
            time.sleep(5)

    except KeyboardInterrupt:
        global runningReading
        logging.info("Stope the client")
        runningReading = False
        t.join()
        sock.close()
        logFormatter.stopReadingLogs()


if __name__ == "__main__":
    main()
