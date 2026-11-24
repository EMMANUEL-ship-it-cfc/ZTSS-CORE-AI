"""ZTSS CORE launcher.

The launcher stays small so future capabilities can be added as separate
modules. No desktop actions run unless the user explicitly selects a demo mode.
"""

import argparse
import math
import os
import sys

from automation.notepad_demo import run_notepad_demo
from automation.notepad_paper_demo import run_notepad_paper_demo
from automation.overnight_demo import run_overnight_demo
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
    parser.add_argument(
        "--paper-demo",
        action="store_true",
        help="type the prepared research-paper manuscript into a new Notepad file",
    )
    parser.add_argument(
        "--overnight-demo",
        action="store_true",
        help="run the prepared writing and review task queue in Notepad with automatic reviews",
    )
    parser.add_argument(
        "--run-hours",
        type=float,
        default=4.0,
        help="maximum wall-clock runtime for --overnight-demo (default: 4 hours)",
    )
    parser.add_argument(
        "--target-words",
        type=int,
        default=5000,
        help="minimum manuscript word count for --paper-demo (default: 5000)",
    )
    parser.add_argument(
        "--checkpoint-minutes",
        type=int,
        default=60,
        help="active typing minutes between review checkpoints (default: 60)",
    )
    parser.add_argument(
        "--typing-interval",
        type=float,
        default=None,
        help="override the mode's default seconds between typed characters",
    )
    parser.add_argument("--version", action="version", version=f"{APP_NAME} {VERSION}")
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if not args.demo and not args.paper_demo and not args.overnight_demo:
        parser.print_help()
        print("\nNo desktop actions run unless you pass --demo, --paper-demo, or --overnight-demo.")
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
    if args.paper_demo:
        typing_interval = args.typing_interval if args.typing_interval is not None else 0.11
        if args.target_words <= 0:
            parser.error("--target-words must be greater than zero")
        if args.checkpoint_minutes <= 0:
            parser.error("--checkpoint-minutes must be greater than zero")
        if not math.isfinite(typing_interval) or not 0 < typing_interval <= 1:
            parser.error("--typing-interval must be greater than 0 and at most 1 second")
        logger.info("ZTSS CORE %s started the Notepad paper demo.", VERSION)
        return run_notepad_paper_demo(
            pyautogui,
            logger,
            target_words=args.target_words,
            checkpoint_minutes=args.checkpoint_minutes,
            typing_interval=typing_interval,
        )

    if args.overnight_demo:
        typing_interval = args.typing_interval if args.typing_interval is not None else 0.15
        if not math.isfinite(args.run_hours) or args.run_hours <= 0:
            parser.error("--run-hours must be greater than zero")
        if args.checkpoint_minutes <= 0:
            parser.error("--checkpoint-minutes must be greater than zero")
        if not math.isfinite(typing_interval) or not 0 < typing_interval <= 1:
            parser.error("--typing-interval must be greater than 0 and at most 1 second")
        logger.info("ZTSS CORE %s started the bounded overnight task queue.", VERSION)
        return run_overnight_demo(
            pyautogui,
            logger,
            max_runtime_hours=args.run_hours,
            checkpoint_minutes=args.checkpoint_minutes,
            typing_interval=typing_interval,
        )

    logger.info("ZTSS CORE %s started with the Notepad demo selected.", VERSION)
    return run_notepad_demo(pyautogui, logger)


if __name__ == "__main__":
    raise SystemExit(main())
