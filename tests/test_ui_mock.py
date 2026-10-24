"""Smoke tests of Gradio UI with a fake agent; never touches AWS.

Run after installing dependencies:
  pip install -r space/requirements.txt
  python tests/test_ui_mock.py
"""
import sys
import os
# Dummy values pass the application's configuration presence check.
# No cloud request occurs: agent_backend is replaced with FakeAgent.
os.environ["AWS_ACCESS_KEY_ID"] = "MOCK_ONLY_NOT_A_REAL_KEY"
os.environ["AWS_SECRET_ACCESS_KEY"] = "MOCK_ONLY_NOT_A_REAL_KEY"
import types
import importlib.util
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
STUB = types.ModuleType("agent_backend")
class FakeAgent:
    def run(self, prompt, reset=True):
        assert reset is True
        if "MODE A" in prompt:
            return "## Kyoto plan\n### Day 1 — Temples\nVisit **Kinkaku-ji**.\n\n**Why it fits:** Cultural interest.\n```places\nKinkaku-ji\n```"
        return "For your specific question, try a quieter stop before the midday crowds."
STUB.make_collaborative_travel_agent = lambda: FakeAgent()
sys.modules["agent_backend"] = STUB
spec = importlib.util.spec_from_file_location("fly_test_app", ROOT / "space" / "app.py")
app = importlib.util.module_from_spec(spec)
sys.modules["fly_test_app"] = app
spec.loader.exec_module(app)

assert app._resolve_duration("Custom", "2 weeks").startswith("14 days")
inputs = ["Kyoto, Japan", "Custom", "8 days", "Spring", "April", "My partner", 2,
          ["Culture & history"], "Tea ceremonies", "Ryokan", "Balanced mid-range", "Peaceful"]
assert "Other interests: Tea ceremonies" in app._trip_snapshot(*inputs)["interests"]
with patch.object(app, "_wiki_media", lambda _: None):
    # Avoid Wikimedia network calls during pure offline mock tests.
    with patch.object(app, "_place_visuals", lambda places, destination: ("", "<div>Mock cards</div>")):
        steps = list(app.build_trip(*(inputs + [None, None])))
        assert len(steps) >= 2
        history, status, cover, gallery, state = steps[-1]
        assert state["built"] and "Kinkaku-ji" in state["plan"]
        assert "Teа ceremonies" not in state["plan"]  # no unrelated corrupted text
        answers = list(app.chat_send("Can you make Day 1 quieter?", history, state))
        assert len(answers) >= 2
        new_hist, status, new_state, cleared_input = answers[-1]
        assert "quieter" in new_hist[-1]["content"]
        assert new_state["plan"] == state["plan"]
        assert cleared_input == ""
        sample = app.preview()
        assert len(sample) == 5
        cleared = app.reset()
        assert len(cleared) == 18
print("PASS: Gradio UI, duration, custom interests, chat, preserved plan, preview and reset")
