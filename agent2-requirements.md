# Agent2: Multi-Agent Parallel Troubleshooting System (Mid / Large Projects)

## Target Scope
Mid to large projects, complex issues, high automation with milestone-based human verification (no babysitting).

## Core Features & Requirements

### A. Multi-Agent Architecture (1-1 Mapping)
- **Orchestrator (State Machine Manager):** Central brain managing the global `SystemState`, transitioning statuses (`PLANNING`, `TROUBLESHOOTING_ACTIVE`, `CODING`, `TESTING`, `REVIEWING`, `PENDING_HUMAN_APPROVAL`, `COMPLETED`), and enforcing the HITL pause mechanism.
- **Dispatcher / Planner Agent:** Analyzes high-level requests or complex error logs, breaks them down into atomic **Milestones**, and generates **2 to N distinct hypotheses/directions** for parallel troubleshooters.
- **Parallel Troubleshooter Agents (Divergent Thinking):** Specialized investigators assigned specific hypotheses. They execute research, analyze logs, run diagnostics, and continuously write findings/progress to the **Shared State / Knowledge Base**.
- **Synthesizer / Reviewer Agent (Converger):** Reads the Shared State once troubleshooters conclude, cross-validates findings, resolves conflicts, and concludes the best solution or next best action.
- **Coder & Tester/Executor Agents (Auto-Repair Loop):** 
  - *Coder Agent:* Writes/updates code based on synthesized solutions.
  - *Tester/Executor Agent:* Runs code in a sandboxed environment (linters, type checkers, unit tests). Feeds error logs back to the Coder/Synthesizer for an auto-repair loop until tests pass or max-retry is hit.

### B. Shared State (Single Source of Truth)
- **Global Status:** Current workflow status.
- **Milestones List:** Array of milestone objects (id, description, status, done/failed).
- **Troubleshooting Threads:** Array of active thread objects (thread_id, direction_hypothesis, status, findings, proposed_code_changes).
- **Code Changes:** Dictionary mapping file paths to new file contents.
- **Test Results & Logs:** String/array of test outputs, linter errors, and system logs.
- **Synthesizer Report:** Final conclusion or next steps.

### C. Workflow / State Machine Transitions
1. **Issue Submission** → 2. **Dispatcher Phase** (Generate milestones & hypotheses) → 3. **Parallel Troubleshooting Phase** (Concurrent investigation) → 4. **Synthesis Phase** (Resolve & conclude) → 5. **Auto-Repair Loop** (Coder + Tester) → 6. **HITL Pause** (Milestone Review) → 7. **Human Verification** (Web UI approval) → 8. **Resume or Revise**.

### D. Web API & Monitor Hub Integration (Flask)
- **`GET /api/state`:** Returns current `SystemState` for real-time frontend polling.
- **`POST /api/submit_issue`:** Accepts user issue descriptions/error logs, updates state to `planning`, and triggers the Dispatcher.
- **`POST /api/approve_milestone`:** Accepts HITL decisions (approve/reject + feedback), updates state to `executing_next_milestone` or `pending_revision`.
- **Frontend UI (Monitor Watch Hub):** HTML/JS dashboard visualizing current status, active troubleshooting threads with findings, milestone progress, and system logs.
