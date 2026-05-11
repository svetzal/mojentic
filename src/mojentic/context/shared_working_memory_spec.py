from mojentic.context.shared_working_memory import SharedWorkingMemory


class DescribeSharedWorkingMemory:

    class DescribeGetWorkingMemory:

        def should_return_deep_copy_protecting_top_level(self):
            memory = SharedWorkingMemory(initial_working_memory={"key": "value"})

            returned = memory.get_working_memory()
            returned["key"] = "mutated"

            assert memory._working_memory["key"] == "value"

        def should_return_deep_copy_protecting_nested(self):
            memory = SharedWorkingMemory(initial_working_memory={"a": {"b": 1}})

            returned = memory.get_working_memory()
            returned["a"]["b"] = 99

            assert memory._working_memory["a"]["b"] == 1

        def should_return_empty_dict_when_initialized_with_no_args(self):
            memory = SharedWorkingMemory()

            returned = memory.get_working_memory()

            assert returned == {}

    class DescribeMergeToWorkingMemory:

        def should_merge_top_level_keys(self):
            memory = SharedWorkingMemory(initial_working_memory={"existing": "value"})

            memory.merge_to_working_memory({"new_key": "new_value"})

            assert memory.get_working_memory() == {"existing": "value", "new_key": "new_value"}

        def should_overwrite_existing_key_on_merge(self):
            memory = SharedWorkingMemory(initial_working_memory={"key": "original"})

            memory.merge_to_working_memory({"key": "updated"})

            assert memory.get_working_memory()["key"] == "updated"
