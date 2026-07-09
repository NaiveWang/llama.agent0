# Agent1 Requirements: Next-Gen Single-Agent (Small / Small-Mid Projects & Long Context)

## Target Scope
Small to small-mid projects, handling long context windows, autonomous file manipulation, and self-correction.

## Core Features & Requirements:

### A. Long Context Window Management
- **Context Pruning & Summarization (Memory Compaction):** Periodically summarize past interactions and compress the memory. Replace detailed chat history of completed tasks with concise summaries (e.g., "Resolved database connection issue in milestone 1 by updating config.py").
- **Structured Memory vs. Linear History:** Replace the single linear chat log with structured memory sections: `current_task_context`, `recent_errors`, `completed_changes`, and `project_overview`.

### B. Project Context & RAG-Lite Indexing
- **Project Context Initialization (Scaffolding Awareness):** Automatically analyze the project environment before starting work. Read `README.md`, `requirements.txt`/`package.json`, and run commands like `tree -L 2` to understand the project structure.
- **RAG-Lite Project File Indexing:** Maintain a lightweight file index (e.g., `project_tree.json` or a list of file paths and their last modified status). Only inject the *relevant* file contents into the LLM's context when a specific file is being discussed or edited.

### C. Direct File Read & Edit Capabilities
- **Direct File Manipulation:** Move beyond generating terminal commands. Implement built-in functions to `read_file(path)` and `edit_file(path, diff)`. The agent should directly read files, generate necessary code changes (using diff or replace patterns), and write the updated file back to the project directory.

### D. Automation & Self-Correction Loop
- **Dependency & Environment Setup Automation:** Detect missing dependencies from error logs (e.g., `ModuleNotFoundError`) and automatically generate and execute the correct installation command (e.g., `pip install -r requirements.txt`).
- **Improved Error Parsing & Self-Correction:** Robustly parse `stdout` and `stderr`. If a command or script fails, extract the specific line number and error type, feed that back into the context, and generate a corrected command or file edit without human intervention.

### E. Pre-Implementation Planning & Review Guardrail
- **Structured Implementation Plan Generation:** Before executing any `read_file`, `edit_file`, or terminal commands, Agent1 must generate a **Structured Implementation Plan** that includes:
  - **Objective:** A restatement of the goal or issue to be resolved.
  - **Steps:** A step-by-step breakdown of what it intends to do.
  - **Files to Touch:** A specific list of files it plans to read or modify.
  - **Commands to Execute:** Any terminal commands or dependency installations it plans to run.
- **User Review (Approval Gate):** The agent **pauses** and presents this Structured Implementation Plan to the user for review via a CLI prompt (e.g., `"[PLAN GENERATED] Please review the implementation plan below. Proceed? [y/n/modify with feedback]:"`).
- **Implementation (Proceed Only After Approval):** If the user approves (or provides valid modifications that the agent incorporates), the agent proceeds to execute the plan (reading files, generating diffs, editing files, and running commands). If the user rejects or provides feedback, the agent goes back to revise the plan based on the input.

### F. Project Structure & Implementation Directory
- **Multi-File Architecture:** Unlike Agent0 (which is a single-file `agent0.py` script), **Agent1 will be implemented under an `agent1/` folder by default**. It requires a multi-file structured architecture, with separate modules/components for:
  - Context management & memory pruning
  - RAG-lite project file indexing
  - Direct file read/edit operations (`read_file`, `edit_file`)
  - Pre-implementation planning & review guardrails
  - LLM interaction & command execution wrappers
