import os
from os import listdir
from os.path import isfile, join
import glob
import cPickle as pickle
import copy
import shutil
import json


class AbstractMemory(object):
    def __init__(self):
        self._cues = {}

    def has_cue(self, cue):
        return cue in self._cues

    def set_cue(self, cue, val):
        self._cues[cue] = val

    def get_cue(self, cue):
        if cue in self._cues:
            return self._cues[cue]
        else:
            raise KeyError("Cue unknown")


class InteractionMemory(AbstractMemory):
    MEMORY_PATH = "C:/l2tor/memories/"

    def __init__(self, user_id, condition, user_name, phon_name, lang, gender, birthday, school, logger):
        AbstractMemory.__init__(self)
        self.im_logger = logger
        # self._cues = {}
        # self._cues["id"] = self.get_next_id()
        self._cues["id"] = user_id
        self._cues["name"] = user_name
        self._cues["phon_name"] = phon_name
        self._cues["lang"] = lang
        self._cues["gender"] = gender
        self._cues["birthday"] = birthday
        self._cues["school"] = school
        self._cues["lang_combo"] = None
        self._cues["condition"] = condition
        self._cues["taskList"] = {}
        self._latestTask = 0
        self._latestSubtask = 0
        self._current_domain = None
        self._current_session = None

    @classmethod
    def from_file(cls, filename, _im_logger):
        _data = InteractionMemory.load_file(filename, _im_logger)
        obj = cls(_data["id"],
                  _data["condition"],
                  _data["name"],
                  _data["phon_name"],
                  _data["lang"],
                  _data["gender"],
                  _data["birthday"],
                  _data["school"],
                  _im_logger)

        obj._cues["filename"] = _data["filename"]
        obj._cues["lang_combo"] = _data["lang_combo"]
        #obj._cues["condition"] = _data["condition"]
        for domain in _data["taskList"]:
            obj._cues["taskList"][domain] = {}
            for session in _data["taskList"][domain]:
                obj._cues["taskList"][domain][session] = {}
                obj._cues["taskList"][domain][session]["timestamp"] = \
                    _data["taskList"][domain][session]["timestamp"]
                obj._cues["taskList"][domain][session]["tasks"] = {}
                for task_id in _data["taskList"][domain][session]["tasks"]:
                    if task_id != "timestamp":
                        task = _data["taskList"][domain][session]["tasks"][task_id]
                        obj._cues["taskList"][domain][session]["tasks"][task_id] = Task(task["id"], task["is_test"], task["timestamp"], _im_logger)
                        for subtask_id in task["subtasks"]:
                            obj._cues["taskList"][domain][session]["tasks"][task_id]._cues["subtasks"][subtask_id] = []
                            for subtask in task["subtasks"][subtask_id]:
                                obj._cues["taskList"][domain][session]["tasks"][task_id]._cues["subtasks"][subtask_id].append(SubTask(subtask["id"],subtask["timestamp"],subtask["type"],_im_logger))
                                obj._cues["taskList"][domain][session]["tasks"][task_id]._cues["subtasks"][subtask_id][-1]._cues["answers"] = subtask["answers"]
                                obj._cues["taskList"][domain][session]["tasks"][task_id]._cues["subtasks"][subtask_id][-1]._cues["feedback"] = subtask["feedback"]
                                obj._cues["taskList"][domain][session]["tasks"][task_id]._cues["subtasks"][subtask_id][-1]._cues["request_answer"] = subtask["request_answer"]
                                obj._cues["taskList"][domain][session]["tasks"][task_id]._cues["subtasks"][subtask_id][-1]._cues["give_help"] = subtask["give_help"]
                                obj._cues["taskList"][domain][session]["tasks"][task_id]._cues["subtasks"][subtask_id][-1]._cues["gesture"] = subtask["gesture"]

        print(obj._cues)
        obj.im_logger.info("Memory-File successfully loaded!")
        return obj

    def __getstate__(self):           
        serDict = copy.copy(self.__dict__)
        serDict['im_logger'] = None
        return serDict

    def get_next_id(self):
        mems = self.get_list_of_memories()
        result = -1
        for mem in mems:
            if mem == "snapshot.json":
                continue
            tmp = int(mem.split("_")[-1].replace(".json", ""))
            if tmp > result:
                result = tmp
        return result+1

    def add_session(self, domain, session, timestamp):
        domain = str(domain)
        session = str(session)
        timestamp = timestamp
        if domain not in self._cues["taskList"]:
            self._cues["taskList"][domain] = {}
        if session not in self._cues["taskList"][domain]:
            self._cues["taskList"][domain][session] = {}
        if "timestamp" not in self._cues["taskList"][domain][session]:
            self._cues["taskList"][domain][session]["timestamp"] = [timestamp, ]
        else:
            self._cues["taskList"][domain][session]["timestamp"].append(timestamp)
        if "tasks" not in self._cues["taskList"][domain][session]:
            self._cues["taskList"][domain][session]["tasks"] = {}
        self._current_domain = domain
        self._current_session = session

    def get_list_of_domains(self):
        return self._cues["taskList"].keys() if len(self._cues["taskList"].keys()) > 0 else [-1,]

    def get_list_of_sessions(self, domain):
        if domain == -1:
            return [-1, ]
        return self._cues["taskList"][str(domain)].keys() if len(self._cues["taskList"][str(domain)].keys()) > 0 else [-1,]

    def add_task(self, domain, session, task):
        task_id = task.get_cue("id")
        self._cues["taskList"][str(domain)][str(session)]["tasks"][task_id] = task
        self._latestTask = task_id
        self.snapshot()

    def has_task(self, task_id):
        return task_id in self._cues["taskList"][str(self._current_domain)][str(self._current_session)]["tasks"]

    def get_tasks(self):
        return self._cues["taskList"][str(self._current_domain)][str(self._current_session)]["tasks"]

    def get_tasks_by_session(self, domain, session):
        return self._cues["taskList"][str(domain)][str(session)]["tasks"]

    def get_task(self, task_id):
        return self._cues["taskList"][str(self._current_domain)][str(self._current_session)]["tasks"][task_id]

    def get_interaction_timestamp(self):
        try:
            return self._cues["taskList"][str(self._current_domain)][str(self._current_session)]["timestamp"][-1]
        except KeyError:
            self.im_logger.error("Key Error: Session doesn't exist.")

    def serialize(self):
        pickle.dumps(self)

    def save_to_file(self, new_file=True):
        self.im_logger.info("Try to save Memory-File ...")
        if new_file:
            self._cues["filename"] = "%s_%s.json" % (self._cues["name"], self._cues["id"])
        if not os.path.exists(InteractionMemory.MEMORY_PATH):
            self.im_logger.info("Directory wasn't found and has been created!")
            os.makedirs(InteractionMemory.MEMORY_PATH)

        self._save_to_file(InteractionMemory.MEMORY_PATH + self._cues["filename"])

    def checkpoint(self):
        filename = "_%s_%s_%s-%s.json" % (self._cues["name"], self._cues["id"], self._latestTask,self._latestSubtask)
        self._save_to_file(InteractionMemory.MEMORY_PATH + filename)

    def snapshot(self):
        self._save_to_file("tmp.json")
        shutil.copyfile("tmp.json", InteractionMemory.MEMORY_PATH + "_snapshot.json")

    def _save_to_file(self, filename):
        with open(filename, 'wb') as f:

            memory_info = {}
            memory_info["id"] = self._cues["id"]
            memory_info["name"] = self._cues["name"]
            memory_info["phon_name"] = self._cues["phon_name"]
            memory_info["lang"] = self._cues["lang"]
            memory_info["gender"] = self._cues["gender"]
            memory_info["birthday"] = self._cues["birthday"]
            memory_info["school"] = self._cues["school"]
            memory_info["lang_combo"] = self._cues["lang_combo"]
            memory_info["condition"] = self._cues["condition"]
            memory_info["filename"] = self._cues["filename"]
            memory_info["taskList"] = {}
            for domain in self._cues["taskList"]:
                memory_info["taskList"][domain] = {}
                for session in self._cues["taskList"][domain]:
                    memory_info["taskList"][domain][session] = {}
                    memory_info["taskList"][domain][session]["timestamp"] = self._cues["taskList"][domain][session]["timestamp"]
                    memory_info["taskList"][domain][session]["tasks"] = {}
                    for task_id in self._cues["taskList"][domain][session]["tasks"]:
                        if task_id != "timestamp":
                            memory_info["taskList"][domain][session]["tasks"][task_id] = {}
                            task = self._cues["taskList"][domain][session]["tasks"][task_id]
                            # memory_info["taskList"][domain][session][task_id].append({})
                            memory_info["taskList"][domain][session]["tasks"][task_id]["id"] = task._cues["id"]
                            memory_info["taskList"][domain][session]["tasks"][task_id]["is_test"] = task._cues["is_test"]
                            memory_info["taskList"][domain][session]["tasks"][task_id]["timestamp"] = task._cues["timestamp"]
                            memory_info["taskList"][domain][session]["tasks"][task_id]["subtasks"] = {}
                            for subtask_id in task._cues["subtasks"]:
                                memory_info["taskList"][domain][session]["tasks"][task_id]["subtasks"][subtask_id] = []
                                for subtask in task._cues["subtasks"][subtask_id]:
                                    memory_info["taskList"][domain][session]["tasks"][task_id]["subtasks"][subtask_id].append({})
                                    memory_info["taskList"][domain][session]["tasks"][task_id]["subtasks"][subtask_id][-1]["id"] = subtask._cues["id"]
                                    memory_info["taskList"][domain][session]["tasks"][task_id]["subtasks"][subtask_id][-1]["timestamp"] = subtask._cues["timestamp"]
                                    memory_info["taskList"][domain][session]["tasks"][task_id]["subtasks"][subtask_id][-1]["type"] = subtask._cues["type"]
                                    memory_info["taskList"][domain][session]["tasks"][task_id]["subtasks"][subtask_id][-1]["answers"] = subtask._cues["answers"]
                                    memory_info["taskList"][domain][session]["tasks"][task_id]["subtasks"][subtask_id][-1]["feedback"] = subtask._cues["feedback"]
                                    memory_info["taskList"][domain][session]["tasks"][task_id]["subtasks"][subtask_id][-1]["request_answer"] = subtask._cues["request_answer"]
                                    memory_info["taskList"][domain][session]["tasks"][task_id]["subtasks"][subtask_id][-1]["give_help"] = subtask._cues["give_help"]
                                    memory_info["taskList"][domain][session]["tasks"][task_id]["subtasks"][subtask_id][-1]["gesture"] = subtask._cues["gesture"]

            json.dump(memory_info, f)
        self.im_logger.info("Memory has been saved successfully!")

    @staticmethod
    def load_file(filename, im_logger):
        im_logger.info("Try to load Memory-File ...")
        _path = InteractionMemory.MEMORY_PATH + filename
        _data = None
        if os.path.exists(_path):
            with open(_path, 'rb') as f:
                _data = json.load(f)
            im_logger.info("Memory-File successfully opened!")
        else:
            im_logger.info("Memory-File doesn't exist!")
        return _data

    @staticmethod
    def delete_memory(filename, im_logger):
        im_logger.info("Try to remove memory file %s." % filename)
        tmp_file_split = filename.split(".")
        filename = tmp_file_split[0] + "*.json"
        for f in glob.glob(join(InteractionMemory.MEMORY_PATH, filename)):
            try:
                os.remove(f)
                im_logger.info("File %s successfully removed." % f)
            except Exception, ex:
                im_logger.info("Something went wrong during removing file %s: %s" % (filename, ex))

    @staticmethod
    def get_list_of_memories():
        if os.path.exists(InteractionMemory.MEMORY_PATH):
            return [f for f in listdir(InteractionMemory.MEMORY_PATH)
                    if isfile(join(InteractionMemory.MEMORY_PATH, f)) and not f.startswith("_")]
        return []


