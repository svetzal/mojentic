import pytest

from mojentic.llm.tools.ephemeral_task_manager.ephemeral_task_list import EphemeralTaskList, TaskStatus


@pytest.fixture
def task_list():
    return EphemeralTaskList()


@pytest.fixture
def populated_task_list():
    task_list = EphemeralTaskList()
    task_list.append_task("Task 1")
    task_list.append_task("Task 2")
    task_list.append_task("Task 3")
    return task_list


class DescribeEphemeralTaskList:

    def should_initialize_with_empty_task_list(self, task_list):
        tasks = task_list.list_tasks()
        assert len(tasks) == 0

    def should_append_task(self, task_list):
        task = task_list.append_task("Test task")

        tasks = task_list.list_tasks()
        assert len(tasks) == 1
        assert tasks[0].id == task.id
        assert tasks[0].description == "Test task"
        assert tasks[0].status == TaskStatus.PENDING

    def should_prepend_task(self, task_list):
        task_list.append_task("Existing task")
        task = task_list.prepend_task("New task")

        tasks = task_list.list_tasks()
        assert len(tasks) == 2
        assert tasks[0].id == task.id
        assert tasks[0].description == "New task"
        assert tasks[0].status == TaskStatus.PENDING

    def should_insert_task_after(self, populated_task_list):
        tasks_before = populated_task_list.list_tasks()
        existing_task_id = tasks_before[1].id

        task = populated_task_list.insert_task_after(existing_task_id, "Inserted task")

        tasks_after = populated_task_list.list_tasks()
        assert len(tasks_after) == 4
        assert tasks_after[2].id == task.id
        assert tasks_after[2].description == "Inserted task"
        assert tasks_after[2].status == TaskStatus.PENDING

    def should_raise_error_when_inserting_after_nonexistent_task(self, task_list):
        with pytest.raises(ValueError) as e:
            task_list.insert_task_after(999, "This should fail")

        assert "No task with ID '999' exists" in str(e.value)

    def should_start_task(self, populated_task_list):
        tasks = populated_task_list.list_tasks()
        task_id = tasks[0].id

        started_task = populated_task_list.start_task(task_id)

        assert started_task.status == TaskStatus.IN_PROGRESS

    def should_raise_error_when_starting_non_pending_task(self, populated_task_list):
        tasks = populated_task_list.list_tasks()
        task_id = tasks[0].id

        populated_task_list.start_task(task_id)

        # Second start should fail
        with pytest.raises(ValueError) as e:
            populated_task_list.start_task(task_id)

        assert f"Task '{task_id}' cannot be started because it is not in PENDING status" in str(e.value)

    def should_complete_task(self, populated_task_list):
        tasks = populated_task_list.list_tasks()
        task_id = tasks[0].id

        # Start the task first
        populated_task_list.start_task(task_id)

        # Now complete it
        completed_task = populated_task_list.complete_task(task_id)

        assert completed_task.status == TaskStatus.COMPLETED

    def should_raise_error_when_completing_non_in_progress_task(self, populated_task_list):
        tasks = populated_task_list.list_tasks()
        task_id = tasks[0].id

        with pytest.raises(ValueError) as excinfo:
            populated_task_list.complete_task(task_id)

        assert f"Task '{task_id}' cannot be completed because it is not in IN_PROGRESS status" in str(excinfo.value)

    def should_clear_tasks(self, populated_task_list):
        populated_task_list.clear_tasks()

        tasks_after = populated_task_list.list_tasks()
        assert len(tasks_after) == 0

    def should_maintain_task_ids_across_operations(self, task_list):
        # Add some tasks
        task1 = task_list.append_task("Task 1")
        task2 = task_list.append_task("Task 2")

        # Start and complete task1
        task_list.start_task(task1.id)
        task_list.complete_task(task1.id)

        # Add another task
        task3 = task_list.append_task("Task 3")

        # Verify all tasks have correct IDs and statuses
        tasks = task_list.list_tasks()
        assert len(tasks) == 3

        # Find tasks by ID
        task1_in_list = next((t for t in tasks if t.id == task1.id), None)
        task2_in_list = next((t for t in tasks if t.id == task2.id), None)
        task3_in_list = next((t for t in tasks if t.id == task3.id), None)

        assert task1_in_list is not None
        assert task2_in_list is not None
        assert task3_in_list is not None

        assert task1_in_list.status == TaskStatus.COMPLETED
        assert task2_in_list.status == TaskStatus.PENDING
        assert task3_in_list.status == TaskStatus.PENDING
