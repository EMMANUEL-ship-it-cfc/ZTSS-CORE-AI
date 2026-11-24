"""Type a prepared, clearly simulated research paper into a new Notepad file.

This is a deterministic desktop-automation demonstration. It does not contain
an AI model or make claims that the manuscript was generated autonomously.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
import re
import subprocess
import sys
import time


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MANUSCRIPT_PATH = PROJECT_ROOT / "automation" / "paper_manuscript.txt"
OUTPUT_DIRECTORY = PROJECT_ROOT / "demo_output"
PAPER_STEM = "ZTSS_CORE_Retrieval_Practice_Paper"


class FocusLostError(RuntimeError):
    """Raised when the target Notepad document is not the foreground window."""


def _duration(seconds: float) -> str:
    return str(timedelta(seconds=max(0, int(seconds))))


def _local_time() -> str:
    return datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")


def _section_name(line: str, fallback: str) -> str:
    stripped = line.strip()
    if not stripped:
        return fallback
    known_headings = {
        "abstract": "Abstract",
        "introduction": "Introduction",
        "background of the study": "Background of the Study",
        "problem statement": "Problem Statement",
        "research objectives": "Research Objectives",
        "literature review": "Literature Review",
        "research methodology": "Research Methodology",
        "conclusion": "Conclusion",
        "recommendations": "Recommendations",
        "references": "References",
    }
    heading = known_headings.get(stripped.casefold())
    if heading:
        return heading

    appendix = re.match(r"^Appendix [A-Z]\.", stripped)
    if appendix:
        return stripped[:100]

    numbered = re.match(r"^\d+(?:\.\d+)*\.?\s+(.+)$", stripped)
    if numbered and len(stripped) <= 120 and not re.search(r"[.!?]", numbered.group(1)):
        return stripped[:100]
    return fallback


def _chunks(text: str, max_chars: int = 76):
    """Yield human-sized text chunks, preferring spaces as split points."""
    while text:
        if len(text) <= max_chars:
            yield text
            return
        split_at = text.rfind(" ", 0, max_chars + 1)
        if split_at < max_chars // 2:
            split_at = max_chars
        else:
            split_at += 1
        yield text[:split_at]
        text = text[split_at:]


def _load_manuscript(target_words: int) -> tuple[str, int]:
    if not MANUSCRIPT_PATH.is_file():
        raise FileNotFoundError(f"Prepared manuscript not found: {MANUSCRIPT_PATH}")
    text = MANUSCRIPT_PATH.read_text(encoding="ascii")
    word_count = len(text.split())
    if word_count < target_words:
        raise ValueError(
            f"The prepared manuscript has {word_count} words, below the "
            f"requested minimum of {target_words}."
        )
    return text, word_count


def _target_window(pyautogui, stem: str, timeout: float = 20.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        matches = [
            window
            for window in pyautogui.getWindowsWithTitle(stem)
            if stem.lower() in (window.title or "").lower()
        ]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            raise RuntimeError(
                "More than one Notepad window matches the new paper filename. "
                "Close or rename the extra paper window and try again."
            )
        time.sleep(0.25)
    raise RuntimeError("Notepad did not open the new paper window in time.")


def run_notepad_paper_demo(
    pyautogui,
    logger,
    *,
    target_words: int = 5000,
    checkpoint_minutes: int = 60,
    typing_interval: float = 0.11,
) -> int:
    """Type the manuscript into Notepad with saves and hourly review gates."""
    text, manuscript_words = _load_manuscript(target_words)
    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)

    run_id = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")
    output_file = OUTPUT_DIRECTORY / f"{PAPER_STEM}_{run_id}.txt"
    activity_file = OUTPUT_DIRECTORY / f"notepad_paper_activity_{run_id}.md"

    print("ZTSS CORE Notepad paper demonstration")
    print("Mode: prepared manuscript typed through real Notepad keyboard input")
    print("AI status: no local AI model is included in this prototype")
    print(f"Manuscript: {manuscript_words:,} words; minimum requested: {target_words:,}")
    print(f"Review gate: every {checkpoint_minutes} minutes of active typing")
    print(f"Output: {output_file}")
    print(f"Activity log: {activity_file}")
    print("Notepad is plain text; its printed page count depends on print settings.")
    print("Move the pointer to the upper-left corner for the PyAutoGUI stop failsafe.")
    print("At an hourly checkpoint, type R to resume after review or STOP to end.")

    try:
        answer = input("Start this Notepad run? Type YES to continue: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("Run cancelled before opening the paper.")
        logger.info("Notepad paper demo cancelled before desktop actions.")
        return 0
    if answer != "yes":
        print("Run cancelled before opening the paper.")
        logger.info("Notepad paper demo cancelled before desktop actions.")
        return 0

    # Create a unique empty file first, so Notepad opens the intended document
    # without a Save As dialog and without touching other open Notepad tabs.
    with output_file.open("x", encoding="ascii", newline="\n"):
        pass

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
    }
    run_start = time.monotonic()
    active_seconds = 0.0
    active_checkpoint_seconds = checkpoint_minutes * 60
    last_save_words = 0
    committed_chars = 0
    current_section = "Title page"
    last_status_print = 0.0
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.01

    def log_event(action: str, *, print_line: bool = False) -> None:
        wall_elapsed = time.monotonic() - run_start
        line = (
            f"| {_local_time()} | {_duration(active_seconds)} | "
            f"{_duration(wall_elapsed)} | {action} | {current_section} | "
            f"{metrics['typed_words']:,} | {metrics['keyboard_interactions']:,} | "
            f"{metrics['mouse_movements']} | {metrics['mouse_clicks']} | "
            f"{metrics['scroll_actions']} |\n"
        )
        with activity_file.open("a", encoding="utf-8", newline="\n") as log:
            log.write(line)
        logger.info(
            "%s; active=%s words=%s keys=%s mouse_moves=%s scrolls=%s",
            action,
            _duration(active_seconds),
            metrics["typed_words"],
            metrics["keyboard_interactions"],
            metrics["mouse_movements"],
            metrics["scroll_actions"],
        )
        if print_line:
            print(
                f"[{_duration(active_seconds)} active] {action} | "
                f"{metrics['typed_words']:,}/{target_words:,} words"
            )
            sys.stdout.flush()

    def foreground_matches() -> bool:
        active = pyautogui.getActiveWindow()
        return bool(active and output_file.stem.lower() in (active.title or "").lower())

    def activate_target(window) -> None:
        window.activate()
        time.sleep(0.25)
        if not foreground_matches():
            raise FocusLostError("The new Notepad paper is not the active window.")

    def ensure_focus(window) -> None:
        if foreground_matches():
            return
        metrics["recovery_events"] += 1
        log_event("Focus changed; paused for the operator to restore Notepad.", print_line=True)
        while True:
            try:
                answer = input(
                    "Bring the paper Notepad window forward, then type R to resume or STOP: "
                ).strip().lower()
            except (EOFError, KeyboardInterrupt):
                raise KeyboardInterrupt
            if answer in {"stop", "s"}:
                raise KeyboardInterrupt
            if answer in {"r", "resume"}:
                activate_target(window)
                pyautogui.hotkey("ctrl", "end")
                metrics["keyboard_interactions"] += 2
                log_event("Operator restored the paper window; typing resumed.", print_line=True)
                return
            print("Type R to resume or STOP to end the run.")

    def save_checkpoint(window, reason: str) -> None:
        ensure_focus(window)
        pyautogui.hotkey("ctrl", "s")
        metrics["keyboard_interactions"] += 2
        metrics["saves"] += 1
        time.sleep(0.15)
        log_event(f"Saved Notepad draft ({reason}).", print_line=True)

    def save_recovery_copy(reason: str) -> None:
        # Keep a text copy if the failsafe or an interface error prevents a
        # final Ctrl+S. Do not overwrite the Notepad file, which may include
        # edits made by the operator during a review pause.
        partial = text[:committed_chars]
        recovery_file = output_file.with_name(f"{output_file.stem}_recovery.txt")
        recovery_file.write_text(partial, encoding="ascii", newline="\n")
        metrics["recovery_events"] += 1
        log_event(f"Wrote {recovery_file.name} after interruption: {reason}.", print_line=True)

    def finalize_log(result: str) -> None:
        with activity_file.open("a", encoding="utf-8", newline="\n") as log:
            log.write(f"\n## Final counters: {result}\n\n")
            for key, value in metrics.items():
                log.write(f"- {key.replace('_', ' ').title()}: {value:,}\n")
            log.write(f"- Active typing time: {_duration(active_seconds)}\n")
            log.write(f"- Wall time including review pauses: {_duration(time.monotonic() - run_start)}\n")
            log.write("- Result: plain-text Notepad deliverable; page count depends on print settings.\n")

    def review_navigation(window) -> None:
        ensure_focus(window)
        left = max(5, int(window.left))
        top = max(5, int(window.top))
        width = max(500, int(window.width))
        height = max(400, int(window.height))
        x = left + width - 45
        y = top + height // 2
        pyautogui.moveTo(x, y, duration=0.25)
        metrics["mouse_movements"] += 1
        pyautogui.scroll(3)
        metrics["scroll_actions"] += 1
        pyautogui.hotkey("ctrl", "end")
        metrics["keyboard_interactions"] += 2
        log_event("Navigated through the completed section and returned to the writing position.")

    try:
        logger.info("Launching Notepad for a new paper output: %s", output_file)
        subprocess.Popen(["notepad.exe", str(output_file)])
        time.sleep(1.5)
        paper_window = _target_window(pyautogui, output_file.stem)
        paper_window.activate()
        paper_window.maximize()
        time.sleep(0.25)
        if not foreground_matches():
            raise FocusLostError("Could not confirm the new paper window is active.")
        pyautogui.click(paper_window.left + 150, paper_window.top + 120)
        metrics["mouse_clicks"] += 1
        metrics["mouse_movements"] += 1
        if not foreground_matches():
            raise FocusLostError("Notepad lost foreground focus during setup.")

        with activity_file.open("x", encoding="utf-8", newline="\n") as log:
            log.write("# ZTSS CORE Notepad paper demonstration\n\n")
            log.write(f"Start time: {_local_time()}\n")
            log.write(f"Paper output: {output_file}\n")
            log.write(f"Prepared source: {MANUSCRIPT_PATH}\n")
            log.write(f"Prepared source words: {manuscript_words:,}\n")
            log.write(f"Target: at least {target_words:,} words (approximately 20 double-spaced pages)\n")
            log.write(f"Review gate: every {checkpoint_minutes} minutes of active typing; operator must resume\n")
            log.write("Mode: prepared manuscript typed through Notepad; no local AI model is used\n")
            log.write("Integrity: simulated values are labeled; no real class data or participants are represented\n\n")
            log.write("| Local time | Active time | Wall time | Action | Current section | Words | Keyboard events | Mouse moves | Clicks | Scrolls |\n")
            log.write("|---|---:|---:|---|---|---:|---:|---:|---:|---:|\n")
        log_event("Opened a new Notepad file; existing Notepad tabs were not targeted.", print_line=True)
        print("Review the blank Notepad paper window. Type START in this terminal to begin, or STOP.")
        try:
            answer = input("START/STOP: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            answer = "stop"
        if answer not in {"start", "yes", "y"}:
            log_event("Run cancelled before typing began.", print_line=True)
            finalize_log("cancelled before typing")
            print("Run cancelled before typing.")
            logger.info("Paper run cancelled before typing began.")
            return 0

        activate_target(paper_window)
        pyautogui.hotkey("ctrl", "home")
        metrics["keyboard_interactions"] += 2
        log_event("Started typing the prepared manuscript.", print_line=True)

        for line in text.splitlines(keepends=True):
            ensure_focus(paper_window)
            line_body = line[:-1] if line.endswith("\n") else line
            new_section = _section_name(line_body, current_section)
            if new_section != current_section and metrics["typed_characters"] > 0:
                save_checkpoint(paper_window, "section transition")
                review_navigation(paper_window)
                current_section = new_section
                log_event("Moved to the next paper section.", print_line=True)

            for chunk in _chunks(line_body):
                ensure_focus(paper_window)
                started = time.monotonic()
                pyautogui.write(chunk, interval=typing_interval)
                active_seconds += time.monotonic() - started
                committed_chars += len(chunk)
                metrics["typed_characters"] += len(chunk)
                metrics["keyboard_interactions"] += len(chunk)
                metrics["editing_actions"] += 1
                metrics["typed_words"] = len(text[:committed_chars].split())
                log_event(f"Typed text chunk ({len(chunk)} characters).")

                if metrics["typed_words"] - last_save_words >= 250:
                    save_checkpoint(paper_window, "250-word interval")
                    last_save_words = metrics["typed_words"]

                now = time.monotonic()
                if now - last_status_print >= 60:
                    print(
                        f"Status: active {_duration(active_seconds)}; "
                        f"{metrics['typed_words']:,}/{target_words:,} words; "
                        f"current section: {current_section}"
                    )
                    sys.stdout.flush()
                    last_status_print = now

                if active_seconds >= active_checkpoint_seconds:
                    save_checkpoint(paper_window, "hourly review checkpoint")
                    log_event("Paused for the requested hourly review.", print_line=True)
                    while True:
                        try:
                            answer = input(
                                "Review the saved draft. Type R to resume or STOP to keep this checkpoint: "
                            ).strip().lower()
                        except (EOFError, KeyboardInterrupt):
                            answer = "stop"
                        if answer in {"stop", "s"}:
                            activate_target(paper_window)
                            save_checkpoint(paper_window, "operator stopped at the review checkpoint")
                            metrics["final_file_words"] = len(
                                output_file.read_text(encoding="ascii").split()
                            )
                            log_event("Stopped at the review checkpoint; saved partial paper.", print_line=True)
                            finalize_log("stopped at review checkpoint")
                            return 0
                        if answer in {"r", "resume"}:
                            activate_target(paper_window)
                            pyautogui.hotkey("ctrl", "end")
                            metrics["keyboard_interactions"] += 2
                            active_checkpoint_seconds += checkpoint_minutes * 60
                            log_event("Operator reviewed and resumed the paper.", print_line=True)
                            break
                        print("Type R to resume after review or STOP to end here.")

            if line.endswith("\n"):
                ensure_focus(paper_window)
                started = time.monotonic()
                pyautogui.press("enter")
                active_seconds += time.monotonic() - started
                committed_chars += 1
                metrics["typed_characters"] += 1
                metrics["keyboard_interactions"] += 1
                metrics["editing_actions"] += 1
                metrics["typed_words"] = len(text[:committed_chars].split())
                log_event("Inserted a paragraph break.")

        save_checkpoint(paper_window, "final document save")
        metrics["typed_words"] = len(text.split())
        metrics["final_file_words"] = len(output_file.read_text(encoding="ascii").split())
        log_event("Completed the prepared manuscript.", print_line=True)
        finalize_log("completed")
        print(f"Paper saved: {output_file}")
        print(f"Activity log: {activity_file}")
        print(f"Words typed: {metrics['typed_words']:,}; active typing: {_duration(active_seconds)}")
        return 0

    except pyautogui.FailSafeException:
        print("PyAutoGUI stop failsafe activated. Saving the last committed text as a recovery copy.")
        save_recovery_copy("mouse-corner failsafe")
        finalize_log("stopped by mouse-corner failsafe")
        return 0
    except KeyboardInterrupt:
        print("Run interrupted from the terminal. Saving the last committed text as a recovery copy.")
        save_recovery_copy("Ctrl+C interruption")
        finalize_log("stopped by Ctrl+C")
        return 0
    except Exception as error:
        print(f"The paper run stopped: {error}")
        try:
            save_recovery_copy(f"{type(error).__name__}: {error}")
            finalize_log(f"error: {type(error).__name__}")
        except Exception:
            logger.exception("Could not write the recovery copy.")
        logger.exception("Notepad paper demo failed.")
        return 1

