class SharedWorkingMemory:
    def __init__(self, initial_working_memory=None):
        if initial_working_memory is None:
            initial_working_memory = {}
        self._working_memory = initial_working_memory

    def get_working_memory(self):
        return self._working_memory

    def merge_to_working_memory(self, working_memory):
        self._working_memory.update(working_memory)