class Task(AbstractMemory):

    def __init__(self, task_id, is_test, timestamp, im_logger):
        AbstractMemory.__init__(self)
        # self._cues = {}
        self._cues["id"] = task_id
        self._cues["is_test"] = is_test
        self._cues["subtasks"] = {}
        self._cues["timestamp"] = timestamp

        self.im_logger = im_logger

    def __getstate__(self):           
        serDict = copy.copy(self.__dict__)
        serDict['im_logger'] = None
        return serDict

    def add_subtask(self, subtask):
        subtask_id = subtask.get_cue("id")
        self._latestSubtask = subtask.get_cue("id")
        if subtask_id not in self._cues["subtasks"]:
            self._cues["subtasks"][subtask_id] = []
        self._cues["subtasks"][subtask_id].append(subtask)

    def get_subtasks(self):
        return self._cues["subtasks"]

    def get_subtask(self, subtask_id):
        return self._cues["subtasks"][subtask_id]


class SubTask(AbstractMemory):

    def __init__(self, subtask_id, timestmap, task_type, im_logger):
        AbstractMemory.__init__(self)
        # self._cues = {}
        self._cues["id"] = subtask_id
        self._cues["timestamp"] = timestmap
        self._cues["type"] = task_type
        # Entry: {"correctness": x, "timestamp": "x", "rel_timestamp": "x" "correct_answer": "x", "given_answer": "x"}
        # timestamp = relative to start of interaction
        # rel_timestamp = relative to start of the validation
        self._cues["answers"] = []
        # Entry: {""}
        self._cues["feedback"] = []
        # Entry: {""}
        self._cues["request_answer"] = []
        # Entry: {""}
        self._cues["give_help"] = []
        # Entry: {""}
        self._cues["gesture"] = []

        self.im_logger = im_logger

    def add_answer(self, answer):
        self._cues["answers"].append(answer)

    def add_output_information(self, key, value):
        try:
            self._cues[key].append(value)
        except KeyError:
            self.im_logger.error("Information can not be stored. Invalid information key from Outputmanager.")

    def get_output_information(self, key):
        try:
            return self._cues[key]
        except KeyError:
            self.im_logger.error("Information can not be read. Invalid information key.")

    def get_answers(self):
        return self._cues["answers"]

