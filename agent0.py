import re
import requests
import json
import os
import subprocess
from typing import Dict, List, Optional

# Color codes for terminal output
SYSTEM_COLOR = "\033[34m"  # Blue
USER_COLOR = "\033[33m"    # Orange
ASSISTANT_COLOR = "\033[32m"  # Green
RESET_COLOR = "\033[0m"

class MemoryManager:
    def __init__(self, memory_file: str = "memory.json"):
        self.memory_file = memory_file
        self.memory: Dict[str, List[str]] = {
            "user": [],
            "assistant": [],
            "system": [],
            "file": []
        }
        self.load_memory()
        self.role_message = """You are a coding agent focused on building llama server based python coding agent, your tasks are modifying, explaining code, and suggest commands, and everything related to it. right now you are agent0 and might be able to envolve to agent1

IMPORTANT INSTRUCTION FOR COMMAND EXECUTION:
When you have executable shell commands that the agent needs to run, you MUST wrap them inside the following XML guard rail markers:
<execute_commands>
```bash
... commands here ...
```
</execute_commands>

Do not put executable commands outside of these markers. Normal conversation, explanations, and code snippets that are not meant to be executed immediately should not be inside these markers.

IMPORTANT INSTRUCTION FOR COMMAND SUCCESS:
If a command executes successfully (Exit Code: 0) and there are no errors in Stderr, DO NOT re-execute the same command. Consider the command task complete and proceed with the next step or provide the final answer."""

    def load_memory(self) -> None:
        """Load memory from a JSON file if it exists."""
        try:
            with open(self.memory_file, 'r') as f:
                self.memory = json.load(f)
            print(f"{SYSTEM_COLOR}[S] Memory loaded from {self.memory_file}{RESET_COLOR}")
        except FileNotFoundError:
            print(f"{SYSTEM_COLOR}[S] No existing memory found. Starting with empty memory.{RESET_COLOR}")
            self.memory = {
                "user": [],
                "assistant": [],
                "system": [],
                "file": []
            }
        except json.JSONDecodeError:
            print(f"{SYSTEM_COLOR}[S] Error decoding memory file. Starting with empty memory.{RESET_COLOR}")
            self.memory = {
                "user": [],
                "assistant": [],
                "system": [],
                "file": []
            }

    def save_memory(self) -> None:
        """Save current memory to a JSON file."""
        try:
            with open(self.memory_file, 'w') as f:
                json.dump(self.memory, f)
            print(f"{SYSTEM_COLOR}[S] Memory saved to {self.memory_file}{RESET_COLOR}")
        except Exception as e:
            print(f"{SYSTEM_COLOR}[S] Error saving memory: {e}{RESET_COLOR}")

    def ensure_system_context(self) -> None:
        """Ensure the role definition is the first system message and source code is loaded as a title message."""
        # Ensure role message is first
        if not self.memory["system"] or not self.memory["system"][0].startswith("You are a coding agent"):
            self.memory["system"].insert(0, self.role_message)

        # Ensure source code is in memory as a title message
        source_code_title = "=== Title: Current Agent Source Code ===\n"
        current_code = self._get_current_code()
        source_code_message = f"{source_code_title}{current_code}"

        # Check if the source code is already in memory
        found_source = False
        for i, entry in enumerate(self.memory["system"]):
            if entry.startswith(source_code_title):
                stored_code = entry[len(source_code_title):]
                if stored_code == current_code:
                    found_source = True
                    break
                else:
                    self.memory["system"][i] = source_code_message
                    found_source = True
                    break

        if not found_source:
            # Add source code message after the role message (at index 1)
            if len(self.memory["system"]) > 1:
                self.memory["system"].insert(1, source_code_message)
            else:
                self.memory["system"].append(source_code_message)

    def _get_current_code(self) -> str:
        """Get the current source code of the script."""
        return open(__file__, 'r').read()

    def trim_memory(self, max_length: int = 32) -> None:
        """Trim memory to a maximum length, preserving the most recent messages."""
        # Ensure system context is up-to-date
        self.ensure_system_context()

        # Count current messages
        system_count = len(self.memory["system"])
        file_count = len(self.memory["file"])
        ua_count = len(self.memory["user"]) + len(self.memory["assistant"])

        total_count = system_count + file_count + ua_count

        if total_count <= max_length:
            return

        # Get all ua messages in order (interleaved as user, assistant, user, assistant...)
        ua_messages = []
        for i in range(max(len(self.memory["user"]), len(self.memory["assistant"]))):
            if i < len(self.memory["user"]):
                ua_messages.append(("user", self.memory["user"][i]))
            if i < len(self.memory["assistant"]):
                ua_messages.append(("assistant", self.memory["assistant"][i]))

        # Calculate how many UA messages we can keep
        max_ua_messages = max(0, max_length - system_count - file_count)

        # Trim UA messages from the end if needed
        if len(ua_messages) > max_ua_messages:
            if max_ua_messages > 0:
                ua_messages = ua_messages[-max_ua_messages:]
            else:
                ua_messages = []

        # Reconstruct user and assistant memory
        self.memory["user"] = []
        self.memory["assistant"] = []
        for msg_type, msg_content in ua_messages:
            if msg_type == "user":
                self.memory["user"].append(msg_content)
            else:
                self.memory["assistant"].append(msg_content)

