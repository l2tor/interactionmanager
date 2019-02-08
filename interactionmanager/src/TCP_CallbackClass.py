import json
# import logging
from enums import Move_State


class CallbackClass:

    def __init__(self, sock, interaction_manager, underworlds, logger):
        self._sock = sock
        self.logger = logger
        self._perception_data = None
        self._im = interaction_manager
        self._uwd = underworlds
        self._last_touch_pos = None
        self.object_ids_received = False
        self.received_object_ids = {}
        self._memory = None

    def set_memory(self, memory):
        self._memory = memory

    # ================ Tablet Game ================
    def setCurrentScene(self, sender, data):
        """Receives a dump of the current scene."""
        _data = json.loads(data)
        print _data
        self._im._scene_dump = _data

    def touchDown(self, sender, data):
        """Child started to touch something on the Tablet."""
        _data = json.loads(data)
        self._im._child_is_dragging = True
        self._last_touch_pos = _data
        if self._sock.acceptTouchObjs and len(_data["id"]) > 0:
            self._im._touched_objects.append(_data["id"])

        if self._sock.acceptTouchObjs or self._sock.acceptSpRel:
            self._im.remove_object_highlights()

        try:
            if self._sock.acceptSpRel and not self._sock.movable_obj and self._im._tablet_objects[_data["id"]] == Move_State.Movable:
                self._sock.lock_objects([x for x in self._im.obj_list if _data["id"] not in x])
                self._sock.movable_obj = _data["id"]
        except KeyError, e:
            print 'KeyError - reason "%s"' % str(e)

    def touchUp(self, sender, data):
        """Child stopped to touch something on the Tablet."""
        print "touchUp", data
        _data = json.loads(data)
        self._im._child_is_dragging = False
        if not self._im.mode_2D:
            if self._last_touch_pos["id"] != _data["id"] or self._last_touch_pos["position"] != _data["position"]:
                self._uwd.updtObjPos(_data)
            if self._sock.acceptSpRel and "s_" not in _data["id"]:
                self._im._rel_data.append(self._uwd.getRel())

    def objectsCollided(self, sender, data):
        """Some objects on the tablet collided."""
        print "objectsCollided", data
        if self._sock.acceptCollision:
            _data = json.loads(data)
            self._im._collision_data.append(_data)
    # =============================================

    # ============== Output Manager ===============
    def log_output_information(self, sender, data):
        """Accepts all messages from the OM to be logged in the memory."""
        try:
            _data = json.loads(data)
            print _data
            _data["data"]["timestamp"] = _data["data"]["timestamp"]-self._memory.get_interaction_timestamp()
            self._im._current_subtask.add_output_information(_data["key"], _data["data"])
        except Exception,ex:
            print ex.message

    def accept_answer(self, sender, data):
        """Indicator that answers can now be accepted and validated."""
        self._im._accept_answer = True

    def output_completed(self, sender, data):
        """Robot finished his output"""
        self._im._output_finished = True
        self._im._wait_for_output = False

    def give_task_completed(self, sender, data):
        """Robot finished the task description."""
        self._im._task_completed = True

    def feedback_completed(self, sender, data):
        """Robot finished feedback."""
        self._im._feedback_count -= 1
        if self._im._feedback_count == 0:
            self._im._feedback_completed = True

    def request_answer_completed(self, sender, data):
        """Robot finished requesting an answer."""
        self._im._request_answer_completed = True

    def help_completed(self, sender, data):
        """Robot finished with giving help."""
        self._im._provide_help_completed = True

    def tablet_output_completed(self, sender, data):
        """Tablet output finished - Not used yet."""
        pass

    def sensor_touched(self, sender, data):
        """One of the robot sensors has been touched."""
        if self._sock.acceptTouchSensor:
            _data = json.loads(data)
            self._im._touched_sensors.append(_data["id"])

    def move_object(self, sender, data):
        """Request to move some objects on the tablet."""
        _data = json.loads(data)

        to_move_id = _data["id"]
        if "_" in to_move_id and not "m_" in to_move_id:
            to_move_id = "m_" + to_move_id
        else:
            for _obj in self._im._tablet_objects:
                if to_move_id in _obj and self._im._tablet_objects[_obj] != Move_State.f_Static:
                    to_move_id = _obj
                    break
        _data["id"] = to_move_id
        self._im._last_correct_object = to_move_id
        self._sock.move_object(_data)
    # =============================================

    # ============== Control Panel ================
    def CPinit(self, sender, data):
        """Start-Button has been pressed --> Load chosen session file and start interaction."""
        self._im.setup(json.loads(data))

    def CPinitContinue(self, sender, data):
        """Continue-Button has been pressed --> Load session of last crash and search for checkpoints to start with."""
        self._im.setup(json.loads(data), _continue=True)

    def vadFake(self, sender, data):
        """Correct word has been spoken by the child"""
        if self._sock.acceptVAD:
            self.logger.info("vadFake")
            self._sock.acceptVAD = False
            self._im._vad_detected = True
            self._im._vad_correct = True

    def vadFakeFalse(self, sender, data):
        """Wrong word has been spoken by the child"""
        if self._sock.acceptVAD:
            self.logger.info("vadFakeFalse")
            self._im._vad_detected = True
            self._im._vad_correct = False

    def create_memory(self, sender, data):
        """Create a new memory for the new child."""
        self._im.create_memory(json.loads(data), self._im.im_logger)

    def change_memory(self, sender, data):
        """Update values in the memory."""
        self._im.change_name_memory(json.loads(data), self._im.im_logger)

    def get_memories(self, sender, data):
        """Return a list of all memory files."""
        data = self._im.get_list_of_memories()
        self._sock.set_list_of_memories(data)

    def get_sessions(self, sender, data):
        """Return a list of all session files."""
        data = self._im.get_list_of_sessions()
        self._sock.set_list_of_sessions(data)

    def get_updated_information(self, sender, data):
        """Return all information to be updated on the GUI."""
        data = self._im.get_list_of_memories()
        self._sock.set_list_of_memories(data)
        data = self._im.get_list_of_sessions()
        self._sock.set_list_of_sessions(data)
        data = self._im.get_memory_infos()
        if data:
            self._sock.memory_loaded(data)

    def load_memory(self, sender, data):
        """Load the given memory file."""
        self._im.load_memory(data, self._im.im_logger)

    def unload_memory(self, sender, data):
        """Unload the current memory file."""
        self._im.unload_memory(self._im.im_logger)

    def delete_memory(self, sender, data):
        """Delete the selected memory file."""
        _data = json.loads(data)
        self._im.delete_memory(_data["filename"], self._im.im_logger)

    def pause_interaction(self, sender, data):
        """Pause the current interaction."""
        self._im._game_paused = True

    def resume_interaction(self, sender, data):
        """Resume the current interaction."""
        self._im._game_paused = False

    def exit_interaction(self, sender, data):
        """Quit the current interaction."""
        self._im._game_paused = True
        self._im._exit_interaction = True

    def set_lang(self, sender, data):
        """Sets the current language combination."""
        self._im.set_lang(data)
    # =============================================

    # =============== KinectTool ==================
    def vadStop(self, sender, data):
        """Child stopped talking."""
        if self._sock.acceptVAD:
            self.logger.info("vadStop")
        # if self._sock.acceptVAD:
        #     self._sock.acceptVAD = False
        #     self._im._vad_detected = True

    def vadStart(self, sender, data):
        """Child started talking."""
        if self._sock.acceptVAD:
            self.logger.info("vadStart")
    # =============================================

    # =============== Dummy or not used anymore ==================
    def log_child_information(self, sender, data):
        """dummy callback, never used. Result of broadcast."""
        pass

    def updtSpRel(self, sender, data):
        """Old update function before the integration of underworlds and IM"""
        print "updateSpRel", data
        if self._sock.acceptSpRel:
            _data = json.loads(data)
            self._im._rel_data.append(_data)

    def setObjectIDs(self, sender, data):
        """?!?"""
        _data = json.loads(data)
        self.received_object_ids = {}
        for obj in _data:
            if obj not in self._im._tablet_objects:
                self.received_object_ids.update({obj: Move_State.Static})
        self.object_ids_received = True
