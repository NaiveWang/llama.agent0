import requests
import json
import os
import subprocess
from typing import Dict, List, Optional

# Color codes for terminal output
SYSTEM_COLOR = "\033[34m"  # Blue
USER_COLOR = "\033[33m"    # Orange
ASSISTANT_COLOR = "\033[32m"  # Green
RED_COLOR = "\033[31m"     # Red
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
        self.role_message = """You are agent0, a coding agent focused on building llama server based python coding agent, your tasks are modifying, explaining code, and suggest commands, and everything related to it.
IMPORTANT INSTRUCTION FOR COMMAND SUCCESS:
If the command exit code is 0 and there are no errors in Stderr, consider the command successful, proceed with the next step or provide the final answer.
If there are no commands to execute, the "commands" array MUST be empty.
You need to simply acknowledge the LAST command executed in a sequence, even if you did not expect it returns to you anything."""

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

    def init_context(self) -> None:
        self.memory["system"].insert(0, self.role_message)
        source_code_reflection_path = "=== agent0 source is in agent0.py, single file ===\n"
        self.memory["system"].append(source_code_reflection_path)

class ChatAgent:
    def __init__(self, memory_manager: MemoryManager, api_url: str, headers: Dict[str, str]):
        self.memory_manager = memory_manager
        self.api_url = api_url
        self.headers = headers
        self.temperature = 0.2  # Default temperature
        self.token_total_accumulator = 0  # Accumulator for total tokens
        # Ensure system context (role message + source code title message) is loaded
        self.memory_manager.init_context()
        self.pm = False

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
        elif command.startswith('/temp'):
            self._handle_temp_command(command)
        elif command.startswith('/pm'):
            print(self.memory_manager.memory)
        elif command.startswith('/pr'):
            self.pm = not self.pm
            print("Print Request =", self.pm)
        else:
            print(f"{SYSTEM_COLOR}[S] Unknown command: {command}{RESET_COLOR}")

    def _show_help(self) -> None:
        """Display available commands."""
        print(f"{SYSTEM_COLOR}[S] Available commands:")
        print("  /help - Show this help message")
        print("  /save - Save memory to file")
        print("  /load - Load memory from file")
        print(f"  /temp <float> - Set temperature (e.g., /temp 0.7). Current: {self.temperature}")
        print("  Ctrl+C - Exit the chat{RESET_COLOR}")

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

    def _parse_grammar_response(self, response_text: str) -> Dict[str, List[str]]:
        """Parse the LLM's JSON grammar response to extract message and commands."""
        # Parse the response as JSON (enforced by json_schema)
        data = json.loads(response_text)

        # Extract message and commands
        message = data.get("message", "")
        commands = data.get("commands", [])

        result = {
            "message": message,
            "commands": commands
        }
        return result

    def _execute_commands(self, commands: List[str]) -> str:
        """Execute a list of commands and return the combined output."""
        execution_results = []
        for idx, cmd in enumerate(commands):
            try:
                # Execute the command
                print(f"{SYSTEM_COLOR}[S] Command: {cmd}{RESET_COLOR}")
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

        max_iterations = 1000
        iteration = 0

        while iteration < max_iterations:
            iteration += 1
            messages = self._build_messages()

            try:
                response = requests.post(
                    self.api_url,
                    headers=self.headers,
                    json={
                        "messages": messages,
                        "temperature": self.temperature,
                        "max_tokens": 32768,
                        "stream": False,
                        "response_format": {
                            "type": "json_schema",
                            "json_schema": {
                                "name": "agent_response",
                                "strict": True,
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "message": {
                                            "type": "string"
                                        },
                                        "commands": {
                                            "type": "array",
                                            "items": {
                                                "type": "string"
                                            }
                                        }
                                    },
                                    "required": ["message", "commands"],
                                    "additionalProperties": False
                                }
                            }
                        }
                    }
                )
                response.raise_for_status()
                response_json = response.json()

                # Extract token usage if available
                token_num = 0
                if "usage" in response_json:
                    usage = response_json["usage"]
                    token_num_i = usage.get("prompt_tokens", 0)
                    token_num_o = usage.get("completion_tokens", 0)
                    current_total = usage.get("total_tokens", 0)
                    self.token_total_accumulator += current_total

                # Extract assistant response (guaranteed by json_schema)
                assistant_response = response_json.get("choices", [{}])[0].get("message", {}).get("content", "")

                # Parse the response using JSON grammar
                parsed_data = self._parse_grammar_response(assistant_response)
                message_text = parsed_data["message"]
                commands = parsed_data["commands"]

                # Print the message part to the user
                print(f"{RED_COLOR}[A|{token_num_i}|{token_num_o}|{self.token_total_accumulator}]\n{ASSISTANT_COLOR}{message_text}{RESET_COLOR}")

                if commands:
                    # Execute commands
                    exec_output = self._execute_commands(commands)

                    # Add execution output to memory as a file/message to be sent to LLM
                    self.memory_manager.memory['file'].append(f"--- Execution Output for LLM (Iteration {iteration}) ---\n{exec_output}")

                    # Continue loop to send to LLM again
                    print(f"{SYSTEM_COLOR}[S] Executed {len(commands)} command(s). Sending output to LLM...{RESET_COLOR}")
                    continue
                else:
                    # No commands to execute, this is the final response
                    self.memory_manager.memory["assistant"].append(assistant_response)
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
        for file_msg in self.memory_manager.memory["file"]:
            messages.append({"role": "user", "content": f"--- Execution Output for LLM ---\n{file_msg}"})
        self.memory_manager.memory["file"] = []
        if (self.pm): print(messages)
        return messages

if __name__ == "__main__":
    # Configuration
    API_URL = os.getenv("LLM_API_URL", "http://localhost:8080/v1/chat/completions")
    HEADERS = {"Content-Type": "application/json"}

    memory_manager = MemoryManager()
    chat_agent = ChatAgent(memory_manager, API_URL, HEADERS)
    chat_agent.run()
