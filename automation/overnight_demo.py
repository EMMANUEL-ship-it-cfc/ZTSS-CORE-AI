"""Run a bounded queue of prepared writing tasks with automatic review.

The task content is prepared locally. This module tests real Notepad interaction,
checkpoint saving, rule-based review, and unattended recovery; it does not include
or claim to be an autonomous research model.
"""

from __future__ import annotations

from datetime import datetime
import math
from pathlib import Path
import re
import subprocess
import sys
import time

from automation.notepad_paper_demo import (
    _chunks,
    _duration,
    _local_time,
    _section_name,
    _target_window,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TASK_DIRECTORY = PROJECT_ROOT / "automation" / "overnight_tasks"
OUTPUT_DIRECTORY = PROJECT_ROOT / "demo_output"

TASKS = (
    {
        "title": "Research paper: retrieval practice in secondary science",
        "source": PROJECT_ROOT / "automation" / "paper_manuscript.txt",
        "slug": "research_paper",
        "headings": (
            "Abstract",
            "Introduction",
            "Background of the Study",
            "Problem Statement",
            "Research Objectives",
            "Literature Review",
            "Research Methodology",
            "Findings and Discussion",
            "Conclusion",
            "Recommendations",
            "References",
        ),
        "requires_simulation_label": True,
    },
    {
        "title": "Teacher implementation guide",
        "source": TASK_DIRECTORY / "teacher_implementation_guide.txt",
        "slug": "teacher_guide",
        "headings": (
            "Purpose and boundaries",
            "Core implementation principles",
            "Before the unit begins",
            "The six-week sequence",
            "Lesson routines",
            "Feedback and correction",
            "Inclusion and student well-being",
            "Monitoring and adaptation",
            "End-of-unit reflection",
        ),
        "requires_simulation_label": False,
    },
    {
        "title": "School pilot evaluation protocol",
        "source": TASK_DIRECTORY / "pilot_evaluation_protocol.txt",
        "slug": "pilot_protocol",
        "headings": (
            "Protocol purpose",
            "Research questions",
            "Design and setting",
            "Participants and recruitment",
            "Intervention and comparison",
            "Measures and timing",
            "Analysis plan",
            "Ethics and data protection",
            "Reporting and decision rules",
        ),
        "requires_simulation_label": False,
    },
    {
        "title": "School leadership brief and classroom tools",
        "source": TASK_DIRECTORY / "school_leadership_brief_and_tools.txt",
        "slug": "leadership_tools",
        "headings": (
            "Decision brief",
            "What the evidence can support",
            "What a pilot needs",
            "Teacher planning checklist",
            "Student experience check-in",
            "Lesson record form",
            "Review meeting guide",
            "Decision options",
        ),
        "requires_simulation_label": False,
    },
    {
        "title": "Classroom scenarios and revision workbook",
        "source": TASK_DIRECTORY / "classroom_scenarios_and_revision_workbook.txt",
        "slug": "scenario_workbook",
        "headings": (
            "Workbook purpose",
            "Scenario card 1",
            "Scenario card 2",
            "Scenario card 3",
            "Scenario card 4",
            "Revision workshop",
            "Revision record",
            "Reflection record",
            "Facilitator closing note",
        ),
        "requires_simulation_label": False,
    },
)

SUSPECT_PATTERNS = (
    ("joined abstract heading", re.compile(r"\bsAbstract\b", re.IGNORECASE)),
    ("joined numbered heading", re.compile(r"\bs\d+(?:\.\d+)*\b", re.IGNORECASE)),
    ("malformed et al. citation", re.compile(r"\bt\s+al\.", re.IGNORECASE)),
    ("joined Agarwal citation", re.compile(r"\b\d+Agarwal\b", re.IGNORECASE)),
    ("missing first letter in Table", re.compile(r"\bable\s+\d+\b", re.IGNORECASE)),
    ("possible missing initial letter", re.compile(r"\bhe selected\b", re.IGNORECASE)),
)


class FocusLostError(RuntimeError):
    """Raised when the new Notepad task window cannot be restored safely."""


class ContentIntegrityError(RuntimeError):
    """Raised when Notepad's saved text differs from the intended task text."""


def _load_task(task: dict) -> str:
    path = Path(task["source"])
    if not path.is_file():
        raise FileNotFoundError(f"Task source not found: {path}")
    text = path.read_text(encoding="ascii").strip()
    if len(text.split()) < 500:
        raise ValueError(f"Task source is unexpectedly short: {path}")
    return text + "\n"


def run_overnight_demo(
    pyautogui,
    logger,
    *,
    max_runtime_hours: float = 4.0,
    checkpoint_minutes: int = 60,
    typing_interval: float = 0.15,
) -> int:
    """Type the local task queue and automatically review it until completion or deadline."""
    if not math.isfinite(max_runtime_hours) or max_runtime_hours <= 0:
        raise ValueError("max_runtime_hours must be greater than zero")
    if checkpoint_minutes <= 0:
        raise ValueError("checkpoint_minutes must be greater than zero")
    if not math.isfinite(typing_interval) or not 0 < typing_interval <= 1:
        raise ValueError("typing_interval must be greater than 0 and at most 1 second")

    loaded_tasks = [(task, _load_task(task)) for task in TASKS]
    run_id = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S_%f")
    run_directory = OUTPUT_DIRECTORY / f"overnight_{run_id}"
    activity_file = run_directory / f"activity_{run_id}.md"
    review_file = run_directory / f"automatic_reviews_{run_id}.md"

    print("ZTSS CORE bounded overnight writing and review demo")
    print("Mode: prepared local task queue, typed through real Notepad input")
    print("Review: local rule-based checks at checkpoints; no model or web research")
    print(f"Maximum wall-clock runtime: {max_runtime_hours:g} hours")
    print(f"Automatic review interval: {checkpoint_minutes} active minutes")
    print(f"Tasks queued: {len(loaded_tasks)}")
    for index, (task, text) in enumerate(loaded_tasks, start=1):
        print(f"  {index}. {task['title']} ({len(text.split()):,} words)")
    print(f"Run folder: {run_directory}")
    print("Keep the laptop awake and unlocked; the run may restore its own Notepad window.")
    print("A short case check will be typed and cleared in the first new Notepad file.")
    print("Move the pointer to the upper-left corner for the PyAutoGUI stop failsafe.")

    try:
        answer = input("Type YES to start the bounded queue, or STOP: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        answer = "stop"
    if answer != "yes":
        print("Run cancelled before desktop actions.")
        logger.info("Overnight task queue cancelled before desktop actions.")
        return 0

    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    run_directory.mkdir()
    metrics = {
        "keyboard_interactions": 0,
        "mouse_movements": 0,
        "mouse_clicks": 0,
        "scroll_actions": 0,
        "editing_actions": 0,
        "saves": 0,
        "recovery_events": 0,
        "typed_characters": 0,
        "typed_words": 0,
        "review_checkpoints": 0,
        "review_flags": 0,
        "integrity_checks": 0,
        "integrity_failures": 0,
        "whitespace_variances": 0,
        "input_calibration_retries": 0,
    }
    run_start = time.monotonic()
    deadline = run_start + max_runtime_hours * 60 * 60
    active_seconds = 0.0
    next_review_seconds = checkpoint_minutes * 60
    last_save_words = 0
    completed_words = 0
    current_task = "Queue startup"
    current_section = "Task setup"
    current_output = None
    current_text = ""
    committed_chars = 0
    current_window = None
    last_status_print = run_start
    stop_reason = "queue completed"
    completed_tasks: list[str] = []
    caps_lock_toggled_by_agent = False

    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.01

    def log_event(action: str, *, print_line: bool = False) -> None:
        wall_elapsed = time.monotonic() - run_start
        line = (
            f"| {_local_time()} | {_duration(active_seconds)} | "
            f"{_duration(wall_elapsed)} | {current_task} | {action} | "
            f"{metrics['typed_words']:,} | {metrics['keyboard_interactions']:,} | "
            f"{metrics['mouse_movements']} | {metrics['mouse_clicks']} | "
            f"{metrics['scroll_actions']} |\n"
        )
        with activity_file.open("a", encoding="utf-8", newline="\n") as log:
            log.write(line)
        logger.info(
            "%s; task=%s active=%s words=%s keys=%s mouse_moves=%s scrolls=%s",
            action,
            current_task,
            _duration(active_seconds),
            metrics["typed_words"],
            metrics["keyboard_interactions"],
            metrics["mouse_movements"],
            metrics["scroll_actions"],
        )
        if print_line:
            print(
                f"[{_duration(active_seconds)} active / "
                f"{_duration(wall_elapsed)} elapsed] {action} | "
                f"{metrics['typed_words']:,} words"
            )
            sys.stdout.flush()

    def foreground_matches() -> bool:
        active = pyautogui.getActiveWindow()
        return bool(active and current_output and current_output.stem.lower() in (active.title or "").lower())

    def ensure_focus() -> None:
        if foreground_matches():
            return
        for attempt in range(1, 4):
            try:
                current_window.activate()
                time.sleep(0.35)
            except Exception as error:
                logger.warning("Notepad focus recovery attempt %s failed: %s", attempt, error)
            if foreground_matches():
                metrics["recovery_events"] += 1
                pyautogui.hotkey("ctrl", "end")
                metrics["keyboard_interactions"] += 2
                log_event(f"Automatically restored the task window (attempt {attempt}).", print_line=True)
                return
        raise FocusLostError("The task's Notepad window could not be restored after three attempts.")

    def calibrate_notepad_input() -> None:
        nonlocal caps_lock_toggled_by_agent
        probe = "AaZzCaseCheck"

        def clear_probe() -> None:
            ensure_focus()
            pyautogui.hotkey("ctrl", "a")
            pyautogui.press("backspace")
            metrics["keyboard_interactions"] += 3
            metrics["editing_actions"] += 1
            pyautogui.hotkey("ctrl", "s")
            metrics["keyboard_interactions"] += 2
            metrics["saves"] += 1
            time.sleep(0.15)

        def type_and_read_probe() -> str:
            ensure_focus()
            pyautogui.hotkey("ctrl", "home")
            pyautogui.write(probe, interval=typing_interval)
            metrics["keyboard_interactions"] += len(probe) + 2
            metrics["editing_actions"] += 1
            pyautogui.hotkey("ctrl", "s")
            metrics["keyboard_interactions"] += 2
            metrics["saves"] += 1
            time.sleep(0.15)
            metrics["integrity_checks"] += 1
            return current_output.read_text(encoding="ascii")

        actual = ""
        passed = False
        for attempt in range(1, 4):
            actual = type_and_read_probe()
            if actual == probe:
                passed = True
                break
            metrics["input_calibration_retries"] += 1
            log_event(
                f"Input calibration attempt {attempt} mismatch: received {actual!r}; "
                f"expected {probe!r}.",
                print_line=True,
            )
            clear_probe()
            if actual.casefold() == probe.casefold() and not caps_lock_toggled_by_agent:
                ensure_focus()
                pyautogui.press("capslock")
                metrics["keyboard_interactions"] += 1
                caps_lock_toggled_by_agent = True
                log_event("Probe showed case inversion; toggled Caps Lock and retrying.", print_line=True)
            elif attempt < 3:
                time.sleep(0.2)

        if not passed:
            metrics["integrity_failures"] += 1
            clear_probe()
            raise ContentIntegrityError(
                "Notepad keyboard calibration failed after three attempts; the task text was not started."
            )

        clear_probe()
        if current_output.read_text(encoding="ascii") != "":
            metrics["integrity_failures"] += 1
            raise ContentIntegrityError("Could not clear the Notepad input calibration text.")
        log_event("Passed case-accurate Notepad input calibration; probe text was cleared.", print_line=True)

    def restore_caps_lock_if_toggled() -> None:
        nonlocal caps_lock_toggled_by_agent
        if caps_lock_toggled_by_agent:
            pyautogui.press("capslock")
            metrics["keyboard_interactions"] += 1
            caps_lock_toggled_by_agent = False
            log_event("Restored Caps Lock after the input calibration change.")

    def save_current(reason: str) -> None:
        ensure_focus()
        pyautogui.hotkey("ctrl", "s")
        metrics["keyboard_interactions"] += 2
        metrics["saves"] += 1
        time.sleep(0.15)
        log_event(f"Saved draft ({reason}).", print_line=True)
        expected = current_text[:committed_chars]
        actual = current_output.read_text(encoding="ascii")
        expected = expected.replace("\r\n", "\n").replace("\r", "\n")
        actual = actual.replace("\r\n", "\n").replace("\r", "\n")
        metrics["integrity_checks"] += 1
        if " ".join(actual.split()) == " ".join(expected.split()):
            if actual != expected:
                metrics["whitespace_variances"] += 1
                log_event("Saved text matches the intended content; only whitespace layout differs.")
            return
        if actual != expected:
            metrics["integrity_failures"] += 1
            log_event(
                f"Content integrity mismatch beyond whitespace: saved {len(actual.split()):,} words; "
                f"expected {len(expected.split()):,}.",
                print_line=True,
            )
            raise ContentIntegrityError(
                "Saved Notepad content differs from the intended source; the run stopped "
                "and will preserve a recovery copy."
            )

    def run_rule_review(*, final: bool) -> list[str]:
        ensure_focus()
        content = current_output.read_text(encoding="ascii") if current_output.is_file() else ""
        words = len(content.split())
        normalized = content.casefold()
        absent = [heading for heading in current_task_spec["headings"] if heading.casefold() not in normalized]
        flags = [
            f"{label}: {len(pattern.findall(content))} match(es)"
            for label, pattern in SUSPECT_PATTERNS
            if pattern.search(content)
        ]
        paragraphs = [" ".join(block.casefold().split()) for block in re.split(r"\n\s*\n", content)]
        paragraphs = [paragraph for paragraph in paragraphs if len(paragraph) >= 80]
        repeated_paragraphs = len(paragraphs) - len(set(paragraphs))
        if repeated_paragraphs:
            flags.append(f"{repeated_paragraphs} repeated long paragraph(s)")
        if current_task_spec.get("requires_simulation_label") and not any(
            phrase in normalized for phrase in ("simulated", "simulation")
        ):
            flags.append("simulation disclosure is missing")
        if "[insert" in normalized or "todo" in normalized:
            flags.append("placeholder or TODO text remains")

        if final and absent:
            flags.extend(f"required heading not found: {heading}" for heading in absent)
        elif not final and absent:
            flags.append(f"{len(absent)} expected section heading(s) are still pending")
        # Navigate through the open document while the local checks review its saved text.
        pyautogui.hotkey("ctrl", "home")
        metrics["keyboard_interactions"] += 2
        page_steps = min(8, max(2, words // 700))
        for _ in range(page_steps):
            pyautogui.press("pagedown")
            metrics["keyboard_interactions"] += 1
            time.sleep(0.35)
        pyautogui.hotkey("ctrl", "end")
        metrics["keyboard_interactions"] += 2
        metrics["review_checkpoints"] += 1
        metrics["review_flags"] += len(flags)
        review_kind = "final task review" if final else "automatic checkpoint review"
        review_text = (
            f"\n## {review_kind}: {current_task}\n\n"
            f"- Time: {_local_time()}\n"
            f"- Saved draft words: {words:,}\n"
            f"- Expected headings present: {len(current_task_spec['headings']) - len(absent)} "
            f"of {len(current_task_spec['headings'])}\n"
            f"- Review type: local rule-based structure and known-entry scan; no grammar, source, "
            f"or factual verification\n"
        )
        if flags:
            review_text += "- Findings:\n" + "".join(f"  - {flag}\n" for flag in flags)
        else:
            review_text += "- Findings: no configured structural or known-entry flags found\n"
        with review_file.open("a", encoding="utf-8", newline="\n") as report:
            report.write(review_text)
        log_event(f"Completed {review_kind}; {len(flags)} review note(s).", print_line=True)
        return flags

    def automatic_checkpoint() -> None:
        nonlocal next_review_seconds
        save_current("automatic review checkpoint")
        log_event("Starting automatic review; the run will continue without operator input.", print_line=True)
        run_rule_review(final=False)
        log_event("Automatic review finished; resumed the task queue.", print_line=True)
        while next_review_seconds <= active_seconds:
            next_review_seconds += checkpoint_minutes * 60

    def open_task(task: dict) -> None:
        nonlocal current_output, current_window, current_text, committed_chars
        nonlocal current_task_spec, current_task, current_section
        current_task_spec = task
        current_task = task["title"]
        current_text = task_text
        committed_chars = 0
        current_section = "Title page"
        current_output = run_directory / f"{task['slug']}_{run_id}.txt"
        with current_output.open("x", encoding="ascii", newline="\n"):
            pass
        subprocess.Popen(["notepad.exe", str(current_output)])
        time.sleep(1.25)
        current_window = _target_window(pyautogui, current_output.stem)
        current_window.activate()
        current_window.maximize()
        time.sleep(0.25)
        if not foreground_matches():
            raise FocusLostError(f"Could not confirm the new Notepad window for {task['title']}.")
        pyautogui.click(current_window.left + 150, current_window.top + 120)
        metrics["mouse_clicks"] += 1
        metrics["mouse_movements"] += 1
        pyautogui.hotkey("ctrl", "home")
        metrics["keyboard_interactions"] += 2
        log_event("Opened a new isolated Notepad task file.", print_line=True)

    with activity_file.open("x", encoding="utf-8", newline="\n") as log:
        log.write("# ZTSS CORE bounded overnight writing and review run\n\n")
        log.write(f"Start time: {_local_time()}\n")
        log.write(f"Wall-clock limit: {max_runtime_hours:g} hours\n")
        log.write(f"Automatic review interval: {checkpoint_minutes} active minutes\n")
        log.write(f"Typing interval: {typing_interval:g} seconds per character\n")
        log.write("Review mode: rule-based local checks; automatically continues\n")
        log.write("Task text: prepared local sources; no model, web research, or private files\n")
        log.write("Generated files are restricted to this run's new output directory\n\n")
        log.write("| Local time | Active typing | Wall time | Task | Action | Words | Keyboard events | Mouse moves | Clicks | Scrolls |\n")
        log.write("|---|---:|---:|---|---|---:|---:|---:|---:|---:|\n")
    review_file.write_text(
        "# Automatic review notes\n\n"
        "Checks cover configured headings, selected known typing artifacts, duplicate long paragraphs, "
        "and required simulation disclosure. They do not verify sources, claims, or grammar.\n",
        encoding="utf-8",
    )

    current_task_spec = TASKS[0]
    task_text = ""
    try:
        for task_number, (task, task_text) in enumerate(loaded_tasks, start=1):
            if time.monotonic() >= deadline:
                stop_reason = "wall-clock limit reached before the next task"
                break
            open_task(task)
            if task_number == 1:
                calibrate_notepad_input()
            print(f"Task {task_number}/{len(loaded_tasks)}: {task['title']}")
            sys.stdout.flush()
            log_event(f"Started task {task_number} of {len(loaded_tasks)}.", print_line=True)

            task_completed = True
            for line in current_text.splitlines(keepends=True):
                if time.monotonic() >= deadline:
                    task_completed = False
                    stop_reason = "four-hour wall-clock limit reached"
                    break
                line_body = line[:-1] if line.endswith("\n") else line
                new_section = _section_name(line_body, current_section)
                if new_section != current_section and metrics["typed_characters"] > 0:
                    current_section = new_section
                    log_event("Moved to the next document section.")

                for chunk in _chunks(line_body):
                    if time.monotonic() >= deadline:
                        task_completed = False
                        stop_reason = "four-hour wall-clock limit reached"
                        break
                    ensure_focus()
                    started = time.monotonic()
                    pyautogui.write(chunk, interval=typing_interval)
                    active_seconds += time.monotonic() - started
                    committed_chars += len(chunk)
                    metrics["typed_characters"] += len(chunk)
                    metrics["keyboard_interactions"] += len(chunk)
                    metrics["editing_actions"] += 1
                    metrics["typed_words"] = completed_words + len(current_text[:committed_chars].split())
                    log_event(f"Typed text chunk ({len(chunk)} characters).")

                    if metrics["typed_words"] - last_save_words >= 250:
                        save_current("250-word interval")
                        last_save_words = metrics["typed_words"]

                    if active_seconds >= next_review_seconds:
                        automatic_checkpoint()

                    now = time.monotonic()
                    if now - last_status_print >= 60:
                        elapsed = now - run_start
                        remaining = max(0, deadline - now)
                        print(
                            f"Status: {_duration(elapsed)} elapsed; "
                            f"{_duration(remaining)} remaining; {_duration(active_seconds)} active; "
                            f"{metrics['typed_words']:,} words; task: {current_task}"
                        )
                        sys.stdout.flush()
                        last_status_print = now

                if not task_completed:
                    break
                if line.endswith("\n"):
                    if time.monotonic() >= deadline:
                        task_completed = False
                        stop_reason = "four-hour wall-clock limit reached"
                        break
                    ensure_focus()
                    started = time.monotonic()
                    pyautogui.press("enter")
                    time.sleep(0.08)
                    active_seconds += time.monotonic() - started
                    committed_chars += 1
                    metrics["typed_characters"] += 1
                    metrics["keyboard_interactions"] += 1
                    metrics["editing_actions"] += 1
                    metrics["typed_words"] = completed_words + len(current_text[:committed_chars].split())
                    log_event("Inserted a paragraph break.")

            save_current("task completion" if task_completed else "runtime limit")
            try:
                final_file_words = len(current_output.read_text(encoding="ascii").split())
            except OSError:
                final_file_words = 0
            metrics["final_file_words"] = metrics.get("final_file_words", 0) + final_file_words
            run_rule_review(final=task_completed)
            if task_completed:
                completed_words += len(current_text.split())
                metrics["typed_words"] = completed_words
                completed_tasks.append(task["title"])
                log_event("Completed task and saved its final draft.", print_line=True)
            else:
                log_event("Saved the current partial task at the runtime limit.", print_line=True)
                break

        if stop_reason == "queue completed":
            log_event("Completed the full writing and review task queue.", print_line=True)
        restore_caps_lock_if_toggled()
        with activity_file.open("a", encoding="utf-8", newline="\n") as log:
            log.write("\n## Final summary\n\n")
            log.write(f"- Result: {stop_reason}\n")
            log.write(f"- Completed tasks: {len(completed_tasks)} of {len(loaded_tasks)}\n")
            for title in completed_tasks:
                log.write(f"  - {title}\n")
            log.write(f"- Active typing time: {_duration(active_seconds)}\n")
            log.write(f"- Wall time: {_duration(time.monotonic() - run_start)}\n")
            for key, value in metrics.items():
                log.write(f"- {key.replace('_', ' ').title()}: {value:,}\n")
        print(f"Run folder: {run_directory}")
        print(f"Activity log: {activity_file}")
        print(f"Automatic review notes: {review_file}")
        print(f"Result: {stop_reason}; {metrics['typed_words']:,} words typed.")
        return 0

    except pyautogui.FailSafeException:
        stop_reason = "stopped by mouse-corner failsafe"
        print("PyAutoGUI stop failsafe activated; saving the current task's committed text.")
    except KeyboardInterrupt:
        stop_reason = "stopped by keyboard interrupt"
        print("Run interrupted; saving the current task's committed text.")
    except Exception as error:
        stop_reason = f"error: {type(error).__name__}"
        print(f"The overnight run stopped: {error}")
        logger.exception("Bounded overnight task queue failed.")

    try:
        restore_caps_lock_if_toggled()
    except Exception:
        logger.exception("Could not restore Caps Lock after input calibration.")
    if current_output and current_text:
        recovery = current_output.with_name(f"{current_output.stem}_recovery.txt")
        recovery.write_text(current_text[:committed_chars], encoding="ascii", newline="\n")
        metrics["recovery_events"] += 1
        log_event(f"Wrote recovery copy after {stop_reason}.", print_line=True)
    with activity_file.open("a", encoding="utf-8", newline="\n") as log:
        log.write(f"\n## Final summary\n\n- Result: {stop_reason}\n")
        log.write(f"- Active typing time: {_duration(active_seconds)}\n")
        log.write(f"- Wall time: {_duration(time.monotonic() - run_start)}\n")
        for key, value in metrics.items():
            log.write(f"- {key.replace('_', ' ').title()}: {value:,}\n")
    print(f"Activity log: {activity_file}")
    print(f"Automatic review notes: {review_file}")
    return 0 if "stopped by" in stop_reason else 1
