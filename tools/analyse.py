
    def get_mean_response_time(self):
        """
            Todo: maybe statistics for each skill, task_difficulty etc.?
            :return:
        """
        rtime = [x.get_answer_time for x in self._memTaskList]
        return sum(rtime)/len(rtime)

    def get_mean_accuracy(self):
        pass
