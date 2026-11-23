# ZTSS CORE

ZTSS CORE is a planned, modular Windows desktop automation project. Version 0.1 starts with one supervised Notepad demonstration. Later work can add reusable routines, screen awareness, and AI-assisted planning in separate modules.

## Version 0.1 demo

The launcher does nothing to the desktop by default. The demo must be selected explicitly and confirmed at the prompt. It opens Notepad, types one fixed test sentence, waits briefly, and switches back to the previously active window. It does not save the Notepad document, send messages, publish content, make purchases, or delete files.

Move the mouse to the upper-left corner of the screen to trigger PyAutoGUI's stop failsafe. Ctrl+C in the terminal also interrupts the sequence while the terminal can receive keyboard input.

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
```

The first command prints help without controlling the desktop. The second asks for confirmation before starting the demo. Activity is recorded locally in `logs/ztss_core.log`.

## Project layout

- `main.py` is the long-term launcher.
- `automation/` contains desktop action routines.
- `config/` holds small user-editable settings.
- `core/` contains shared services such as activity logging.
- `logs/` is created when the program runs.

The first milestone stays intentionally narrow. Add and understand each capability before expanding the agent's reach.
