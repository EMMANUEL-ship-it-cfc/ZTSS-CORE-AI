"""ZTSS CORE launcher.

The launcher stays small so future capabilities can be added as separate
modules. No desktop actions run unless the user explicitly selects a demo mode.
"""

import argparse
import math
import os
import sys

from automation.coding_agent_demo import run_coding_agent_demo
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
    parser.add_argument(
        "--coding-agent",
        action="store_true",
        help="let a model write, test, and fix a small program (free local model by default)",
    )
    parser.add_argument(
        "--provider",
        choices=("ollama", "anthropic"),
        default="ollama",
        help="model source for --coding-agent: free local Ollama (default) or paid Anthropic API",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="model name for --coding-agent (default depends on --provider)",
    )
    parser.add_argument("--goal", default=None, help="what the coding agent should build")
    parser.add_argument(
        "--max-hours",
        type=float,
        default=3.0,
        help="maximum wall-clock runtime for --coding-agent (default and ceiling: 3 hours)",
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=10,
        help="maximum model rounds for --coding-agent (default: 10, ceiling: 30)",
    )
    parser.add_argument(
        "--auto-run",
        action="store_true",
        help="run tests without asking first (the code is not sandboxed; use with care)",
    )
    parser.add_argument(
        "--no-editor",
        action="store_true",
        help="do not open the generated code in VS Code",
    )
    parser.add_argument(
        "--allow-test-edits",
        action="store_true",
        help="let the model change its test files after the first step",
    )
    parser.add_argument("--version", action="version", version=f"{APP_NAME} {VERSION}")
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if not (args.demo or args.paper_demo or args.overnight_demo or args.coding_agent):
        parser.print_help()
        print(
            "\nNothing runs unless you pass --demo, --paper-demo, --overnight-demo, "
            "or --coding-agent."
        )
        return 0

    if args.coding_agent:
        # The coding agent needs neither PyAutoGUI nor Windows: it writes files and runs tests.
        if not math.isfinite(args.max_hours) or not 0 < args.max_hours <= 3.0:
            parser.error("--max-hours must be above 0 and at most 3")
        if not 1 <= args.max_steps <= 30:
            parser.error("--max-steps must be between 1 and 30")
        logger = configure_activity_log()
        logger.info("ZTSS CORE %s started the coding agent.", VERSION)
        return run_coding_agent_demo(
            logger,
            goal=args.goal,
            provider=args.provider,
            model=args.model,
            max_hours=args.max_hours,
            max_steps=args.max_steps,
            auto_run=args.auto_run,
            open_editor=not args.no_editor,
            allow_test_edits=args.allow_test_edits,
        )

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
