import argparse
import json
from time import sleep, time
from memory import InteractionMemory, Task, SubTask
import logging
from TCP_Client import TCPClient
import os
from os import listdir
from os.path import isfile, join
import log_formatter as lf
from datetime import datetime
from threading import Lock, Thread
from enums import Move_State, EnumEncoder, as_enum

UWDS_PATH = '..\\..\\..\\underworlds\\clients'
import sys
if not UWDS_PATH in sys.path:
    sys.path.append(UWDS_PATH)

from l2tor_uwds_client import l2tor_uwds_client

int_manager = None
memory = None
conn_man = None
underworlds = None
logFormatter = None
uwds_status_thread = None


class InteractionManager:
    LOG_DIR = "C:/l2tor/logs/"
    SESSION_DIR = "../../../DataModel/sessions/interactionmanager/"
    SCENE_DIR = "../../../DataModel/tablet_scenes/"
    SCENE_CHECKPOINT_DIR = "../../../DataModel/tablet_scenes/checkpoints/"

    def __init__(self, logger, mode):
        """
            Constructor to initialize the interaction manager. It loads the lesson-files from the hard drive and
            initialize the child model.
        """
        self.im_logger = logger

        # general variables for the class
        self._running = False
        self._continue = False
        self._threads = []
        self._current_subtask = None
        self._current_domain = None
        self._current_session = None
        self._checkpoint_mode = mode == 'checkpoint'
        self._scene_dump = None
        self._start_with_task = -1
        self._start_with_subtask = -1

        # stores a history which objects can be used for fulfilling a "move_object" task
        self._objects_to_enable = []
        self._highlighted_objects = []

        self.mode_2D = False

        # Feedback from Outputmanager
        self._output_finished = False
        self._request_answer = False
        self._wait_for_output = False
        self._accept_answer = False

        self._task_completed = False
        self._feedback_completed = True
        self._feedback_count = 0
        self._neg_feedback_count = 0
        self._request_answer_completed = False
        self._request_answer_count = 0
        self._game_paused = False
        self._help_given = False
        self._provide_help_completed = False
        self._exit_interaction = False

        # variables with data from perception, tablet_game and underworlds
        self._vad_detected = False
        self._vad_correct = False
        self._touched_objects = []
        self._touched_sensors = []
        self._rel_data = []
        self._collision_data = []
        self._tablet_objects = {}
        self._from_town = True
        self._child_is_dragging = False

        # [JAN] For being able to reposition objects after they were interacted with
        self._last_correct_object = None

        self._test_mode = False

    def main(self):
        # wait until start
        while not self._running:
            sleep(1)

        session_information = {"task_id": "-", "task_type": "-", "scene": "town-map"}
        # go through all tasks
        for task in self._c_session["tasks"]:
            if self._continue and self._start_with_task > int(task["task_id"]):
                continue
            if "is_test" in task:
                self._test_mode = task["is_test"]

            if (not self._continue and not memory.has_task(task["task_id"])) or (self._continue and self._start_with_subtask < 0):
                # create a memory entry for the current task
                _is_test = False
                if "is_test" in task:
                    _is_test = task["is_test"]
                new_task = Task(task["task_id"], _is_test, time()-memory.get_interaction_timestamp(), im_logger)
            else:
                new_task = memory.get_task(task["task_id"])

            # go through all subtasks
            for sub_task in task["subtasks"]:
                if self._continue:
                    if self._start_with_subtask > int(sub_task["subtask_id"]):
                        continue
                    conn_man.prepare_scene()
                    sleep(1.5)
                    checkpoint_data = self._get_checkpoint_data()
                    session_information["scene"] = checkpoint_data["scene_name"]
                    self._last_correct_object = checkpoint_data["last_answer"]

                    # inform output manager and tablet game
                    self._tablet_objects = conn_man.init_tablet_game(data=checkpoint_data["scene"], wait_for_underworlds=True)
                    self._tablet_objects = checkpoint_data["tablet_objects"]

                    self._from_town = False
                    sleep(3)
                    conn_man.movable_obj = None
                    self._continue = False

                session_information["task_id"] = task["task_id"]
                task_type = sub_task["exit_criteria"][0]["type"]

                self._request_answer_count = 0
                self._neg_feedback_count = 0

                if self._checkpoint_mode and task_type in ["OBJECT_SELECT_CRITERIUM", "OBJECT_MOVE_CRITERIUM",
                                                           "OBJECT_COLLISION_CRITERIUM", "SENSOR_TOUCH_CRITERIUM",
                                                           "VOICE_ACTIVATION_CRITERIUM"] and not self._from_town:
                    self.im_logger.info("Try to create checkpoint ... ")
                    conn_man.get_current_scene()
                    self.im_logger.info("Requesting data from tablet game.")
                    while not self._scene_dump and not isinstance(self._scene_dump, dict):
                        sleep(0.1)
                    self.im_logger.info("Scene dump received!")
                    self._write_dump_to_hdd(task["task_id"], sub_task["subtask_id"], session_information["scene"], self._last_correct_object)

                # create for each sub_tasks a memory entry
                self._current_subtask = SubTask(sub_task["subtask_id"], time()-memory.get_interaction_timestamp(),
                                       task_type, im_logger)
                session_information["task_id"] += "." + sub_task["subtask_id"]

                # tablet actions required?
                if "tablet_display_actions" in sub_task.keys():
                    scene = self._process_tablet_display_actions(sub_task["tablet_display_actions"])
                    if scene:
                        session_information["scene"] = scene

                # indicator if a task has been successfully finished
                valid = False
                # if loop is visited first time AND this subtask has output --> send it to the output-manager
                first_try = True

                # while not all tasks fulfilled
                while not valid:
                    if self._exit_interaction:
                        self.im_logger.info("bye bye!")
                        close_interaction()
                        return

                    if self._game_paused:
                        first_try = True
                        sleep(0.1)
                        continue
                    valid = True

                    if "exit_criteria" in sub_task:
                        session_information["task_type"] = sub_task["exit_criteria"][0]["type"]
                    else:
                        session_information["task_type"] = "-"
                    conn_man.send_session_information(session_information)

                    # if there is some text and it is the first visit of this loop --> msg to output-manager
                    if sub_task["has_output"] and first_try:
                        # for the case the task requires touching some items -> empty the list,
                        # so that no old "touches" will be used to valid the task
                        self._touched_objects = []
                        # send the task to the outputmanager ...
                        conn_man.give_task(task["task_id"], sub_task["subtask_id"], 1, sub_task["exit_criteria"][0]["type"], self._test_mode)
                        self._wait_for_output = True
                        self._output_finished = self._task_completed = False

                        # ... and wait for it to be finished, so that the validation can be started
                        try:
                            if sub_task["exit_criteria"][0]["type"] in ["RESPONSE_DELAY_CRITERIUM",
                                                                        "VOICE_ACTIVATION_CRITERIUM",
                                                                        "OUTPUT_FINISH_CRITERIUM",
                                                                        "SENSOR_TOUCH_CRITERIUM"]:
                                self._wait_for_task_finished()
                            else:
                                self._wait_for_accept_answer()
                        except KeyError, ex:
                            self.im_logger.error("Task does not have a type!")

                        if len(self._highlighted_objects) > 0:
                            conn_man.highlight_objects(self._highlighted_objects)

                        # reset some variables
                        first_try = False

                    feedback_data = self._check_exit_criteria(sub_task["exit_criteria"])

                    # only to be sure that the task description is really finished
                    self._wait_for_task_finished()

                    if feedback_data and not self._test_mode:
                        valid = feedback_data["valid"]
                        if feedback_data["answer"]:
                            # wait for interrupt to be finished to go on
                            while self._request_answer:
                                sleep(0.5)
                            # positive or negative feedback
                            self._output_finished = False
                            conn_man.give_feedback(feedback_data)
                            self._wait_for_feedback_finished()

                    if self._game_paused:
                        valid = False
                        continue
                    if self._help_given:
                        data = {"type": sub_task["exit_criteria"][0]["type"]}
                        good_id = ''

                        if data["type"] in ["OBJECT_SELECT_CRITERIUM", "OBJECT_MOVE_CRITERIUM", "OBJECT_COLLISION_CRITERIUM"]:
                            if data["type"] == "OBJECT_SELECT_CRITERIUM": 
                                objs = sub_task["exit_criteria"][0]["object_id"].split(",")
                                obj = objs[0]
                                if len(objs) > 1 and objs[0].startswith("dummy"):
                                    obj = objs[1]
                            else:
                                obj = sub_task["exit_criteria"][0]["obj_1"]

                            good_id = "s_" + obj

                            for obj_id, obj_value in self._tablet_objects.iteritems():
                                if "m_" + obj in obj_id:
                                    if data["type"] == "OBJECT_SELECT_CRITERIUM" or obj_value != Move_State.f_Static:
                                        good_id = obj_id
                                        break

                        if data["type"] == "OBJECT_SELECT_CRITERIUM":
                            data["obj_1"] = good_id
                        elif data["type"] in ["OBJECT_MOVE_CRITERIUM", "OBJECT_MOVE_CRITERIUM_2D"]:
                            if data["type"] == "OBJECT_MOVE_CRITERIUM":
                                data["obj_1"] = good_id
                            else:
                                data["obj_1"] = sub_task["exit_criteria"][0]["obj_1"]
                            data["rel"] = sub_task["exit_criteria"][0]["relationship"]
                            data["obj_2"] = sub_task["exit_criteria"][0]["obj_2"]
                        elif data["type"] == "VOICE_ACTIVATION_CRITERIUM":
                            data["word"] = sub_task["exit_criteria"][0]["target_word"]
                        elif data["type"] == "OBJECT_COLLISION_CRITERIUM":
                            data["obj_1"] = good_id
                            if "m_" + sub_task["exit_criteria"][0]["obj_2"] in self._tablet_objects.keys():
                                data["obj_2"] = "m_" + sub_task["exit_criteria"][0]["obj_2"]
                            else:
                                data["obj_2"] = "s_" + sub_task["exit_criteria"][0]["obj_2"]

                        self.provide_help(data)
                        valid = True
                        self._help_given = False

                    new_task.add_subtask(self._current_subtask)
                    #self._current_subtask = None
                memory.add_task(self._current_domain, self._current_session, new_task)
                memory.checkpoint()
                memory.snapshot()

        InteractionManager.unload_memory(self.im_logger)

    def _get_checkpoint_data(self):
        """
            This function reads the checkpoint and parse it to json dict.

            :return: If checkpoint file exists returns a Json dict with the checkpoint data else NONE
        """
        _filepath = "%sdomain_%s_session_%s_task_%s_subtask_%s.json" % (InteractionManager.SCENE_CHECKPOINT_DIR,
                                                                        self._current_domain, self._current_session,
                                                                        self._start_with_task, self._start_with_subtask)
        _data = None
        if os.path.exists(_filepath):
            with open(_filepath) as _checkpoint_file_data:
                _data = json.load(_checkpoint_file_data)
                _data["tablet_objects"] = json.loads(_data["tablet_objects"], object_hook=as_enum)
        return _data

    def _write_dump_to_hdd(self, task_id, sub_task_id, scene_name, last_correct_answer):
        """
             This function try to write a checkpoint for the current task. The checkpoint includes a scene dump and also
             the status of all tablet objects (static or movable) at that time.

            :param task_id: The ID of the current task.
            :param sub_task_id: The ID of the current sub-task
            :param scene_name: Name of the scene to be shown on the CP after loading the checkpoint.
            :param last_correct_answer: The last correct answer given also will be stored to reproduce some
                   object snapping actions after loading the checkpoint.
        """
        if not os.path.exists(InteractionManager.SCENE_CHECKPOINT_DIR):
            self.im_logger.info("Checkpoint-Directory wasn't found and has been created!")
            os.makedirs(InteractionManager.SCENE_CHECKPOINT_DIR)

        _data = {"scene": self._scene_dump,
                 "tablet_objects": json.dumps(self._tablet_objects, cls=EnumEncoder),
                 "scene_name": scene_name, "last_answer": last_correct_answer}

        _filepath = "%sdomain_%s_session_%s_task_%s_subtask_%s.json" % (InteractionManager.SCENE_CHECKPOINT_DIR,
                                                                        self._current_domain, self._current_session,
                                                                        task_id, sub_task_id)
        try:
            with open(_filepath, 'w') as outfile:
                json.dump(_data, outfile)
            self.im_logger.info("Checkpoint written successfully.")
        except IOError:
            self.im_logger.info("Error occured while writing checkpoint-file.")

        self._scene_dump = None

    def _process_tablet_display_actions(self, actions):
        """
            This function parses all tablet change actions and sends it to the tablet.

            :param actions: List of all things to change on the GUI
            :return the name/type of the scene
        """
        scene = None
        # go through all actions to be send to the tablet
        for key in actions.keys():
            # load new scene
            if "scene" in key:
                # load town?
                if "town" in actions[key].lower():
                    self._from_town = True
                    conn_man.show_map()
                    scene = "town-map"
                elif "recap" in actions[key].lower():
                    conn_man.show_recap()
                    scene = "recap"
                # load a scene from file and send it to the tablet
                else:
                    if not self._from_town:
                        conn_man.prepare_scene()
                        sleep(1.5)
                    # inform output manager and tablet game
                    file_path = InteractionManager.SCENE_DIR + actions[key] + ".json"
                    self._tablet_objects = conn_man.init_tablet_game(filepath=file_path)
                    scene = actions[key]
                    self._from_town = False
                    sleep(3)
                    conn_man.movable_obj = None
            elif "objects_enabled" in key:
                self._objects_to_enable = actions[key]
            elif "objects_highlighted" in key:
                try:
                    for obj in actions[key]:
                        obj_id = obj["object_id"]
                        if "m_" + obj_id in self._tablet_objects:
                            obj_id = "m_" + obj_id
                        else:
                            obj_id = "s_" + obj_id
                        self._highlighted_objects.append(obj_id)
                except KeyError:
                    self.im_logger.error("Missing information at %s." % key)

            elif "remove_highlights" in key:
                conn_man.remove_all_highlights()
            elif "objects_move" in key:
                try:
                    for obj_mov in actions[key]:
                        to_move_id = obj_mov["object_id"]
                        if to_move_id == "previous_target":
                            to_move_id = self._last_correct_object
                        elif "_" in to_move_id:
                            to_move_id = "m_" + to_move_id
                        else:
                            for _obj in self._tablet_objects:
                                if to_move_id in _obj:
                                    to_move_id = _obj
                                    break
                        _data = {"id": to_move_id, "position": {"x": float(obj_mov["x"]), "y": float(obj_mov["y"]), "z": float(obj_mov["z"])},
                                 "timeout": float(obj_mov["speed"]), "loop": obj_mov["loop"]}

                        conn_man.move_object(_data)
                        self._last_correct_object = to_move_id
                except KeyError:
                    self.im_logger.error("Missing information at %s." % key)
            elif "objects_animated" in key:
                try:
                    conn_man.animate_objects({key: actions[key]})
                except KeyError:
                    self.im_logger.error("Missing information at %s." % key)
            else:
                add_obj_list = []
                rmv_obj_list = []
                for obj in actions[key]:
                    _obj_id = obj["object_id"]
                    obj_id = ""
                    if self._from_town or "previous_target" == _obj_id:
                        obj_id = _obj_id
                    if "_" in _obj_id and _obj_id != "previous_target":
                        obj_id = "m_" + _obj_id
                        if obj_id not in self._tablet_objects:
                            obj_id = "s_" + _obj_id

                    # add objects (show them)
                    if key == "objects_added":
                        # simply add an obj of a specific type
                        if "confetti" in obj["object_id"]:
                            conn_man.add_stars()
                        else:
                            add_obj_list.append(obj_id)

                    # remove objects (hide)
                    elif key == "objects_removed":
                        if "confetti" in obj["object_id"]:
                            conn_man.remove_stars()
                        elif obj_id == "previous_target":
                            self._tablet_objects[self._last_correct_object] = Move_State.f_Static
                            rmv_obj_list.append(self._last_correct_object)
                        else:
                            self._tablet_objects[obj_id] = Move_State.f_Static
                            rmv_obj_list.append(obj_id)
                if len(add_obj_list) > 0:
                    conn_man.add_object(add_obj_list)
                if len(rmv_obj_list) > 0:
                    conn_man.remove_object(rmv_obj_list)
        return scene

    def remove_object_highlights(self):
        if len(self._highlighted_objects) > 0:
            conn_man.unhighlight_objects(self._highlighted_objects)
            self._highlighted_objects = []

    def _check_exit_criteria(self, exit_criteria):
        """
            This function checks all exit_criteria to be checked for the current task and returns a data-structure for
            feedback

            :param exit_criteria: List of all exit criteria
            :return: Return a dict with the keys "valid", "answer", "type" and "ADD_INFO"
        """
        feedback_data = None
        # check all exit_criteria to be finished
        self.im_logger.info("exit-criteria: %s" % exit_criteria)
        for criteria in exit_criteria:
            # get current type of exit criteria
            exit_criteria = criteria["type"]

            self.mode_2D = (exit_criteria == "OBJECT_MOVE_CRITERIUM_2D")

            # exit_criteria for voice activation:
            # listen to the VAD Service and wait for some seconds if a timeout occurs --> request_answer
            # could not be answered wrong!
            if exit_criteria == "VOICE_ACTIVATION_CRITERIUM":
                feedback_data = self._check_voice_activation_criterium(int(criteria["timeout_ms"]),
                                                                       criteria["target_word"])

            elif exit_criteria == "SENSOR_TOUCH_CRITERIUM":
                feedback_data = self._check_sensor_touch_criterium(5000, criteria["sensor"])

            # simply wait for an answer and continue regardless if there was an answer or not
            elif exit_criteria == "RESPONSE_DELAY_CRITERIUM":
                # for this criteria no extra feedback is required
                self._check_response_delay_criterium(int(criteria["timeout_ms"]))

            # check whether the right objects has been touched or not
            elif exit_criteria == "OBJECT_SELECT_CRITERIUM":
                e_obj_list = []
                t_objs_list = criteria["object_id"].split(",")
                for obj in t_objs_list:
                    if "_" in obj:
                        obj_id = "m_" + obj
                        e_obj_list.append(obj_id)
                    else:
                        if self.mode_2D:
                            self._tablet_objects.update(conn_man.give_object_IDs(obj))
                        for obj_id in self._tablet_objects.keys():
                            if obj in obj_id:
                                e_obj_list.append(obj_id)
                feedback_data = self._check_object_select_criterium(5000,  t_objs_list, e_obj_list)

            # check whether obj_1 has the right spatial relation to obj_2 after child response
            elif exit_criteria in ["OBJECT_MOVE_CRITERIUM", "OBJECT_MOVE_CRITERIUM_2D"]:
                self.obj_list = self._create_object_list_with_prefix(criteria["obj_1"])
                feedback_data = self._check_object_move_criterium(5000, exit_criteria, criteria["obj_1"], self.obj_list,
                                                                  criteria["relationship"], criteria["obj_2"])

            elif exit_criteria == "OBJECT_COLLISION_CRITERIUM":
                self.obj_list = self._create_object_list_with_prefix(criteria["obj_1"])
                feedback_data = self._check_object_collision_criterium(8000, criteria["obj_1"], self.obj_list,
                                                                       criteria["obj_2"])

        return feedback_data

    def _create_object_list_with_prefix(self, obj_1):
        """
            If obj_1 only describes one specific object, the prefix m_ will be added and it will be added to the list.
            If obj_1 describes a type-group of objects, all objects will be found, prefix m_ will be added to the id
            and the ids will be added to the resulting list.

            :param obj_1: id of one objects (bread_1) or a type-group of objects (bread)
            :return: list of ids which has to be checked for the task
        """
        obj_list = []
        # is it one object or a group of objects?
        if "_" in obj_1:
            # if one objects --> generate id string
            obj_id = "m_" + obj_1

            if obj_id in self._tablet_objects:
                # if this object isn't fixed forever
                if self._tablet_objects[obj_id] != Move_State.f_Static:
                    obj_list.append(obj_id)
                    self._tablet_objects[obj_id] = Move_State.Movable
            else:
                self._tablet_objects.update({obj_id: Move_State.Movable})
        else:
            if self.mode_2D:
                self._tablet_objects.update(conn_man.give_object_IDs(obj_1))
            for obj_id in self._tablet_objects.keys():
                if obj_1 in obj_id and self._tablet_objects[obj_id] != Move_State.f_Static:
                    obj_list.append(obj_id)
                    self._tablet_objects[obj_id] = Move_State.Movable
        return obj_list

    def _check_object_collision_criterium(self, timeout, obj_1, obj_1_list, obj_2):
        """
            Check whether 2 objects collided.

            :param timeout: THe time to wait until an answer will be requested.
            :param obj_1: object or group-name of objects (flour_1 or flour)
            :param obj_1_list: the list of all objects which can be used for the task e.g. [flour_1, flour_2, ..]
            :param obj_2: The id of the object with which it the dragged objects should collide e.g. bowl

            :return: True   if criterium is fulfilled
                     False  else
        """
        self.im_logger.info("start check_object_collision_criterium")

        _timestamp = time()

        # init some result variables
        valid = answer = False
        feedback_data = None
        self._collision_data = []
        im_logger.info(obj_1_list)

        # make all target-objects movable
        if not conn_man.movable_obj:
            conn_man.unlock_objects(obj_1_list)

        # accept collisions from the tablet game
        conn_man.acceptCollision = True

        while not answer:
            # prepare timer and check spatial relations until timeout
            start_time = time()
            while (time() - start_time) * 1000 < timeout:
                self._help_given = (self._neg_feedback_count == 2)

                if self._game_paused or self._help_given or self._exit_interaction:
                    conn_man.lock_objects(obj_1_list)
                    conn_man.movable_obj = None
                    conn_man.acceptCollision = False
                    return None

                # if a request for answer output is currently running --> reset timer
                if not self._task_completed or not self._feedback_completed:
                    start_time = time()

                if self._task_completed and not self._feedback_completed and self._child_is_dragging:
                    conn_man.interrupt_output(False)

                self.im_logger.info("[ANSWER]task-type=object_collision_criterium, timer=%s, target-objs= (%s, %s) , collision-data= %s" % ((time() - start_time), obj_1, obj_2, self._collision_data))

                # if a collision update has been send by tablet game --> the child did something
                if len(self._collision_data) > 0:
                    # an answer has been detected
                    answer = True
                    # interrupt the output to give feedback
                    conn_man.interrupt_output(False)
                else:
                    sleep(0.1)
                    continue

                info_to_send = self._collision_data[:]
                _col = self._collision_data.pop(0)
                object_to_lock = None
                for obj in obj_1_list:
                    if _col["obj_1"] in obj and obj_2 in _col["obj_2"]:
                        valid = True
                        object_to_lock = obj

                self.im_logger.info("answer= %s,valid= %s" % (answer, valid))
                # if a valid answer has been found
                if valid:
                    conn_man.acceptCollision = False
                    # drop all other collision updates
                    self._collision_data = []
                    # make all objects static again
                    conn_man.lock_objects(obj_1_list)
                    for _obj_1 in obj_1_list:
                        # if the object is in the right state, it can be locked "forever"
                        if _obj_1 == object_to_lock:
                            self._tablet_objects[_obj_1] = Move_State.f_Static
                            self._last_correct_object = _obj_1
                        else:
                            self._tablet_objects[_obj_1] = Move_State.Static

                obj_2_full = "s_" + obj_2
                if "m_" + obj_2 in self._tablet_objects.keys():
                    obj_2_full = "m_" + obj_2

                add_info = {"obj_1": object_to_lock, "obj_2": obj_2_full}
                feedback_data = {"valid": valid, "answer": answer, "type": "OBJECT_COLLISION_CRITERIUM", "ADD_INFO": add_info}

                _data = {"correctness": valid, "timestamp": time() - memory.get_interaction_timestamp(),
                         "correct_answer": [obj_1, obj_2_full], "given_answer": info_to_send,
                         "rel_timestamp": time()-_timestamp}

                if answer:
                    self._current_subtask.add_answer(_data)

                if valid:
                    break

                if answer:
                    # only to be sure that the task description is really finished
                    self._wait_for_task_finished()

                    # wait for interrupt to be finished to go on
                    while self._request_answer:
                        sleep(0.1)

                    answer = False
                sleep(0.1)

            # if there was no answer --> request an answer
            if not answer:
                if self._request_answer_count == 2:
                    self._help_given = True
                    conn_man.lock_objects(obj_1_list)
                    conn_man.movable_obj = None
                    conn_man.acceptSpRel = False
                    return None

                data = {"type": "OBJECT_COLLISION_CRITERIUM", "obj_1": obj_1, "obj_2": obj_2, "answering": self._child_is_dragging}
                self.request_answer(data)
                self._request_answer_count += 1

        # don't accept any spatial relation update anymore
        conn_man.acceptCollision = False
        if valid:
            conn_man.movable_obj = None

        self.im_logger.info("end check_object_collision_criterium")

        # return result
        return feedback_data

    def _check_object_select_criterium(self, timeout, target_objects, enable_objects):
        """
            This function checks if one of the given objects has been touched.

            :param timeout: Time to wait until an answer will be requested
            :param target_objects: The list of objects to be touched.

            :return: True   if touched objects is in the target_objects list
                     False  else
        """
        self.im_logger.info("start check_object_select_criterium")

        _timestamp = time()

        # init some result variables
        valid = answer = False
        add_info = {}
        memory_data = {}
        feedback_data = None
        self._touched_objects = []
        request_answer_limit = 2
        if self._test_mode:
            request_answer_limit = 3

        # accept touches
        conn_man.acceptTouchObjs = True

        if len(self._objects_to_enable) > 0:
            for obj in self._objects_to_enable:
                conn_man.enable_object(obj["object_id"])
            self._objects_to_enable = []
        else:
            conn_man.enable_objects(enable_objects)

        while not answer:
            # listen to all information about touched objects until timeout
            start_time = time()
            while (time() - start_time) * 1000 < timeout:
                self._help_given = (self._neg_feedback_count == 2)
                if self._game_paused or self._help_given or self._exit_interaction:
                    conn_man.acceptTouchObjs = False
                    return None
                # if a request for answer output is currently running --> reset timer
                if self._request_answer or not self._task_completed or not self._feedback_completed:
                    start_time = time()

                self.im_logger.info("[ANSWER]task-type=object_select_criterium, timer=%s, target-objs= %s touched-obj= %s" % ((time() - start_time), target_objects, self._touched_objects))

                # if to many objects has been touched
                if len(self._touched_objects) >= 5:
                    # give feedback --> no no just touch the goal object
                    # conn_man.interrupt_output(False)
                    # give some negative feedback and explain that only one object should be touched
                    add_info.update({"comment": "too many objects"})
                    # an answer has been given so delete the touched objects list and start over again
                    # answer = True
                    # clear the cache for recently touched objects
                    # self._touched_objects = []
                    # break

                if len(target_objects) > 0 and "screen" in target_objects[0]:
                    if len(self._touched_objects) > 0:
                        valid = answer = True
                        feedback_data = None

                        memory_data = {"correctness": valid, "timestamp": time() - memory.get_interaction_timestamp(),
                                       "correct_answer": target_objects, "given_answer": self._touched_objects[:],
                                       "rel_timestamp": time() - _timestamp}

                        self._touched_objects = []
                else:
                    # go through the list of all objects
                    for t_obj in target_objects:
                        # go through all touched objects
                        # TODO: Make sure this loop will not explode if objects will be added during the iteration
                        for touched_object in self._touched_objects:
                            if "screen" in touched_object:
                                continue
                            # answer found
                            answer = True
                            # interrupt output manager
                            conn_man.interrupt_output(False)
                            # check whether the answer is valid or not
                            if t_obj.strip() in touched_object:
                                # give feedback --> alright! that was the right answer!
                                valid = True
                                self._last_correct_object = touched_object
                                conn_man.disable_objects(enable_objects)
                                break

                        # if valid answer has been found in advance --> break the loop and go on
                        if valid:
                            break

                    add_info.update({"target_objects": target_objects, "touched_objects": self._touched_objects[:]})
                    feedback_data = {"valid": valid, "answer": answer, "type": "OBJECT_SELECT_CRITERIUM", "ADD_INFO": add_info}

                    memory_data = {"correctness": valid, "timestamp": time() - memory.get_interaction_timestamp(),
                                   "correct_answer": target_objects, "given_answer": self._touched_objects[:],
                                   "rel_timestamp": time()-_timestamp}

                    self._touched_objects = []

                if answer:
                    self._current_subtask.add_answer(memory_data)

                if valid:
                    if not self._feedback_completed:
                        conn_man.interrupt_output(False)
                    break

                if answer:
                    if self._test_mode:
                        conn_man.interrupt_output(False)
                        return feedback_data

                    # only to be sure that the task description is really finished
                    self._wait_for_task_finished()

                    # wait for interrupt to be finished to go on
                    while self._request_answer:
                        sleep(0.1)

                    if self._feedback_completed:
                        # negative feedback and go on checking
                        self._feedback_completed = False
                        conn_man.give_feedback(feedback_data)
                        self._neg_feedback_count += 1
                        self.im_logger.info("Feedback count " + str(self._feedback_count))

                    answer = False
                sleep(0.1)

            # request answer
            if not answer:
                if self._request_answer_count == request_answer_limit:
                    if not self._test_mode:
                        self._help_given = True
                    conn_man.acceptTouchObjs = False
                    return None

                # request answer
                data = {"type": "OBJECT_SELECT_CRITERIUM", "obj_1": target_objects[0]}
                self.request_answer(data)
                self._request_answer_count += 1

        conn_man.acceptTouchObjs = False
        self.im_logger.info("end check_object_select_criterium")

        return feedback_data

    def _check_object_move_criterium(self, timeout, type_str, obj_1, obj_1_list, rel, obj_2):
        """
            This function checks whether an object has been placed at the right spot or not.
            Example: Elephant_1 in Cage_1

            :param timeout: Time until the system actively requests an answer form the child.
            :param type_str: check object_move_criterium or object_move_criterium_2D
            :param obj_1: Object_id or Type to be moved.
            :param obj_1_list: All ids of objects which can be used to fulfill the task.
            :param rel: Spatial relation of obj_1 to obj_2 to be fulfilled.
            :param obj_2: Object_id or Type of the second object to which the first object have to be placed.

            :return: True   If spatial relation of obj_1 and obj_2 is correct
                     False  Else
        """
        self.im_logger.info("start check_" + type_str)
        _timestamp = time()

        # init some result variables
        valid = answer = False
        feedback_data = None

        # make all target-objects movable
        if not conn_man.movable_obj:
            conn_man.unlock_objects(obj_1_list)

        # accept information from underworld (prevent queuing outdated information)
        conn_man.acceptSpRel = True

        while not answer:
            # prepare timer and check spatial relations until timeout
            start_time = time()
            while (time() - start_time) * 1000 < timeout:
                self._help_given = (self._neg_feedback_count == 2)

                if self._game_paused or self._help_given or self._exit_interaction:
                    conn_man.lock_objects(obj_1_list)
                    conn_man.movable_obj = None
                    conn_man.acceptSpRel = False
                    return None

                # if a request for answer output is currently running --> reset timer
                if self._request_answer or not self._task_completed or not self._feedback_completed:
                    start_time = time()

                if self._task_completed and not self._feedback_completed and self._child_is_dragging:
                    conn_man.interrupt_output(False)

                self.im_logger.info("[ANSWER]task-type=%s, timer=%s, target-SpRel= (%s, %s, %s) , spRel-data= %s" % (type_str, (time() - start_time), obj_1, rel, obj_2, self._rel_data))
                # if a spatial relation update has been send by underworld --> the child did something

                if len(self._rel_data) > 0:
                    # an answer has been detected
                    answer = True
                    # interrupt the output to give feedback
                    conn_man.interrupt_output(False)
                else:
                    sleep(0.1)
                    continue

                # validate the answer from the child
                valid, object_to_lock = self._validate_relations(obj_1_list, rel, obj_2, self._rel_data[0])
                # and drop the oldest relation update
                self._rel_data.pop(0)

                self.im_logger.info("answer= %s,valid= %s" % (answer, valid))
                # if a valid answer has been found
                if valid:
                    # drop all other spatial relation updates
                    self._rel_data = []
                    # make all objects static again
                    conn_man.lock_objects(obj_1_list)
                    for _obj_1 in obj_1_list:
                        # conn_man.lock_object(_obj_1)
                        # if the object is in the right state, it can be locked "forever"
                        if _obj_1 == object_to_lock:
                            self._tablet_objects[_obj_1] = Move_State.f_Static
                            self._last_correct_object = _obj_1
                        else:
                            self._tablet_objects[_obj_1] = Move_State.Static

                add_info = {"target_object": obj_1, "target_sprel": rel, "goal_object": obj_2, "moved_object": conn_man.movable_obj}
                feedback_data = {"valid": valid, "answer": answer, "type": type_str, "ADD_INFO": add_info}

                _data = {"correctness": valid, "timestamp": time() - memory.get_interaction_timestamp(),
                         "correct_answer": [obj_1, rel, obj_2], "given_answer": conn_man.movable_obj,
                         "rel_timestamp": time()-_timestamp}
                if answer:
                    self._current_subtask.add_answer(_data)

                if valid:
                    break

                if answer:

                    # only to be sure that the task description is really finished
                    self._wait_for_task_finished()

                    # wait for interrupt to be finished to go on
                    while self._request_answer:
                        sleep(0.1)

                    # negative feedback and go on checking
                    conn_man.lock.acquire()
                    self._feedback_completed = False
                    conn_man.lock.release()
                    conn_man.give_feedback(feedback_data)
                    self._neg_feedback_count += 1
                    answer = False

                sleep(0.1)

            # if there was no answer --> request an answer
            if not answer:
                if self._request_answer_count == 2:
                    self._help_given = True
                    conn_man.lock_objects(obj_1_list)
                    conn_man.movable_obj = None
                    conn_man.acceptSpRel = False
                    return None

                data = {"type": type_str, "obj_1": obj_1, "rel": rel, "obj_2": obj_2, "answering": self._child_is_dragging}
                self.request_answer(data)
                self._request_answer_count += 1

        # don't accept any spatial relation update anymore
        conn_man.acceptSpRel = False
        if valid:
            conn_man.movable_obj = None

        self.im_logger.info("end check_" + type_str)

        return feedback_data

    def _check_response_delay_criterium(self, timeout):
        """
            This function is waiting for a specific time, while the child can but has not to answer.
            After timeout is reached or voice has been detected (interrupt),
            the dialog flow continue with the next task.

            :param timeout: Time to wait until continuing the dialog flow.

            :return: True
        """
        self.im_logger.info("start check_response_delay_criteria")
        _timestamp = time()
        # listen for some voice
        conn_man.acceptVAD = True

        # wait for timeout or vad event
        start_time = time()
        while (time() - start_time) * 1000 < timeout:
            if self._game_paused or self._exit_interaction:
                conn_man.acceptVAD = False
                self._vad_detected = self._vad_correct = False
                return None

            self.im_logger.info("Voice detected?=%s, timer=%s" % (self._vad_detected, (time() - start_time)))
            # check if some voice has been detected
            if self._vad_detected:
                # interrupt the output to go on in the next step
                conn_man.interrupt_output(False)
                break
            sleep(0.1)
        # don't listen anymore
        conn_man.acceptVAD = False

        _data = {"correctness": self._vad_detected, "timestamp": time() - memory.get_interaction_timestamp(),
                 "correct_answer": "", "given_answer": "", "rel_timestamp": time()-_timestamp}
        self._current_subtask.add_answer(_data)

        # reset indicator variable for VAD
        self._vad_detected = self._vad_correct = False

        self.im_logger.info("end check_response_delay_criteria")

    def _check_sensor_touch_criterium(self, timeout, sensor_id):
        """
            This function checks if one of the given robot sensor has been touched.

            :param timeout: Time to wait until an answer will be requested
            :param sensor_id: The lid of the sensor to be touched on the robot

            :return: True   if touched sensor equals the given sensor_id
                     False  else
        """
        self.im_logger.info("start check_sensor_touch_criteria")
        _timestamp = time()
        valid = False
        answer = False
        feedback_data = None
        add_info = {}
        request_answer_limit = 2

        # accept information form VAD service
        conn_man.acceptTouchSensor = True

        while not valid:
            # prepare timeout timer
            start_time = time()
            # wait for timeout or vad event
            while (time() - start_time) * 1000 < timeout:
                self._help_given = (self._neg_feedback_count == 2)
                if self._game_paused or self._help_given or self._exit_interaction:
                    conn_man.acceptTouchSensor = False
                    self._touched_sensors = []
                    return None

                # reset timeout timer if the current task is REPEATED to get an answer, so that
                # the child get the same amount of time to answer again (interrupt also possible)
                if self._request_answer or not self._task_completed or not self._feedback_completed:
                    # reset timer
                    start_time = time()

                self.im_logger.info("check_sensor_touch_criteria?=%s, timer=%s" % (self._request_answer, (time() - start_time)))

                # go through the list of all objects
                for touched_sensor in self._touched_sensors:
                    # answer found
                    answer = True
                    # interrupt output manager
                    conn_man.interrupt_output(False)
                    # check whether the answer is valid or not
                    if sensor_id.strip() in touched_sensor:
                        # give feedback --> alright! that was the right answer!
                        valid = True
                        break

                add_info.update({"target_sensor": sensor_id, "touched_sensors": self._touched_sensors[:]})
                feedback_data = {"valid": valid, "answer": answer, "type": "SENSOR_TOUCH_CRITERIUM",
                                 "ADD_INFO": add_info}

                _data = {"correctness": valid, "timestamp": time() - memory.get_interaction_timestamp(),
                         "correct_answer": sensor_id, "given_answer": self._touched_sensors[:],
                         "rel_timestamp": time()-_timestamp}
                if answer:
                    self._current_subtask.add_answer(_data)

                self._touched_sensors = []

                if valid:
                    if not self._feedback_completed:
                        conn_man.interrupt_output(False)
                    break

                if answer:
                    #if self._test_mode:
                    #    return feedback_data

                    # only to be sure that the task description is really finished
                    self._wait_for_task_finished()

                    # wait for interrupt to be finished to go on
                    while self._request_answer:
                        sleep(0.1)

                    if self._feedback_completed:
                        # negative feedback and go on checking
                        self._feedback_completed = False
                        conn_man.give_feedback(feedback_data)
                        self._neg_feedback_count += 1
                        self.im_logger.info("Feedback count " + str(self._feedback_count))

                    answer = False
                sleep(0.1)

            # request answer
            if not answer:
                if self._request_answer_count == request_answer_limit:
                    #if not self._test_mode:
                    self._help_given = True
                    conn_man.acceptTouchSensor = False
                    return None

                # request answer
                data = {"type": "SENSOR_TOUCH_CRITERIUM", "obj_1": sensor_id}
                self.request_answer(data)
                self._request_answer_count += 1

        conn_man.acceptTouchSensor = False
        self._touched_sensors = []
        self.im_logger.info("end check_sensor_touch_criterium")

        return feedback_data

    def _check_voice_activation_criterium(self, timeout, target_word):
        """
            This function is listening for voice activity until a timeout happened and then actively requests an answer.

            :param timeout: Time to listen for an answer.
            :param target_word: The word to be pronounced by the child.

            :return: if VAD: True
                       else: False
        """
        self.im_logger.info("start check_voice_activation_criteria")
        _timestamp = time()

        # reset valid variable --> valid if voice has been detected
        valid = False
        answer = False
        feedback_data = None

        # accept information form VAD service
        conn_man.acceptVAD = True

        while not valid:
            # prepare timeout timer
            start_time = time()
            # wait for timeout or vad event
            while (time() - start_time) * 1000 < timeout:
                self._help_given = (self._neg_feedback_count == 2)
                if self._game_paused or self._help_given or self._exit_interaction:
                    conn_man.acceptVAD = False
                    self._vad_detected = False
                    self._vad_correct = False
                    return None
                # reset timeout timer if the current task is REPEATED to get an answer, so that
                # the child get the same amount of time to answer again (interrupt also possible)
                if self._request_answer or not self._task_completed or not self._feedback_completed:
                    # reset timer
                    start_time = time()

                self.im_logger.info("Request_answer?=%s, timer=%s" % (self._request_answer, (time() - start_time)))
                # hsa some voice been detected?
                if self._vad_detected:
                    self.im_logger.info("Voice detected!")

                    # child said at least something
                    answer = True
                    # task is valid or not
                    valid = self._vad_correct
                    # interrupt the outputmanager (e.g. when currently the task is repeated)
                    conn_man.interrupt_output(False)
                    self._vad_detected = self._vad_correct = False
                    conn_man.acceptVAD = not valid

                    add_info = {"target_word": target_word}
                    feedback_data = {"valid": valid, "answer": answer, "type": "VOICE_ACTIVATION_CRITERIUM",
                                     "ADD_INFO": add_info}

                    _data = {"correctness": valid, "timestamp": time()-memory.get_interaction_timestamp(),
                             "correct_answer": target_word, "given_answer": "", "rel_timestamp": time()-_timestamp}

                    if answer:
                        self._current_subtask.add_answer(_data)

                    # break timeout look
                    if valid:
                        break

                    # FEEDBACK
                    # only to be sure that the task description is really finished
                    self._wait_for_task_finished()

                    # wait for interrupt to be finished to go on
                    while self._request_answer:
                        sleep(0.1)

                    if self._feedback_completed:
                        # negative feedback and go on checking
                        self._feedback_completed = False
                        conn_man.give_feedback(feedback_data)
                        self._neg_feedback_count += 1
                        self.im_logger.info("Feedback count" + str(self._feedback_count))

                    answer = False

                    # self.im_logger.info("Voice detected!")
                    # # task is valid
                    # valid = True
                    # # interrupt the outputmanager (e.g. when currently the task is repeated)
                    # conn_man.interrupt_output(False)
                    # # don't accept further information from VAD service
                    # conn_man.acceptVAD = False
                    # # reset variable for the next time
                    # self._vad_detected = False
                    # self._vad_correct = False
                    #
                    # # break timeout look
                    # break

                # wait 100ms until check again
                sleep(0.1)

            self.im_logger.info("end check_voice_activation_criteria")

            # if still not valid --> no answer was detected --> request a response from child
            if not answer:
                if self._request_answer_count == 2:
                    self._help_given = True
                    conn_man.acceptVAD = False
                    self._vad_detected = False
                    self._vad_correct = False
                    return None

                # request answer from child
                data = {"type": "VOICE_ACTIVATION_CRITERIUM", "word": target_word}
                self.request_answer(data)
                self._request_answer_count += 1

        # don't listen anymore
        conn_man.acceptVAD = False

        return feedback_data

    def _validate_relations(self, obj_1_list, rel, obj_2, cdata):
        """
            This function checks whether obj_1 or one of the objects of type obj_1 is at the right spot regarding obj_2
            and the spatial relation rel.

            :param obj_1_list: The object (or group of objects) to be placed by the child.
            :param rel: The spatial relation which obj_1 should have referred to obj_2
            :param obj_2: The second object.
            :param cdata: All information from Underworlds to check the goal.
            :return: True, Obj_xy      If Obj_xy is at the right place
                     False, None       Else
        """
        negation = False
        if "NOT_" in rel:
            negation = True
            rel = rel.replace("NOT_", "")

        # iter over all objects which can be used to solve the task
        for obj_1 in obj_1_list:
            valid = True
            # look into the spRel data if the current object is inside
            for rel_obj_1 in (x for x in cdata.keys() if x == obj_1):
                    rel_list = cdata[rel_obj_1]
                    for _rel in rel_list:
                        if negation:
                            if _rel["relation"] == rel and obj_2 in _rel["obj_2"]:
                                valid = False
                        else:
                            if rel == "in":
                                rel_2 = "weaklyCont"
                                if _rel["relation"] in [rel, rel_2] and obj_2 in _rel["obj_2"]:
                                    return True, obj_1
                            else:
                                if _rel["relation"] == rel and obj_2 in _rel["obj_2"]:
                                    return True, obj_1
            if negation and valid:
                return valid, obj_1
        return False, None

    def request_answer(self, data):
        """
            Sends a message to the output-manager, that there was no answer and an answer has to be requested.

            :param data: task dependent information about the request in a dict
        """
        self.im_logger.info("Requesting answer ...")
        # send request
        conn_man.request_answer(data)
        self._output_finished = False
        self._request_answer = True

        # and start a thread which waits for completion
        t = Thread(target=self._wait_for_request_output, args=())
        t.start()

        # append thread to a list so that it can be cleanly ended
        self._threads.append(t)

    def provide_help(self, data):
        """
            This function sends a request to the output manager to provide help for the child to solve the task.

            :param data: The data to be send to the output manager so that it can provide help for the current task.
        """
        # waiting for all feedbacks to be finished.
        while not self._feedback_completed:
            sleep(0.1)

        self.im_logger.info("Provide help ...")

        conn_man.provide_help(data)
        self._output_finished = False
        self._provide_help_completed = False

        while not self._provide_help_completed:
            sleep(0.1)
        
        # Lock some stuff
        if data["type"] in ["OBJECT_MOVE_CRITERIUM", "OBJECT_COLLISION_CRITERIUM"]:
            self._tablet_objects[data["obj_1"]] = Move_State.f_Static
            self._last_correct_object = data["obj_1"]

        # If we are coming from the town into a scene after giving help to "open" the scene, we need to switch pages!
        if self._from_town:
            conn_man.goto_scene()

    def _wait_for_request_output(self):
        """
            This function waits until after a request_answer an output_finished has been send.
        """
        lock = Lock()

        # wait for request to be finished
        while not self._request_answer_completed:
            sleep(0.1)

        # set variables
        lock.acquire()
        self._request_answer = False
        self._request_answer_completed = False
        lock.release()

        self.im_logger.info("Request answer finished.")

    def _wait_for_task_finished(self):
        """
            This function simply waits for an "output_finished" message from output manager.
        """
        while not self._task_completed:
            sleep(0.1)

    def _wait_for_feedback_finished(self):
        """
            This function simply waits for an "output_finished" message from output manager.
        """
        conn_man.lock.acquire()
        self._feedback_completed = False
        conn_man.lock.release()
        while not self._feedback_completed:
            sleep(0.1)

    def _wait_for_output_finished(self):
        """
            This function simply waits for an "output_finished" message from output manager.
        """
        while not self._output_finished:
            sleep(0.1)
        self._output_finished = False

    def _wait_for_accept_answer(self):
        """
            This function simply waits for an "output_finished" message from output manager.
        """
        while not self._accept_answer:
            sleep(0.1)
        self._accept_answer = False

    def setup(self, data, _continue=False):
        """
            This function sets up the IM. It triggers loading all necessary files as well as
            it starts the main loop of the flow.

            :param data: Name of the session_file
            :param _continue: should the current interaction be continued?
        """
        self._load_files(data["session_file"])
        session_data = data["session_file"].replace(".json", "").split("_")
        self._current_domain = session_data[1]
        self._current_session = session_data[3]
        memory.add_session(self._current_domain, self._current_session, time())
        memory.set_cue("lang_combo", data["lang_combo"])
        # memory.set_cue("condition", data["condition"])
        self._running = True
        self._continue = _continue

        _data = {"name": memory.get_cue("name"), "id": memory.get_cue("id"), "lang_combi": data["lang_combo"],
                 "condition": memory.get_cue("condition"), "domain": self._current_domain, "session": self._current_session}
        self.im_logger.info("[CHILD_INFO]%s" % json.dumps(_data))
        underworlds.writeChildInfoToLog(_data)
        conn_man.log_child_information(_data)

    def _load_files(self, session_file):
        """
            This function reads the session file and spread out the information to all other modules.

            :param session_file: The name of the session_file
        """
        self.im_logger.info("Init outputmanager")
        conn_man.init_output_man(session_file, memory.get_cue("phon_name"))

        self.im_logger.info("Loading lesson for IM ...")
        # _path = self._lesson_file["small_scenario"]
        _path = InteractionManager.SESSION_DIR + session_file
        if os.path.exists(_path):
            with open(_path) as _scenario_file_data:
                self._c_session = json.load(_scenario_file_data)
            self.im_logger.info("Lesson file successfully loaded!")
        else:
            self.im_logger.info("Session file doesn't exist!")

    def join_threads(self):
        for t in self._threads:
            t.join()

    @staticmethod
    def get_list_of_sessions():
        abs_path = os.path.abspath(InteractionManager.SESSION_DIR)
        print abs_path
        if os.path.exists(abs_path):
            return [f for f in listdir(abs_path) if isfile(join(abs_path, f))]
        return []

    @staticmethod
    def get_list_of_memories():
        return InteractionMemory.get_list_of_memories()

    @staticmethod
    def create_memory(data, _im_logger):
        """
            This method will create a new memory for a child.

            :param _im_logger: the logger to be used in the memory
            :param data: The ID and Name of a child in a dict.
        """
        global memory
        if memory:
            InteractionManager.unload_memory(_im_logger)
        memory = InteractionMemory(data["id"], data["condition"], data["name"], data["phon_name"], data["L1"],
                                   data["gender"], data["birthday"], data["school"], _im_logger)
        memory.save_to_file()
        #_im_logger.info("[child]%s;;%s" % (memory.get_cue("id"), memory.get_cue("name")))
        # conn_man.memory_loaded([memory.get_cue("id"), memory.get_cue("name"), memory.get_cue("filename")])
        data = InteractionManager.get_list_of_memories()
        conn_man.set_list_of_memories(data)
        InteractionManager.load_memory("", _im_logger, load_new=False)

    @staticmethod
    def delete_memory(filename, _im_logger):
        global memory
        if memory and memory.get_cue("filename") == filename:
            InteractionManager.unload_memory(_im_logger)
        InteractionMemory.delete_memory(filename, _im_logger)
        InteractionMemory.delete_memory("_" + filename, _im_logger)
        conn_man.set_list_of_memories(InteractionMemory.get_list_of_memories())

    @staticmethod
    def change_name_memory(name, _im_logger):
        global memory
        _im_logger.info("Changing name of %s to %s" % (memory.get_cue("name"), name['name']))
        memory.set_cue("name", name['name'])
        memory.save_to_file(new_file=False)

    @staticmethod
    def load_memory(file_name, _im_logger, load_new=True):
        """
            This method will load a memory file from hard drive.

            :param _im_logger: the logger to be used in the memory
            :param file_name: name of the memory file.
            :param load_new: no new memory file should be loaded but the rest should be executed,
        """
        try:
            global memory
            if load_new:
                if memory:
                    InteractionManager.unload_memory(_im_logger)

                memory = InteractionMemory.from_file(file_name, _im_logger)
            if memory:
                conn_man.set_memory(memory)
                _im_logger.info("[child]" + str(memory.get_cue("id")) + ";;" + str(memory.get_cue("name")))

                _last_domain = max([int(x) for x in memory.get_list_of_domains()])
                _last_session = max([int(x) for x in memory.get_list_of_sessions(_last_domain)])

                _session_data = ["-1", "-1", "", "clean"]
                if _last_domain != -1 and _last_session != -1:
                    unfinished_session_found, last_task, last_sub_task = InteractionManager.check_last_session_finished(_last_domain, _last_session)
                    _session_file = "domain_%s_session_%s.json" % (_last_domain, _last_session)
                    if unfinished_session_found:
                        next_task, next_subtask = InteractionManager.find_next_checkpoint(_last_domain, _last_session, last_task, last_sub_task)
                        if next_task != -1 != next_subtask:
                            int_manager._start_with_task = next_task
                            int_manager._start_with_subtask = next_subtask
                            int_manager._current_domain = _last_domain
                            int_manager._current_session = _last_session
                            _session_data = [next_task, next_subtask, _session_file, "true"]
                        else:
                            _session_data = [last_task, last_sub_task, _session_file, "no_point"]
                    elif last_task == -1 == last_sub_task:
                        pass
                    else:
                        _session_data = [last_task, last_sub_task, _session_file, "false"]

                conn_man.send_extended_session_information(_session_data)

                _memory_data = [memory.get_cue("id"), memory.get_cue("name"), memory.get_cue("filename"),
                                memory.get_cue("lang_combo"), memory.get_cue("condition")]
                conn_man.memory_loaded(_memory_data)
        except Exception, e:
            _im_logger.error("Error loading memory: %s" % str(e))

    @staticmethod
    def find_next_checkpoint(domain, session, task, sub_task):
        """
            This function try to find the next best checkpoint before the crash.

            :param domain: Last domain before crash.
            :param session: Last session before crash.
            :param task: Last task before crash.
            :param sub_task: Last sub-task before crash.

            :return: task_id and sub_task_id for the last checkpoint before the crash.
        """
        current_task = task
        get_next_best = False
        while current_task > 0:
            sub_task_ids = InteractionManager.find_sub_task_ids(domain, session, current_task)
            for _id in sorted(sub_task_ids, key=int, reverse=True):
                if _id <= sub_task or get_next_best:
                    return current_task, _id
            current_task -= 1
            get_next_best = True
        # no checkpoint found --> start from beginning
        return -1, -1

    @staticmethod
    def find_sub_task_ids(domain, session, task):
        """
            This function try to find the next best checkpoint before the crash.

            :param domain: Last domain before crash.
            :param session: Last session before crash.
            :param task: Last task before crash.

            :return: task_id and sub_task_id for the last checkpoint before the crash.
        """
        subtask_ids = []
        file_str = "domain_%s_session_%s_task_%s" % (domain, session, task)
        _full_path = os.path.realpath(int_manager.SCENE_CHECKPOINT_DIR)
        if os.path.exists(_full_path):
            for filename in os.listdir(_full_path):
                if filename.startswith(file_str):
                    tmp_split = filename.split("_")
                    if len(tmp_split) >= 7:
                        subtask_ids.append(int(tmp_split[7].replace(".json", "")))
        return subtask_ids

    @staticmethod
    def check_last_session_finished(last_domain, last_session):
        """
            This function checks whether there is an incomplete session which has to be continued.

            :param: last_domain: Last domain taught.
            :param: last_session: Last session taught.

            :return: True, task_id, subtask_id if there is a incomplete session
                     False, -1, -1             else
        """
        _tasks = memory.get_tasks_by_session(last_domain, last_session)
        _path = "%sdomain_%s_session_%s.json" % (InteractionManager.SESSION_DIR, last_domain, last_session)
        _session = None
        if os.path.exists(_path):
            with open(_path) as _scenario_file_data:
                _session = json.load(_scenario_file_data)
        if _session:
            _last_session_task = _session["tasks"][-1]
            _last_session_sub_task = _last_session_task["subtasks"][-1]
            if len(_tasks.keys()) > 0:
                _last_task_id = max([int(x) for x in _tasks.keys()])
                _sub_tasks = _tasks[str(_last_task_id)].get_subtasks()
                if len(_sub_tasks.keys()) > 0:
                    _last_subtask_id = max([int(x) for x in _sub_tasks.keys()])
                    if int(_last_session_task["task_id"]) > _last_task_id \
                            or int(_last_session_sub_task["subtask_id"]) > _last_subtask_id:
                        return True, _last_task_id, _last_subtask_id
                    else:
                        return False, 0, 0
                else:
                    return True, _last_task_id, -1
            else:
                return False, -1, -1

    @staticmethod
    def set_lang(data):
        """
            Sets the language pair in the memory of the child.

            :param data: Lang pair from the ControlPanel e.g. ger-eng
        """
        global memory
        memory.set_cue("lang", data)

    @staticmethod
    def unload_memory(_im_logger):
        """
            This function unloads the current memory file.

            :param _im_logger: The current logger.
        """
        global memory
        if memory:
            _im_logger.info("Try to unload current memory %s." % memory.get_cue("filename"))
            memory.save_to_file(new_file=False)
            memory = None
            _im_logger.info("Memory successfully has been unloaded.")
        else:
            _im_logger.info("Unload not possible since no memory is loaded!")
        conn_man.memory_unloaded()

    @staticmethod
    def get_memory_infos():
        """
            This function returns general child information from the memory.

            :return: id, name of the child and also the memory file name as a list of strings
        """
        global memory
        if memory:
            return [memory.get_cue("id"), memory.get_cue("name"), memory.get_cue("filename"), "", ""]
        else:
            conn_man.memory_unloaded()
            return None


