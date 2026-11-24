# ZTSS CORE

ZTSS CORE is a modular Windows desktop automation project. The current prototype includes a short supervised Notepad check and a prepared-manuscript paper demonstration. Later work can add reusable routines, screen awareness, and AI-assisted planning in separate modules.

## Version 0.1 demo

The launcher does nothing to the desktop by default. The demo must be selected explicitly and confirmed at the prompt. It opens Notepad, types one fixed test sentence, waits briefly, and switches back to the previously active window. It does not save the Notepad document, send messages, publish content, make purchases, or delete files.

Move the mouse to the upper-left corner of the screen to trigger PyAutoGUI's stop failsafe. Ctrl+C in the terminal also interrupts the sequence while the terminal can receive keyboard input.

## Notepad paper demonstration

`--paper-demo` types the prepared literature-based manuscript in `automation/paper_manuscript.txt` into a new, timestamped plain-text file under `demo_output/`. The manuscript contains an explicit disclosure that it is a demonstration, and its example results are labeled simulated. This prototype does not include a local AI model; the run automates keyboard entry, navigation, saves, and logging for prepared text.

The default target is at least 5,000 words, approximately 20 double-spaced academic pages after formatting. Notepad does not provide a dependable page count; the printed length depends on font and page settings. The default typing interval is 0.11 seconds per character. The run saves about every 250 words and pauses after each 60 minutes of active typing. At a checkpoint, review the saved Notepad file and type `R` in the terminal to resume or `STOP` to keep the partial paper. Review time is excluded from active typing time.

The paper file and a separate action log are created for each run. The log records section transitions, typed chunks, saves, elapsed time, and keyboard and mouse interaction counts. Existing Notepad tabs are not selected or closed. Keep the VS Code terminal available for checkpoint prompts; move the mouse to the upper-left corner to trigger PyAutoGUI's failsafe, or use Ctrl+C while the terminal has focus.

## Set up

From this project folder, create and activate a virtual environment, then install the listed dependency:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

If the `py` launcher is unavailable, use `python` to create the virtual environment.

## Run

```powershell
python main.py
python main.py --demo
python main.py --paper-demo
```

The first command prints help without controlling the desktop. `--demo` asks for confirmation before starting the short demo. `--paper-demo` asks for confirmation, opens a new Notepad file, and asks for a second `START` confirmation before typing. Activity is recorded locally in `logs/ztss_core.log` and in a per-run Markdown log under `demo_output/`.

## Project layout

- `main.py` is the long-term launcher.
- `automation/` contains desktop action routines.
- `config/` holds small user-editable settings.
- `core/` contains shared services such as activity logging.
- `demo_output/` contains local demonstration papers and per-run activity logs; Git ignores it.
- `logs/` is created when the program runs.

The first milestone stays intentionally narrow. Add and understand each capability before expanding the agent's reach.