class ChatAgent:
    def __init__(self, memory_manager: MemoryManager, api_url: str, headers: Dict[str, str]):
        self.memory_manager = memory_manager
        self.api_url = api_url
        self.headers = headers
        self.temperature = 0.3  # Default temperature
        # Ensure system context (role message + source code title message) is loaded
        self.memory_manager.ensure_system_context()

    def run(self) -> None:
        """Start the chat interface."""
        print(f"{SYSTEM_COLOR}[S] Chat agent is running. Type /help for commands.{RESET_COLOR}")

        while True:
            try:
                # Format temperature nicely for the prompt indicator
                temp_str = f"{self.temperature:g}"
                user_input = input(f"{USER_COLOR}[U|{temp_str}] {RESET_COLOR}")

                if user_input.startswith('/'):
                    self._handle_command(user_input)
                    continue

                self._process_agent_request(user_input)

            except KeyboardInterrupt:
                print(f"\n{SYSTEM_COLOR}[S] Chat terminated by user.{RESET_COLOR}")
                break
            except Exception as e:
                print(f"{SYSTEM_COLOR}[S] Error: {e}{RESET_COLOR}")
                break

    def _handle_command(self, command: str) -> None:
        """Handle commands starting with '/'."""
        if command == '/help':
            self._show_help()
        elif command.startswith('/save'):
            self.memory_manager.save_memory()
        elif command.startswith('/load'):
            self.memory_manager.load_memory()
        elif command.startswith('/read'):
            self._handle_read_command(command)
        elif command.startswith('/exec'):
            self._handle_exec_command(command)
        elif command.startswith('/temp'):
            self._handle_temp_command(command)
        else:
            print(f"{SYSTEM_COLOR}[S] Unknown command: {command}{RESET_COLOR}")

    def _show_help(self) -> None:
        """Display available commands."""
        print(f"{SYSTEM_COLOR}[S] Available commands:")
        print("  /help - Show this help message")
        print("  /save - Save memory to file")
        print("  /load - Load memory from file")
        print("  /read <filename> - Read and store file content in memory")
        print("  /exec <command> - Execute a shell command and store output in memory")
        print(f"  /temp <float> - Set temperature (e.g., /temp 0.7). Current: {self.temperature}")
        print("  Ctrl+C - Exit the chat{RESET_COLOR}")

    def _handle_read_command(self, command: str) -> None:
        """Handle the /read command to read a file."""
        parts = command.split(' ', 1)
        if len(parts) < 2:
            print(f"{SYSTEM_COLOR}[S] Please provide a filename: /read <filename>{RESET_COLOR}")
            return

        filename = parts[1]
        # Resolve to absolute path but ensure it's under the current directory
        file_path = os.path.abspath(os.path.join(os.getcwd(), filename))
        cwd_abs = os.path.abspath(os.getcwd())

        # Security check: ensure the file is under the current directory
        # We ensure file_path starts with cwd_abs + os.sep to prevent directory traversal
        if not file_path.startswith(cwd_abs + os.sep) and file_path != cwd_abs:
            print(f"{SYSTEM_COLOR}[S] Access denied: File must be under the current directory.{RESET_COLOR}")
            return

        if not os.path.isfile(file_path):
            if os.path.isdir(file_path):
                print(f"{SYSTEM_COLOR}[S] '{filename}' is a directory, not a file. Use /exec 'ls -la {filename}' to list directory contents.{RESET_COLOR}")
            else:
                print(f"{SYSTEM_COLOR}[S] File '{filename}' not found in the current directory.{RESET_COLOR}")
            return

        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                file_content = f.read()
            self.memory_manager.memory['file'].append(f"File content of '{filename}':\n{file_content}")
            print(f"{SYSTEM_COLOR}[S] File '{filename}' read and stored in memory.{RESET_COLOR}")
        except Exception as e:
            print(f"{SYSTEM_COLOR}[S] Error reading file: {e}{RESET_COLOR}")

    def _handle_exec_command(self, command: str) -> None:
        """Handle the /exec command to execute a shell command."""
        parts = command.split(' ', 1)
        if len(parts) < 2:
            print(f"{SYSTEM_COLOR}[S] Please provide a command: /exec <command>{RESET_COLOR}")
            return

        shell_command = parts[1]
        try:
            # Execute the shell command
            result = subprocess.run(
                shell_command,
                shell=True,
                capture_output=True,
                text=True,
                cwd=os.getcwd(),
                timeout=60  # Added timeout to prevent hanging on long-running commands
            )
            output = result.stdout
            error = result.stderr

            # Store in memory
            memory_entry = f"Command executed: {shell_command}\nExit Code: {result.returncode}\nStdout:\n{output}\nStderr:\n{error}"
            self.memory_manager.memory['file'].append(memory_entry)

            # Print output
            if output:
                print(f"{SYSTEM_COLOR}[S] Command output:\n{output}{RESET_COLOR}")
            if error:
                print(f"{SYSTEM_COLOR}[S] Command error:\n{error}{RESET_COLOR}")
            if not output and not error:
                print(f"{SYSTEM_COLOR}[S] Command executed successfully with no output.{RESET_COLOR}")

        except subprocess.TimeoutExpired as e:
            output = e.stdout if e.stdout else ""
            error = e.stderr if e.stderr else ""
            print(f"{SYSTEM_COLOR}[S] Command '{shell_command}' timed out after 60 seconds.{RESET_COLOR}")
            # Store in memory
            memory_entry = f"Command executed: {shell_command}\nExit Code: -1 (Timeout)\nStdout:\n{output}\nStderr:\n{error}"
            self.memory_manager.memory['file'].append(memory_entry)
        except Exception as e:
            print(f"{SYSTEM_COLOR}[S] Error executing command: {e}{RESET_COLOR}")
            # Store in memory
            memory_entry = f"Command executed: {shell_command}\nError: {e}"
            self.memory_manager.memory['file'].append(memory_entry)


    def _handle_temp_command(self, command: str) -> None:
        """Handle the /temp command to set temperature."""
        parts = command.split(' ', 1)
        if len(parts) < 2:
            print(f"{SYSTEM_COLOR}[S] Please provide a temperature: /temp <float>{RESET_COLOR}")
            return

        try:
            temp_value = float(parts[1])
            if 0.0 <= temp_value <= 2.0:
                self.temperature = temp_value
                print(f"{SYSTEM_COLOR}[S] Temperature set to {self.temperature}{RESET_COLOR}")
            else:
                print(f"{SYSTEM_COLOR}[S] Temperature must be between 0.0 and 2.0{RESET_COLOR}")
        except ValueError:
            print(f"{SYSTEM_COLOR}[S] Invalid temperature value. Please provide a float number.{RESET_COLOR}")

    def _is_valid_shell_command(self, cmd: str) -> bool:
        """Check if the command looks like a valid shell command and not a placeholder or natural language text."""
        cmd = cmd.strip()
        if not cmd:
            return False

        # Filter out placeholders like "... commands here ...", "...", etc.
        if cmd.startswith('...') or cmd.startswith('.. ') or cmd.startswith('. . .'):
            return False

        # Filter out common placeholder phrases
        placeholder_phrases = [
            'commands here',
            'maybe more commands',
            'replace with',
            'your command',
            'insert your',
            'put your',
            'example command',
            'sample command',
            'your script',
            'modify this',
            'do this',
            'run this',
            'insert code',
            'add code',
        ]
        cmd_lower = cmd.lower()
        for phrase in placeholder_phrases:
            if phrase in cmd_lower:
                return False

        # Get the first token (command name or path) by stripping leading shell operators
        import re
        cmd_stripped_ops = re.split(r'[|>&;<\s]+', cmd.strip())[0].strip()
        # Remove leading operators like >, <, |, &, &&, ||, ;, (, {, [
        cmd_stripped_ops = re.sub(r'^[|>&;<\s\(\{\[\];&]+', '', cmd_stripped_ops)

        first_token = cmd_stripped_ops.split()[0] if cmd_stripped_ops.split() else cmd_stripped_ops
        first_token_lower = first_token.lower()

        # Whitelist of common valid command starts or paths
        valid_starts = [
            'ls', 'cd', 'pwd', 'mkdir', 'rmdir', 'rm', 'cp', 'mv', 'touch', 'cat', 'echo', 'grep', 'find', 'sed', 'awk',
            'head', 'tail', 'wc', 'sort', 'uniq', 'tee', 'xargs', 'curl', 'wget', 'ssh', 'scp', 'rsync', 'python', 'python3',
            'pip', 'pip3', 'node', 'npm', 'npx', 'git', 'make', 'gcc', 'clang', 'sh', 'bash', 'zsh', 'docker', 'kubectl',
            'chmod', 'chown', 'ln', 'tar', 'zip', 'unzip', 'gzip', 'gunzip', 'jq', 'yq', 'env', 'export', 'source', 'eval',
            'exec', 'test', '[', '[[', 'if', 'for', 'while', 'do', 'done', 'case', 'esac', 'function', 'return', 'exit',
            'kill', 'ps', 'df', 'du', 'free', 'netstat', 'ss', 'ping', 'nslookup', 'dig', 'host', 'tr', 'cut', 'paste',
            'join', 'diff', 'patch', 'base64', 'openssl', 'ssh-keygen', 'pytest', 'flake8', 'black', 'isort', 'mypy',
            'eslint', 'tsc', 'go', 'cargo', 'rustc', 'java', 'javac', 'dotnet', 'php', 'ruby', 'bundle', 'lein', 'gradle',
            'mvn', 'yarn', 'pnpm', 'bun', 'sudo', 'nohup', 'timeout', 'strace', 'lsof', 'vim', 'nano', 'less', 'more',
            'man', 'which', 'whereis', 'locate', 'systemctl', 'service', 'apt', 'apt-get', 'yum', 'dnf', 'pacman', 'brew',
            'apk', 'python-', 'node-', 'bash-', 'sh-', 'docker-', 'kubectl-', 'git-', 'pip-', 'npm-', 'yarn-', 'pnpm-',
            './', '../', '/usr/', '/etc/', '/var/', '/opt/', '/home/', '~/ ', '~/', 'true', 'false', 'let', 'declare',
            'local', 'read', 'print', 'printf', 'venv', 'virtualenv', 'sudo ', 'nohup ', 'timeout ', 'strace '
        ]

        for valid_start in valid_starts:
            if first_token_lower.startswith(valid_start.lower()):
                return True

        # If it starts with a valid command character pattern (alphanumeric, ., /, ~, -) and is not a natural language word, accept it
        if re.match(r'^[a-zA-Z0-9_./~\-]+', first_token):
            # Ensure it's not just a random short English word
            if len(first_token) > 1 and first_token_lower not in ['a', 'an', 'the', 'is', 'in', 'it', 'to', 'of', 'and', 'or', 'but']:
                return True

        return False

    def _extract_commands(self, response: str) -> List[str]:
        """Extract command sequences from the LLM's response."""
        commands = []

        # Set of shell-related languages (only actual executable shell languages)
        # Removed: 'console', 'terminal', 'sh-session', 'bash-session', 'cat', 'shellsession'
        # These are often used for logs, output, or sessions, not for executable commands.
        shell_languages = {
            'bash', 'sh', 'shell', 'cmd', 'powershell', 'shell-script',
            'zsh'
        }

        # Define guard region markers to isolate command execution regions
        GUARD_START_MARKER = "<execute_commands>"
        GUARD_END_MARKER = "</execute_commands>"

        # Find the guard region in the response
        guard_start_idx = response.find(GUARD_START_MARKER)
        if guard_start_idx == -1:
            # No guard region found, do not extract any commands from normal conversation
            return commands

        guard_start_idx += len(GUARD_START_MARKER)
        guard_end_idx = response.find(GUARD_END_MARKER, guard_start_idx)
        if guard_end_idx == -1:
            # Guard start found but no guard end, do not extract commands
            return commands

        # Cut to the guard region to save wasted performance and avoid false positives in normal conversation
        process_region = response[guard_start_idx:guard_end_idx]

        # Now perform regex matching only on the cutted guard region

        code_block_pattern = r'```([a-zA-Z0-9_\-]*)\n?(.*?)\n?```'
        matches = re.findall(code_block_pattern, process_region, re.DOTALL | re.IGNORECASE)

        for lang, content in matches:
            lang_lower = lang.strip().lower() if lang else ''
            # Check if language is explicitly shell-related
            # We no longer accept empty/unspecified languages to prevent extracting
            # normal conversation text that is formatted in untagged code blocks.
            if lang_lower in shell_languages:
                cmd = content.strip()
                if cmd and cmd not in commands:
                    # Validate if it looks like a real shell command and not a placeholder or natural language text
                    if self._is_valid_shell_command(cmd):
                        commands.append(cmd)

        tag_patterns = [
            r'<execute>\s*(.*?)\s*</execute>',
            r'<execute_command>\s*(.*?)\s*</execute_command>'
        ]
        for tp in tag_patterns:
            tag_matches = re.findall(tp, process_region, re.DOTALL)
            for match in tag_matches:
                cmd = match.strip()
                if cmd and cmd not in commands:
                    # Validate if it looks like a real shell command
                    if self._is_valid_shell_command(cmd):
                        commands.append(cmd)

        return commands

    def _execute_commands(self, commands: List[str]) -> str:
        """Execute a list of commands and return the combined output."""
        execution_results = []
        for idx, cmd in enumerate(commands):
            try:
                # Execute the command
                result = subprocess.run(
                    cmd,
                    shell=True,
                    capture_output=True,
                    text=True,
                    cwd=os.getcwd(),
                    timeout=60  # Added timeout to prevent hanging on long-running or interactive commands
                )
                output = result.stdout
                error = result.stderr

                result_str = f"--- Command {idx+1} Execution ---\nCommand: {cmd}\nExit Code: {result.returncode}\nStdout:\n{output}\nStderr:\n{error}\n"
                execution_results.append(result_str)

                # Print output to user as well
                if output:
                    print(f"{SYSTEM_COLOR}[S] Command output:\n{output}{RESET_COLOR}")
                if error:
                    print(f"{SYSTEM_COLOR}[S] Command error:\n{error}{RESET_COLOR}")

            except subprocess.TimeoutExpired as e:
                output = e.stdout if e.stdout else ""
                error = e.stderr if e.stderr else ""
                error_str = f"--- Command {idx+1} Execution Timeout ---\nCommand: {cmd}\nError: Command timed out after 60 seconds.\nStdout:\n{output}\nStderr:\n{error}\n"
                execution_results.append(error_str)
                print(f"{SYSTEM_COLOR}[S] Command '{cmd}' timed out after 60 seconds.{RESET_COLOR}")
            except Exception as e:
                error_str = f"--- Command {idx+1} Execution Error ---\nCommand: {cmd}\nError: {e}\n"
                execution_results.append(error_str)
                print(f"{SYSTEM_COLOR}[S] Error executing command '{cmd}': {e}{RESET_COLOR}")

        return "\n".join(execution_results)

    def _process_agent_request(self, user_input: str) -> None:
        """Process user input as an agent request with auto-execution loop."""
        self.memory_manager.memory["user"].append(user_input)

        max_iterations = 10
        iteration = 0

        while iteration < max_iterations:
            iteration += 1
            self.memory_manager.trim_memory()
            messages = self._build_messages()

            try:
                response = requests.post(
                    self.api_url,
                    headers=self.headers,
                    json={"messages": messages, "temperature": self.temperature, "max_tokens": 65536, "stream": False}
                )
                response.raise_for_status()
                response_json = response.json()

                # Check for empty or unexpected response format
                if "choices" not in response_json or not response_json.get("choices"):
                    print(f"{SYSTEM_COLOR}[S] Debug - Empty or invalid choices in response. Full response JSON: {response_json}{RESET_COLOR}")
                    assistant_response = ""
                else:
                    assistant_response = response_json["choices"][0].get("message", {}).get("content", "")

                    if not assistant_response:
                        print(f"{SYSTEM_COLOR}[S] Debug - Empty response received. Full response JSON: {response_json}{RESET_COLOR}")
                        assistant_response = ""

                # Check if response contains commands to execute
                commands = self._extract_commands(assistant_response)

                if commands:
                    print(assistant_response)
                    # Execute commands
                    exec_output = self._execute_commands(commands)

                    # Add execution output to memory as a file/message to be sent to LLM
                    self.memory_manager.memory['file'].append(f"--- Execution Output for LLM (Iteration {iteration}) ---\n{exec_output}\n\n--- IMPORTANT INSTRUCTION ---\nIf the commands executed successfully (Exit Code: 0 for all commands) and there are no errors in Stderr, DO NOT re-execute the same commands. Consider the command task complete. Proceed with the next step or provide the final answer.")

                    # Continue loop to send to LLM again
                    print(f"{SYSTEM_COLOR}[S] Executed {len(commands)} command(s). Sending output to LLM...{RESET_COLOR}")
                    continue
                else:
                    # No commands to execute, this is the final response
                    self.memory_manager.memory["assistant"].append(assistant_response)
                    print(f"{ASSISTANT_COLOR}[A]{assistant_response}{RESET_COLOR}")
                    break

            except requests.exceptions.RequestException as e:
                print(f"{SYSTEM_COLOR}[S] API request failed: {e}{RESET_COLOR}")
                break
            except json.JSONDecodeError as e:
                response_text = response.text if 'response' in locals() else 'N/A'
                print(f"{SYSTEM_COLOR}[S] Failed to decode JSON response: {e}. Response text: {response_text}{RESET_COLOR}")
                break
            except Exception as e:
                print(f"{SYSTEM_COLOR}[S] An error occurred: {e}{RESET_COLOR}")
                break

    def _build_messages(self) -> List[Dict[str, str]]:
        """Construct the message list for the API request."""
        messages = []

        # Merge all system and file messages into a single system message to avoid consecutive system messages
        system_contents = []
        for msg in self.memory_manager.memory["system"]:
            system_contents.append(msg)
        for msg in self.memory_manager.memory["file"]:
            system_contents.append(msg)

        if system_contents:
            # Merge system contents into a single system message
            merged_system_content = "\n\n---\n\n".join(system_contents)
            messages.append({"role": "system", "content": merged_system_content})

        # Interleave user and assistant messages
        user_messages = self.memory_manager.memory["user"]
        assistant_messages = self.memory_manager.memory["assistant"]

        for i in range(max(len(user_messages), len(assistant_messages))):
            if i < len(user_messages):
                messages.append({"role": "user", "content": user_messages[i]})
            if i < len(assistant_messages):
                messages.append({"role": "assistant", "content": assistant_messages[i]})

        return messages

if __name__ == "__main__":
    # Configuration
    API_URL = os.getenv("LLM_API_URL", "http://localhost:8080/v1/chat/completions")
    HEADERS = {"Content-Type": "application/json"}

    memory_manager = MemoryManager()
    chat_agent = ChatAgent(memory_manager, API_URL, HEADERS)
    chat_agent.run()