def close_interaction():
    """
        Kill all threads and save all data to shut down the interactionmanager
    """
    global int_manager
    int_manager._exit_interaction = True
    int_manager.join_threads()
    uwds_status_thread.join()
    global memory
    global conn_man
    if memory:
        memory.save_to_file()
        memory = None
        conn_man.memory_unloaded()
    if conn_man:
        conn_man.close_connection()
        conn_man = None
    logFormatter.stopReadingLogs()


def setup_logger(name, log_file, format_str, level=logging.INFO):
    """Function setup as many loggers as you want"""
    handler = logging.FileHandler(log_file)
    formatter = logging.Formatter(format_str)
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)

    return logger


def check_uwds_status():
    while not int_manager._exit_interaction:
        try:
            conn_man.send_uwds_status(underworlds.isOnline())
        except Exception, ex:
            conn_man.send_uwds_status(False)
        sleep(3)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", type=str, default="127.0.0.1", help="Connection manager ip address")
    parser.add_argument("--port", type=int, default=1111, help="Connection manager port number")
    parser.add_argument("--mode", type=str, default="normal", help="Defines the mode of the IM. The mode 'checkpoint'"
                                                                       "will allow to create new scene files for all "
                                                                       "checkpoints. (default-mode:normal)")

    try:
        args = parser.parse_args()

        # if log dir doesn't exist ...
        if not os.path.exists(InteractionManager.LOG_DIR):
            # ... create it
            os.makedirs(InteractionManager.LOG_DIR)
        # new log path
        _date_str = datetime.fromtimestamp(time()).strftime('%Y%m%d%H%M%S')
        str_log_file = InteractionManager.LOG_DIR + "im_%s.log" % _date_str
        str_uwds_log_file = InteractionManager.LOG_DIR + "uwds_%s.log" % _date_str
        str_im_uwds_log_file = InteractionManager.LOG_DIR + "im_uwds_%s.log" % _date_str

        # create logger
        _format_str = '%(levelname)s %(relativeCreated)6d %(threadName)s %(message)s (%(module)s.%(lineno)d)'
        logging.basicConfig(filename=str_im_uwds_log_file, level=logging.DEBUG, format=_format_str, filemode='w')
        uwds_logger = setup_logger("uwds_logger", str_uwds_log_file, _format_str, level=logging.DEBUG)
        im_logger = setup_logger("im_logger", str_log_file, _format_str, level=logging.DEBUG)

        logFormatter = lf.LogFormatter(str_log_file, level=lf.DEBUG)
        logFormatter.start()
        im_logger.info("Log initialized")

        # set loggers
        int_manager = InteractionManager(im_logger, args.mode)
        InteractionMemory.im_logger = im_logger
        underworlds = l2tor_uwds_client(uwds_logger)

        # initialize tcp client
        conn_man = TCPClient("interactionmanager", int_manager, underworlds, im_logger, args.ip, args.port)

        uwds_status_thread = Thread(target=check_uwds_status)
        uwds_status_thread.start()

        # start main loop of IM
        int_manager.main()

        close_interaction()

    except KeyboardInterrupt:
        close_interaction()
