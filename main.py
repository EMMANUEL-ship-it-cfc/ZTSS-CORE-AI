"""ZTSS CORE launcher.

The launcher stays small so future capabilities can be added as separate
modules. No desktop actions run unless the user explicitly selects --demo.
"""

import argparse
import os
import sys

from automation.notepad_demo import run_notepad_demo
from config.settings import APP_NAME, VERSION
from core.activity_log import configure_activity_log


def build_parser():
    parser = argparse.ArgumentParser(
        prog="main.py",
        description=f"{APP_NAME} {VERSION} - supervised desktop automation prototype",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="run the supervised Notepad typing demo",
    )
    parser.add_argument("--version", action="version", version=f"{APP_NAME} {VERSION}")
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if not args.demo:
        parser.print_help()
        print("\nNo desktop actions run unless you pass --demo.")
        return 0

    if os.name != "nt":
        print("The v0.1 Notepad demo is currently for Windows.", file=sys.stderr)
        return 1

    try:
        import pyautogui
    except ImportError:
        print(
            "PyAutoGUI is not installed. Set up the project environment with "
            "'python -m pip install -r requirements.txt'.",
            file=sys.stderr,
        )
        return 1

    logger = configure_activity_log()
    logger.info("ZTSS CORE %s started with the Notepad demo selected.", VERSION)
    return run_notepad_demo(pyautogui, logger)


if __name__ == "__main__":
    raise SystemExit(main())
