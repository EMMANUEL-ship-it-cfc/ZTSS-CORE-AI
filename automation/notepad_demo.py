"""A small, supervised Windows desktop automation demonstration."""

import subprocess
import time

from config.settings import DEMO_TEXT, DEMO_WAIT_SECONDS


def run_notepad_demo(pyautogui, logger):
    """Open Notepad, type fixed demo text, wait, then switch back.

    The demo never saves the Notepad document. PyAutoGUI's upper-left-corner
    failsafe remains enabled so the user can stop the sequence quickly.
    """
    print("This demo opens Notepad, types one fixed sentence, waits, and switches back.")
    print("It does not save the Notepad document or interact with other services.")
    print("Move the mouse to the upper-left corner of the screen to trigger the stop failsafe.")

    try:
        answer = input("Run the demo? [y/N]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("Demo cancelled.")
        logger.info("Demo cancelled before desktop actions started.")
        return 0

    if answer not in {"y", "yes"}:
        print("Demo cancelled.")
        logger.info("Demo cancelled before desktop actions started.")
        return 0

    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.2

    try:
        print("Starting in 3 seconds. Press Ctrl+C in this terminal to cancel.")
        time.sleep(3)

        logger.info("Launching Notepad.")
        subprocess.Popen(["notepad.exe"])
        time.sleep(2)

        logger.info("Typing the predefined demo sentence into the active window.")
        pyautogui.write(DEMO_TEXT, interval=0.03)
        pyautogui.press("enter")
        time.sleep(DEMO_WAIT_SECONDS)

        logger.info("Switching to the previously active window.")
        pyautogui.hotkey("alt", "tab")
        print("Demo finished. The Notepad text was not saved.")
        logger.info("Demo finished; no document was saved.")
        return 0
    except pyautogui.FailSafeException:
        print("Stopped by the mouse-corner failsafe.")
        logger.warning("Demo stopped by the PyAutoGUI failsafe.")
        return 0
    except KeyboardInterrupt:
        print("Demo interrupted.")
        logger.warning("Demo interrupted by Ctrl+C.")
        return 0
    except Exception:
        print("The demo stopped because an error occurred. See logs/ztss_core.log.")
        logger.exception("Demo failed.")
        return 1
