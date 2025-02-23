# Project Brief: Adaptive Multi-Agent Coordination with Full Audit Trail

Below is an updated project brief for an **event-sourced OODA loop**, emphasizing that our system does **not** rely on a monolithic, start-to-finish plan. Instead, we treat the “plan” as an emergent artifact, capturing **historical steps**, **current options**, and **the logic for deciding the next best step**. This ensures adaptability when “no plan survives contact with the enemy.”

---

## 1. Overview

Many agentic systems coordinate multiple components—LLMs, tools, and reasoning modules—to solve complex tasks. However, static plans quickly become outdated. In this project, we’ll implement a **loop that continuously observes the environment**, **orients around new information**, **decides the next best step**, and **acts** (the OODA loop). All actions and decisions are recorded as **events** under a single correlation ID, ensuring **end-to-end traceability**.

---

## 2. Objective

1. **Emergent Planning**  
   - Rather than a static plan with a fixed list of steps, we maintain a dynamic record of completed steps, discovered tasks, and potential next steps.  
   - The system picks the *best next step* at each iteration, informed by real-time data and previous successes/failures.

2. **Comprehensive Auditability**  
   - Leverage **event sourcing** to log every key decision or state change.  
   - Use a **root correlation ID** per end-user request, so the entire sequence of events is traceable in chronological order.

3. **Iterative & Resilient**  
   - If a step fails or new constraints appear, the system adapts by updating its list of possible next steps (instead of following a static index in a “plan array”).  
   - The system can re-check environment conditions and prior decisions at each OODA cycle.

---

## 3. General Approach

### 3.1 Key Concepts

- **Task Graph (or Task State)**  
  - Tracks:
    - **Completed steps**: what’s been done.  
    - **Discovered tasks**: newly identified opportunities or subtasks.  
    - **Pending tasks**: potential “next steps” that could be attempted.  
  - This replaces the notion of a single, linear plan. Instead, think of it as a living backlog.

- **OODA Loop with Event Sourcing**  
  1. **Observe**: Collect environment data, user overrides, or new discoveries from previous steps.  
  2. **Orient**: Update the task graph by adding/removing tasks based on new information (e.g., new tasks discovered, old ones invalidated).  
  3. **Decide**: From the pending tasks, select the best next step.  
  4. **Act**: Execute that step, log the result, and record an event with the outcome.

- **Correlation ID**  
  - Each user request gets a unique ID.  
  - All events for that request reference the same ID.  
  - This provides an end-to-end audit trail.

### 3.2 Event Log & Auditability

- Every time we add or remove tasks, pick a next step, or fail/succeed, we record an event in an **immutable event store**.  
- By querying all events with a specific correlation ID, we can reconstruct exactly how the system responded to changes, discovered new tasks, and decided each next step.

---

## 4. Pseudo-code: OODA Loop & Event Logging (Emergent Next Step)

Here’s a revised pseudo-code snippet that **doesn’t rely on a single “getPlanStep(stepIndex)”**. Instead, we maintain a “task graph” (or backlog) and pick the next step at each iteration based on current conditions.

```plaintext
function handleUserRequest(userGoal):
    // (1) Generate Correlation ID
    correlationId = generateUUID()

    // (2) Initialize Task Graph
    // The task graph might start with a single top-level goal or a few discovered tasks
    taskGraph = initializeTaskGraph(userGoal)

    eventStore.record({
        "eventType": "TaskGraphWasInitialized",
        "correlationId": correlationId,
        "timestamp": now(),
        "initialTasks": taskGraph.pendingTasks,
        "reason": "User requested: " + userGoal
    })

    done = false

    while not done:
        // (3) OBSERVE + ORIENT
        // Possibly gather new data from environment or previous step results
        environmentUpdates = senseEnvironment()
        newDiscoveredTasks = discoverNewTasks(environmentUpdates)

        // Update the task graph with newly discovered tasks
        if newDiscoveredTasks not empty:
            taskGraph.pendingTasks += newDiscoveredTasks
            eventStore.record({
                "eventType": "TaskGraphWasUpdated",
                "correlationId": correlationId,
                "timestamp": now(),
                "addedTasks": newDiscoveredTasks,
                "reason": "New tasks discovered"
            })

        // (4) DECIDE: pick the best next step from pending tasks
        nextStep = selectBestNextStep(taskGraph.pendingTasks, environmentUpdates)

        if nextStep is null:
            // Possibly we're done or stuck
            if taskGraph.pendingTasks is empty:
                done = true
                // No more tasks => success if we consider the goal met
                eventStore.record({
                    "eventType": "SystemWasTerminated",
                    "correlationId": correlationId,
                    "timestamp": now(),
                    "status": "success",
                    "summary": "All tasks completed"
                })
            else:
                // We have pending tasks but can’t pick one => could be a deadlock or unsatisfiable state
                eventStore.record({
                    "eventType": "SystemWasTerminated",
                    "correlationId": correlationId,
                    "timestamp": now(),
                    "status": "failure",
                    "summary": "No feasible next step"
                })
            break

        // (5) ACT: Execute the chosen step
        eventStore.record({
            "eventType": "StepWasStarted",
            "correlationId": correlationId,
            "timestamp": now(),
            "taskId": nextStep.id,
            "taskDetails": nextStep
        })

        outcome = executeStep(nextStep)

        if outcome.success:
            eventStore.record({
                "eventType": "StepWasCompleted",
                "correlationId": correlationId,
                "timestamp": now(),
                "taskId": nextStep.id,
                "outcome": "success",
                "result": outcome.data
            })

            // Mark the task as completed
            taskGraph.completedTasks.append(nextStep)
            remove nextStep from taskGraph.pendingTasks

            // Possibly discover follow-up tasks based on the outcome
            followUpTasks = analyzeOutcomeForNewTasks(outcome.data)
            if followUpTasks not empty:
                taskGraph.pendingTasks += followUpTasks
                eventStore.record({
                    "eventType": "TaskGraphWasUpdated",
                    "correlationId": correlationId,
                    "timestamp": now(),
                    "addedTasks": followUpTasks,
                    "reason": "Discovered tasks from outcome"
                })

        else:
            eventStore.record({
                "eventType": "StepDidFail",
                "correlationId": correlationId,
                "timestamp": now(),
                "taskId": nextStep.id,
                "cause": outcome.error
            })

            // We could try to revise our approach, remove or transform the failing task,
            // or mark it as failed for now
            taskGraph.failedTasks.append(nextStep)
            remove nextStep from taskGraph.pendingTasks

            // Possibly discover alternative tasks or a different approach
            alternativeTasks = considerAlternatives(nextStep, outcome.error)
            if alternativeTasks not empty:
                taskGraph.pendingTasks += alternativeTasks
                eventStore.record({
                    "eventType": "TaskGraphWasUpdated",
                    "correlationId": correlationId,
                    "timestamp": now(),
                    "addedTasks": alternativeTasks,
                    "reason": "Alternative approach after failure"
                })

        // Loop continues until done == true or we break from errors
```

