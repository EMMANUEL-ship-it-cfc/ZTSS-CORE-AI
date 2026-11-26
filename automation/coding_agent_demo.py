"""A time-boxed coding agent: write, run, and fix a small Python program.

The loop is the core pattern behind every agent:

    decide (model writes code) -> act (save files, run tests) -> observe
    (test output) -> decide again

Only the model call is "AI"; everything else is ordinary, inspectable code.
Generated code is run locally in a subprocess with a timeout. That is NOT a
security sandbox, so the default is to ask for approval before every run.
"""

from __future__ import annotations

import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

from config.settings import CODING_AGENT_MODEL


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIRECTORY = PROJECT_ROOT / "demo_output"

MAX_HOURS_CEILING = 3.0
MAX_STEPS_CEILING = 30
MAX_FILES_PER_REPLY = 5
MAX_FILE_BYTES = 40_000
MAX_FEEDBACK_CHARS = 6_000
TEST_TIMEOUT_SECONDS = 60
MAX_GOAL_CHARS = 500
FILENAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,40}\.py$")
STDLIB_NAMES = getattr(sys, "stdlib_module_names", frozenset())

SYSTEM_PROMPT = """You are the coding step of a supervised agent. Reply with ONE JSON \
object and nothing else (no markdown fences, no commentary outside the JSON):

{"notes": "one or two sentences on what you did or changed",
 "files": {"solution.py": "<full file contents>", "test_solution.py": "<full file contents>"}}

Rules:
- Python 3, standard library only. No network access, no subprocesses, no deleting \
files, and no reading or writing outside the current directory.
- First reply: write solution.py and test_solution.py. Use unittest. The tests must \
check real behaviour, including edge cases and error handling.
- Later replies: you receive the test output. Find the cause and fix it. Return only \
the files you change, each in full.
- {test_rule}
- Never weaken, skip, or special-case a test to make it pass.
- Keep programs small: under about 200 lines per file, at most 5 files.
"""

LOCKED_TEST_RULE = (
    "Test files (test_*.py) are locked after your first reply. If a test looks "
    "wrong, say so in notes and fix the solution as best you can."
)
OPEN_TEST_RULE = (
    "You may fix a test only if it is clearly wrong, and you must say why in notes."
)


def _duration(seconds: float) -> str:
    return str(timedelta(seconds=max(0, int(seconds))))


def _truncate(text: str, limit: int = MAX_FEEDBACK_CHARS) -> str:
    if len(text) <= limit:
        return text
    head = 1_000
    return text[:head] + "\n...[output truncated]...\n" + text[-(limit - head):]


def _extract_json(reply: str) -> dict:
    """Pull one JSON object out of a model reply, tolerating stray fences."""
    text = reply.strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("the reply contained no JSON object")
    try:
        data = json.loads(text[start : end + 1])
    except json.JSONDecodeError as error:
        raise ValueError(f"the JSON could not be parsed ({error.msg})") from error
    if not isinstance(data, dict):
        raise ValueError("the JSON must be an object")
    return data


def _validate_files(
    data: dict, *, first_step: bool, allow_test_edits: bool
) -> tuple[dict[str, str], list[str]]:
    """Return (files safe to write, human-readable rejections).

    Only flat, simple ``name.py`` files are accepted, so the model can never
    write outside the workspace or shadow a standard-library module.
    """
    files = data.get("files")
    if not isinstance(files, dict) or not files:
        raise ValueError('"files" must be a non-empty object of filename: contents')
    if len(files) > MAX_FILES_PER_REPLY:
        raise ValueError(f"too many files (limit {MAX_FILES_PER_REPLY})")

    accepted: dict[str, str] = {}
    rejected: list[str] = []
    for name, content in files.items():
        if not isinstance(name, str) or not FILENAME_PATTERN.match(name):
            rejected.append(f"{name!r}: not a simple .py filename")
        elif name[:-3] in STDLIB_NAMES:
            rejected.append(f"{name}: would shadow a standard-library module")
        elif not isinstance(content, str):
            rejected.append(f"{name}: contents must be a string")
        elif len(content.encode("utf-8")) > MAX_FILE_BYTES:
            rejected.append(f"{name}: larger than {MAX_FILE_BYTES:,} bytes")
        elif name.startswith("test_") and not first_step and not allow_test_edits:
            rejected.append(f"{name}: test files are locked after the first step")
        else:
            accepted[name] = content
    return accepted, rejected


