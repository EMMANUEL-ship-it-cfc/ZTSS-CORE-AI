"""Small, user-editable settings for the v0.1 prototype."""

APP_NAME = "ZTSS CORE"
VERSION = "0.1.0"

DEMO_TEXT = "ZTSS CORE v0.1 desktop automation check."
DEMO_WAIT_SECONDS = 3

# Coding agent models. Override either one with --model.
# OLLAMA_MODEL runs free on this computer; use a smaller one such as qwen2.5-coder:3b on low-RAM laptops.
OLLAMA_MODEL = "qwen2.5-coder:7b"
# CODING_AGENT_MODEL is the paid cloud model used with --provider anthropic.
CODING_AGENT_MODEL = "claude-sonnet-5-5"