### Explanation of Key Points

1. **No Single Plan or Step Index**  
   - We maintain `taskGraph` with `pendingTasks`, `completedTasks`, etc.  
   - Each iteration, we pick whichever pending task is best aligned with the current state.

2. **Observation & Orientation**  
   - We sense changes in the environment (could be user overrides, external data, partial results).  
   - We incorporate newly discovered tasks into the task graph.

3. **Decision**  
   - `selectBestNextStep` is where the system (LLM or rule-based approach) chooses *which* of the pending tasks to do next.

4. **Action**  
   - We execute that single step, record it as started/completed/failed.  
   - We then update the task graph accordingly (remove the task from pending, possibly add new tasks discovered by the outcome).

5. **Termination**  
   - If there are no pending tasks left (and we consider the goal complete), record a success event.  
   - If we can’t pick any next step but still have unhandled tasks, record a failure or deadlock event.

---

## 5. Event List (Revisited for Emergent Approach)

With the above approach, here’s a suggested set of events. Each includes a `correlationId` so you can reconstruct the entire sequence for a single user request:

1. **TaskGraphWasInitialized**  
   - Fired when the system sets up the task graph based on the initial user goal.  
   - Fields: `correlationId`, `initialTasks`, `reason`.

2. **TaskGraphWasUpdated**  
   - Fired when tasks are added/removed/modified due to new discoveries, step failures, or user overrides.  
   - Fields: `correlationId`, `addedTasks`/`removedTasks`, `reason`.

3. **StepWasStarted**  
   - Fired when the system selects a pending task and begins execution.  
   - Fields: `correlationId`, `taskId`, `taskDetails`.

4. **StepWasCompleted**  
   - Fired on successful completion of a task.  
   - Fields: `correlationId`, `taskId`, `outcome`, `result`.

5. **StepDidFail**  
   - Fired when a task fails.  
   - Fields: `correlationId`, `taskId`, `cause`.

6. **UserOverrideWasApplied**  
   - Fired if a user directly modifies the pending tasks or the approach (e.g., skipping certain tasks, forcing new tasks).  
   - Fields: `correlationId`, `overrideAction`, `reason`.

7. **SystemWasTerminated**  
   - Fired when the process ends (success, failure, or user-initiated stop).  
   - Fields: `correlationId`, `status` (`success`, `failure`, `aborted`), `summary`.

*(Optionally, you can still have tool-call events like “ToolCallWasRequested” and “ToolCallWasCompleted” if you want a fine-grained record of external interactions.)*

---

## 6. Conclusion

By **focusing on a “next most important step”** rather than a sequential plan, this design:

- **Adapts** in real-time to new information, changing constraints, and unexpected results.  
- **Maintains a strong audit trail** via event sourcing. We can replay all events by correlation ID to see the emergent “plan” that actually materialized over time.  
- **Keeps decisions local and incremental**. The system re-prioritizes tasks on every loop, so we aren’t locked into a rigid plan that no longer makes sense.

This approach better matches the OODA principle of continuous feedback and flexible response, giving you a robust framework for building agentic systems that thrive amid uncertainty.