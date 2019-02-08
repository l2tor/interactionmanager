#!/usr/bin/env python
# coding: utf-8

import socket
from threading import Thread, Lock
# import logging
import time

import json
from TCP_CallbackClass import CallbackClass
from Queue import Queue
from enums import Move_State

runningReading = True


class TCPClient:
    tcp_logger = None

    def __init__(self, client_name, interaction_manager, underworlds, im_logger, ip="127.0.0.1", port=1111):
        # store reference to interaction manager
        self._im = interaction_manager
        self._uwd = underworlds

        TCPClient.tcp_logger = im_logger

        # create socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_address = (ip, port)
        # try to connect in a loop with 3 sec sleep
        while True:
            try:
                TCPClient.tcp_logger.info("Try to  connect to connectionmanager on %s:%s" % server_address)
                self.sock.connect(server_address)
                TCPClient.tcp_logger.info("Connection established!")
                break
            except socket.error, exc:
                TCPClient.tcp_logger.info("Connection timeout - retry in 3 seconds.")
                time.sleep(3)

        # list of received messages
        self.a_messages = Queue()

        # start thread to receive messages
        TCPClient.tcp_logger.info("Starting thread for receiving messages ...")
        self.t = Thread(target=self.read_messages, args=(self.sock, self.a_messages))
        self.t.start()

        # start thread to evaluate the received messages
        TCPClient.tcp_logger.info("Starting thread for handling messages ...")
        self.callback_obj = CallbackClass(self, interaction_manager, underworlds, TCPClient.tcp_logger)
        self.te = Thread(target=self.event_binding, args=(self.callback_obj, self.a_messages))
        self.te.start()

        # register interaction manager at connection manager
        TCPClient.tcp_logger.info("register " + client_name)
        self.sendMessage("register:" + client_name)

        self.lock = Lock()

        # initialize some indicator variables for accepting or refusing different kind of messages
        self.acceptVAD = False
        self.acceptSpRel = False
        self.movable_obj = None
        self.acceptTouchObjs = False
        self.acceptCollision = False
        self.acceptTouchSensor = False

    def set_memory(self, memory):
        self.callback_obj.set_memory(memory)

    @staticmethod
    def read_messages(_socket, a_messages):
        """
            This function receives all messages send over the socket connection.

            :param _socket: The TCP Socket.
            :param a_messages: A list where all messages have to be stored.
        """
        tmp_messages = []
        while runningReading:
            try:
                str_receive = _socket.recv(1024)
                if "#" in str_receive:
                    str_receive = str_receive.split("#")
                    if len(str_receive) > 1:
                        tmp_messages += str_receive[0]
                        a_messages.put("".join(tmp_messages)) if len(tmp_messages) > 1 else a_messages.put(tmp_messages[0])

                        for r in str_receive[1:-1]:
                            a_messages.put(r)
                            TCPClient.tcp_logger.info("Current message # on stack: %s" % a_messages.qsize())

                    tmp_messages = [str_receive[-1]]
                else:
                    tmp_messages.append(str_receive)

                #time.sleep(0.3)
            except socket.error, e:
                TCPClient.tcp_logger.debug("error on socket: " + str(e))

    @staticmethod
    def event_binding(callback, a_messages):
        """
            This method evaluates all send messages and calls the corresponding callback function.

            :param callback: The object which contains all callback functions.
            :param a_messages: The send message with function call.
        """
        while runningReading:
            if not a_messages.empty():
                str_message = a_messages.get_nowait()
                if str_message != "":
                    fields = str_message.split("|")
                    sender, method, params = fields[:3]
                    TCPClient.tcp_logger.info("received message %s from %s" % (method, str(sender)))
                    try:
                        getattr(callback, method)(sender, params)
                    except AttributeError:
                        TCPClient.tcp_logger.error("Function call %s not found!" % method)
                a_messages.task_done()
            time.sleep(0.01)

    def sendMessage(self, str_message):
        """
            This function sends a messages to the connection manager.

            :param str_message: The message to be send.
        """
        if "uwdsStatus" in str_message:
            pass
            #TCPClient.tcp_logger.debug("send message: %s" % str_message)
        else:
            TCPClient.tcp_logger.info("send message: %s" % str_message)
        self.sock.sendall(str_message + "#")

    def close_connection(self):
        """
            This function provides a clean close and exit for the TCP client.
        """
        global runningReading
        TCPClient.tcp_logger.info("Stop the client")
        runningReading = False
        self.sendMessage("exit")
        self.t.join()
        self.te.join()
        self.sock.close()

    # ============================================
    STR_OUTPUTMANAGER = "tablet.outputmanager"
    STR_TABLETGAME = "tablet.WebSocket"

    # ============= CONTROL PANEL ================
    def memory_loaded(self, _data):
        self.sendMessage('call:tablet.ControlPanel.memoryLoaded|%s' % json.dumps(_data))

    def send_session_information(self, session_info):
        self.sendMessage('call:tablet.ControlPanel.sessionInformationUpdate|[%s, %s, %s]' % (session_info["task_id"], session_info["task_type"], session_info["scene"]))

    def send_extended_session_information(self, _data):
        self.sendMessage('call:tablet.ControlPanel.extendedSessionInformationUpdate|%s' % json.dumps(_data))

    def send_uwds_status(self, data):
        self.sendMessage('call:tablet.ControlPanel.uwdsStatus|%s' % json.dumps(data))

    def memory_unloaded(self):
        self.sendMessage('call:tablet.ControlPanel.memoryUnloaded')

    def set_list_of_memories(self, memory_list):
        self.sendMessage('call:tablet.ControlPanel.setMemoryList|%s' % json.dumps(memory_list))

    def set_list_of_sessions(self, session_list):
        self.sendMessage('call:tablet.ControlPanel.setSessionList|%s' % json.dumps(session_list))
    # ============================================

    # ============= TABLET GAME ==================
    def init_tablet_game(self, filepath=None, data=None, wait_for_underworlds=False):
        time.sleep(1)
        _data = None
        if filepath:
            with open(filepath) as _tablet_file:
                _data = json.load(_tablet_file)
        if data:
            _data = data

        if _data:
            if not self._im._test_mode:
                if wait_for_underworlds:
                    self._uwd.loadScene(_data)
                else:
                    Thread(target=self._uwd.loadScene, args=(_data,)).start()

            self.sendMessage("call:tablet.WebSocket.loadScene|" + json.dumps(_data) + "")

            tablet_objects = {}
            for _obj in _data["loadable_objects"]:
                if _obj["id"].startswith("m_"):
                    tablet_objects.update({_obj["id"]: Move_State.Static})

            return tablet_objects
        else:
            return None

    def get_current_scene(self):
        self.sendMessage('call:%s.getCurrentScene' % TCPClient.STR_TABLETGAME)

    def move_object(self, _data):
        self.sendMessage('call:%s.moveObject|%s' % (TCPClient.STR_TABLETGAME, json.dumps(_data)))

    def highlight_objects(self, obj_list):
        _data = {"ids": obj_list}
        self.sendMessage('call:%s.hintObject|%s' % (TCPClient.STR_TABLETGAME, json.dumps(_data)))

    def prepare_scene(self):
        self.sendMessage('call:%s.prepareScene' % TCPClient.STR_TABLETGAME)

    def goto_scene(self):
        self.sendMessage('call:%s.gotoScene' % TCPClient.STR_TABLETGAME)

    def unhighlight_objects(self, obj_list):
        _data = {"ids": obj_list}
        self.sendMessage('call:%s.hintRObject|%s' % (TCPClient.STR_TABLETGAME, json.dumps(_data)))

    def remove_all_highlights(self):
        self.sendMessage('call:%s.hintRAllObjects' % TCPClient.STR_TABLETGAME)

    def animate_objects(self, data):
        self.sendMessage('call:%s.performAnimation|%s' % (TCPClient.STR_TABLETGAME, json.dumps(data)))

    def add_arrow(self, obj_type, source_obj, destination_obj):
        self.sendMessage('call:%s.addArrow|{"type":%s, "source":%s, "destination":%s}' % (TCPClient.STR_TABLETGAME, obj_type, source_obj, destination_obj))

    def add_stars(self):
        self.sendMessage('call:%s.showStars' % TCPClient.STR_TABLETGAME)

    def remove_stars(self):
        self.sendMessage('call:%s.hideStars' % TCPClient.STR_TABLETGAME)

    def show_map(self):
        self.sendMessage('call:%s.showMap' % TCPClient.STR_TABLETGAME)

    def show_recap(self):
        self.sendMessage('call:%s.showRecap' % TCPClient.STR_TABLETGAME)        

    def add_object(self, obj_list):
        _data = {"ids": obj_list}
        self.sendMessage('call:%s.showObject|%s' % (TCPClient.STR_TABLETGAME, json.dumps(_data)))

    def remove_object(self, obj_list):
        _data = {"ids": obj_list}
        self.sendMessage('call:%s.hideObject|%s' % (TCPClient.STR_TABLETGAME, json.dumps(_data)))

    def lock_objects(self, obj_list):
        _data = {"ids": obj_list}
        self.sendMessage('call:%s.makeStatic|%s' % (TCPClient.STR_TABLETGAME, json.dumps(_data)))

    def unlock_objects(self, obj_list):
        _data = {"ids": obj_list}
        self.sendMessage('call:%s.makeMovable|%s' % (TCPClient.STR_TABLETGAME, json.dumps(_data)))

    def enable_object(self, obj_id):
        self.sendMessage('call:%s.enableObject|%s' % (TCPClient.STR_TABLETGAME, obj_id))

    def enable_objects(self, obj_list):
        _data = {"ids": obj_list}
        self.sendMessage('call:%s.enableObject|%s' % (TCPClient.STR_TABLETGAME, json.dumps(_data)))

    def give_object_IDs(self, obj):
        self.callback_obj.object_ids_received = False
        self.sendMessage('call:%s.giveObjectIDs|%s' % (TCPClient.STR_TABLETGAME, json.dumps(obj)))
        while not self.callback_obj.object_ids_received:
            time.sleep(0.01)
        return self.callback_obj.received_object_ids

    def disable_objects(self, obj_list):
        _data = {"ids": obj_list}
        self.sendMessage('call:%s.disableObject|%s' % (TCPClient.STR_TABLETGAME, json.dumps(_data)))
    # ============================================

    # ============ OUTPUT MANAGER ================
    def init_output_man(self, file_path, child_name):
        self.sendMessage("call:%s.load_session|%s" % (TCPClient.STR_OUTPUTMANAGER, file_path))
        time.sleep(0.5)
        self.sendMessage("call:%s.set_child_name|%s" % (TCPClient.STR_OUTPUTMANAGER, child_name))

    def give_task(self, task_id, sub_task_id, difficulty_lvl, criterium, is_test):
        self.sendMessage('call:%s.give_task|{"task": %s, "subtask": %s, "difficulty": %s, "type": "%s", "is_test": %s }' % (TCPClient.STR_OUTPUTMANAGER, task_id, sub_task_id, difficulty_lvl, criterium, str(is_test).lower()))

    def give_feedback(self, task_result):
        self._im._feedback_count += 1
        self.sendMessage("call:%s.give_feedback|%s" % (TCPClient.STR_OUTPUTMANAGER, json.dumps(task_result)))

    def request_answer(self, data):
        self.sendMessage("call:%s.request_answer|%s" % (TCPClient.STR_OUTPUTMANAGER, json.dumps(data)))

    def interrupt_output(self, explanation):
        self.sendMessage("call:%s.interrupt_output|%s" % (TCPClient.STR_OUTPUTMANAGER, explanation))

    # not used yet
    def give_break(self, break_activity_id):
        self.sendMessage("call:%s.give_break|%s" % (TCPClient.STR_OUTPUTMANAGER, break_activity_id))

    def resume_interaction(self):
        self.sendMessage("call:%s.resume_interaction|" % TCPClient.STR_OUTPUTMANAGER)

    def provide_help(self, data):
        self.sendMessage("call:%s.give_help|%s" % (TCPClient.STR_OUTPUTMANAGER, json.dumps(data)))

    def grab_attention(self):
        self.sendMessage("call:%s.grabAttention|" % TCPClient.STR_OUTPUTMANAGER)
    # ============================================

    # =============== BROADCAST ==================
    def log_child_information(self, data):
        self.sendMessage("call:tablet.*.log_child_information|%s" % json.dumps(data))
    # ============================================