def _clean_environment() -> dict[str, str]:
    """Child-process environment without anything that looks like a secret."""
    markers = ("KEY", "TOKEN", "SECRET", "PASSWORD", "CREDENTIAL")
    env = {
        name: value
        for name, value in os.environ.items()
        if not any(marker in name.upper() for marker in markers)
    }
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def _run_tests(workspace: Path, timeout: float) -> tuple[bool, int | None, str]:
    command = [sys.executable, "-m", "unittest", "discover", "-s", ".", "-p", "test_*.py", "-v"]
    try:
        result = subprocess.run(
            command,
            cwd=workspace,
            env=_clean_environment(),
            capture_output=True,
            text=True,
            errors="replace",
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as error:
        partial = (error.stderr or "") if isinstance(error.stderr, str) else ""
        return False, None, f"Tests timed out after {int(timeout)} seconds.\n{partial}"
    output = (result.stderr or "") + (result.stdout or "")
    passed = result.returncode == 0 and "Ran 0 tests" not in output
    return passed, result.returncode, output


class ModelClient:
    """Thin wrapper so the loop does not depend on one SDK's details."""

    def __init__(self, model: str):
        try:
            import anthropic
        except ImportError as error:
            raise RuntimeError(
                "The 'anthropic' package is not installed. Run: "
                "python -m pip install -r requirements.txt"
            ) from error
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise RuntimeError(
                "Set the ANTHROPIC_API_KEY environment variable first. "
                "Keep the key out of the repository."
            )
        self.model = model
        self._client = anthropic.Anthropic(timeout=120.0)

    def complete(self, system: str, messages: list[dict]) -> str:
        response = self._client.messages.create(
            model=self.model,
            max_tokens=8000,
            system=system,
            messages=messages,
        )
        return "".join(
            block.text for block in response.content if getattr(block, "type", "") == "text"
        )


def _open_in_vscode(logger, workspace: Path, first_file: Path) -> None:
    code = shutil.which("code")
    if not code:
        print("VS Code's 'code' command was not found. Open this folder yourself:")
        print(f"  {workspace}")
        logger.info("VS Code command not found; user told to open the workspace manually.")
        return
    try:
        subprocess.Popen([code, "--reuse-window", str(workspace), str(first_file)])
        logger.info("Opened %s in VS Code.", workspace)
    except OSError as error:
        print(f"Could not start VS Code ({error}). Open this folder yourself: {workspace}")
        logger.warning("Could not start VS Code: %s", error)


def run_coding_agent_demo(
    logger,
    *,
    goal: str | None = None,
    max_hours: float = MAX_HOURS_CEILING,
    max_steps: int = 10,
    model: str | None = None,
    auto_run: bool = False,
    open_editor: bool = True,
    allow_test_edits: bool = False,
    model_client=None,
) -> int:
    """Let a model write and repair a small program, stopping at any limit."""
    if not math.isfinite(max_hours) or not 0 < max_hours <= MAX_HOURS_CEILING:
        raise ValueError(f"max_hours must be above 0 and at most {MAX_HOURS_CEILING:g}")
    if not 1 <= max_steps <= MAX_STEPS_CEILING:
        raise ValueError(f"max_steps must be between 1 and {MAX_STEPS_CEILING}")
    model = model or os.environ.get("ZTSS_MODEL") or CODING_AGENT_MODEL

    print("ZTSS CORE time-boxed coding agent")
    print("Loop: model writes code -> files are saved -> tests run -> results go back to the model")
    print(f"Limits: {max_hours:g} hours and {max_steps} steps, whichever comes first")
    print("The generated code runs on this computer in a subprocess with a timeout.")
    print("That is not a security sandbox, so keep goals to plain, harmless programs.")
    if not auto_run:
        print("You will review the code in VS Code and approve every test run.")
    print("Press Ctrl+C at any time to stop.")

    if goal is None:
        try:
            goal = input("Goal (for example: a command-line to-do list with tests): ").strip()
        except (EOFError, KeyboardInterrupt):
            print("Cancelled.")
            return 0
    goal = (goal or "").strip()
    if not goal:
        print("No goal given. Nothing to do.")
        return 0
    if len(goal) > MAX_GOAL_CHARS:
        print(f"Goal is too long (limit {MAX_GOAL_CHARS} characters).")
        return 1

    try:
        client = model_client or ModelClient(model)
    except RuntimeError as error:
        print(error)
        return 1

    try:
        answer = input(f"Goal: {goal}\nModel: {model}\nType YES to start: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        answer = "no"
    if answer != "yes":
        print("Cancelled before any model call.")
        logger.info("Coding agent cancelled before starting.")
        return 0

    run_id = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S_%f")
    run_directory = OUTPUT_DIRECTORY / f"coding_agent_{run_id}"
    workspace = run_directory / "workspace"
    workspace.mkdir(parents=True)
    trace_file = run_directory / "agent_log.jsonl"
    summary_file = run_directory / "summary.md"
    print(f"Run folder: {run_directory}")

    run_start = time.monotonic()
    deadline = run_start + max_hours * 3600
    system = SYSTEM_PROMPT.replace(
        "{test_rule}", OPEN_TEST_RULE if allow_test_edits else LOCKED_TEST_RULE
    )
    messages = [
        {
            "role": "user",
            "content": f"Goal: {goal}\n\nWrite solution.py and test_solution.py now.",
        }
    ]
    stop_reason = "step limit reached"
    steps_run = 0
    editor_opened = False
    passed = False
    user_stopped = False

    def trace(step: int, event: str, **details) -> None:
        record = {
            "time": datetime.now().astimezone().isoformat(timespec="seconds"),
            "elapsed": _duration(time.monotonic() - run_start),
            "step": step,
            "event": event,
            **details,
        }
        with trace_file.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        logger.info("coding agent step=%s event=%s", step, event)

    trace(0, "start", goal=goal, model=model, max_hours=max_hours, max_steps=max_steps)

    try:
        for step in range(1, max_steps + 1):
            if time.monotonic() >= deadline:
                stop_reason = "time limit reached"
                break
            steps_run = step
            print(f"\n--- Step {step}/{max_steps} | {_duration(time.monotonic() - run_start)} elapsed ---")

            print("Asking the model...")
            try:
                reply = client.complete(system, messages)
            except Exception as error:  # SDK errors vary; log and stop cleanly
                stop_reason = f"model call failed: {type(error).__name__}"
                print(f"The model call failed: {error}")
                logger.exception("Model call failed.")
                trace(step, "model_error", error=f"{type(error).__name__}: {error}")
                break
            messages.append({"role": "assistant", "content": reply})

            try:
                data = _extract_json(reply)
                accepted, rejected = _validate_files(
                    data, first_step=(step == 1), allow_test_edits=allow_test_edits
                )
                if not accepted:
                    raise ValueError("every file in the reply was rejected: " + "; ".join(rejected))
            except ValueError as error:
                print(f"Unusable reply: {error}")
                trace(step, "invalid_reply", problem=str(error))
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            f"Your last reply could not be used: {error}. Reply again with "
                            "one JSON object in the required format."
                        ),
                    }
                )
                continue

            for name, content in accepted.items():
                (workspace / name).write_text(content, encoding="utf-8", newline="\n")
            notes = str(data.get("notes", ""))[:500]
            print(f"Model notes: {notes}")
            print(f"Wrote: {', '.join(sorted(accepted))}")
            for item in rejected:
                print(f"Rejected: {item}")
            trace(step, "files_written", files=sorted(accepted), rejected=rejected, notes=notes)

            if open_editor and not editor_opened:
                first = "solution.py" if "solution.py" in accepted else sorted(accepted)[0]
                _open_in_vscode(logger, workspace, workspace / first)
                editor_opened = True

            if not auto_run:
                try:
                    choice = input("Review the code, then type RUN to run the tests or STOP: ").strip().lower()
                except (EOFError, KeyboardInterrupt):
                    choice = "stop"
                if choice not in {"run", "r"}:
                    stop_reason = "stopped by the user before running the code"
                    user_stopped = True
                    trace(step, "user_stopped")
                    break

            remaining = deadline - time.monotonic()
            if remaining <= 0:
                stop_reason = "time limit reached"
                break
            print("Running the tests...")
            ok, exit_code, output = _run_tests(workspace, min(TEST_TIMEOUT_SECONDS, remaining))
            trace(step, "tests_run", passed=ok, exit_code=exit_code, output_tail=_truncate(output, 2000))
            tail = output.strip().splitlines()[-1] if output.strip() else "(no output)"
            print("Tests passed." if ok else f"Tests failed: {tail}")

            if ok:
                passed = True
                stop_reason = "all tests passed"
                break

            messages.append(
                {
                    "role": "user",
                    "content": (
                        f"The tests failed (exit code {exit_code}). Output:\n\n"
                        f"{_truncate(output)}\n\nFind the cause and return the corrected files."
                    ),
                }
            )
    except KeyboardInterrupt:
        stop_reason = "interrupted with Ctrl+C"
        user_stopped = True
        print("\nInterrupted.")
        trace(steps_run, "interrupted")

    elapsed = _duration(time.monotonic() - run_start)
    trace(steps_run, "finish", result=stop_reason, passed=passed)
    summary_file.write_text(
        "# Coding agent run\n\n"
        f"- Goal: {goal}\n"
        f"- Model: {model}\n"
        f"- Result: {stop_reason}\n"
        f"- Tests passing: {'yes' if passed else 'no'}\n"
        f"- Steps used: {steps_run} of {max_steps}\n"
        f"- Elapsed: {elapsed} of a {max_hours:g}-hour limit\n"
        f"- Code: {workspace}\n"
        "- Full step-by-step record: agent_log.jsonl\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"\nResult: {stop_reason}. Steps: {steps_run}. Elapsed: {elapsed}.")
    print(f"Code: {workspace}")
    print(f"Summary: {summary_file}")
    return 0 if (passed or user_stopped) else 1
