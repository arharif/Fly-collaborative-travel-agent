"""Offline release gate: no network, model invocation, or credentials needed."""
from pathlib import Path
import ast
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
SPACE = ROOT / "space"
README = (SPACE / "README.md").read_text(encoding="utf-8")

# Validate basic HF front matter without depending on PyYAML.
assert README.startswith("---\n"), "Space README needs YAML frontmatter"
metadata = README.split("---", 2)[1]
assert re.search(r"(?m)^sdk:\s*gradio\s*$", metadata), "Need real Gradio Space"
assert re.search(r"(?m)^app_file:\s*app.py\s*$", metadata)
m = re.search(r"(?m)^short_description:\s*(.*)$", metadata)
assert m is not None and 0 < len(m.group(1).strip()) <= 60, "short_description too long"

for name in ("app.py", "agent_backend.py"):
    code = (SPACE / name).read_text(encoding="utf-8")
    ast.parse(code, filename=name)
    assert "from google.colab" not in code, "Hosted files must not import Colab"

requirements = (SPACE / "requirements.txt").read_text(encoding="utf-8")
assert "gradio==6.5.1" in requirements
assert "smolagents[litellm]==1.26.0" in requirements

backend = (SPACE / "agent_backend.py").read_text(encoding="utf-8")
assert "REMOVE_PARAMETER" in backend
assert 'bedrock/deepseek.v3.2' in backend
assert "make_collaborative_travel_agent" in backend

ui = (SPACE / "app.py").read_text(encoding="utf-8")
for required in ("build_trip", "chat_send", "_wiki_media", "preview", "reset"):
    assert f"def {required}(" in ui, required
assert 'type="messages"' not in ui

nb = json.loads((ROOT / "notebooks/FLY_From_Zero_to_Hugging_Face_PRO.ipynb").read_text(encoding="utf-8"))
assert len(nb.get("cells", [])) >= 20
for cell in nb["cells"]:
    if cell.get("cell_type") == "code":
        src = "".join(cell.get("source", []))
        ast.parse(src, filename="notebook_cell")

# Prevent accidental publication of realistic AWS/HF tokens. Avoid scanning older
# user-provided/reference binaries; validate plain-text source in this package.
patterns = [
    ("AWS access key", r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    ("HF token", r"\bhf_[A-Za-z0-9]{25,}\b"),
    ("private key", r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
]
allowed_suffixes = {".py", ".md", ".html", ".css", ".js", ".yml", ".yaml", ".json", ".ipynb", ".example", ".txt"}
for file in ROOT.rglob("*"):
    if not file.is_file() or file.suffix not in allowed_suffixes:
        continue
    if file.stat().st_size > 400_000:
        continue
    txt = file.read_text(encoding="utf-8", errors="ignore")
    for label, expr in patterns:
        assert not re.search(expr, txt), f"Possible {label} in {file.relative_to(ROOT)}"

print("PASS: Space YAML, Python source, pinned versions, notebook, basic credential patterns")
