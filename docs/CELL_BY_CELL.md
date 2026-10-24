# Colab notebook: cell by cell

The included standalone notebook `notebooks/FLY_From_Zero_to_Hugging_Face_PRO.ipynb` has its own sequence of labeled cells. The professor's original assignment notebook is **different**, so do not assume cell index numbers are interchangeable.

## Professor notebook (verified roles only)

| Professor index | Purpose | Key idea / likely problem |
|---|---|---|
| 5 | AWS auth | Colab Secrets / boto3 Session; never hardcode keys |
| 6 | DeepSeek V3.2 model | `LiteLLMModel(model_id='bedrock/deepseek.v3.2', stop=REMOVE_PARAMETER)` |
| 8 | User profile, common-ground and input tools | `@tool` functions called with structured strings |
| 9 | Baseline `CodeAgent` | preserved for A/B experiments |
| 10 | Baseline `GradioUI` | may need version-compatible dependencies; `debug=True` blocks |
| 11 | replay | inspect agent actions and tool calls |
| 12 | memory | inspect agent step messages; do not expose private context |
| 14 | collaborative `CodeAgent` | purposeful prompts, personalization, efficient use |
| 16 | improved Gradio UI | pink form, day-by-day plan, free-text chat |
| After 16 | Hugging Face publishing | authenticates, uploads `space/` source, checks runtime |

## Standalone notebook in this repository

| Notebook section | Objective | Validation |
|---|---|---|
| 00 | Configure repo identity | GitHub repo can be cloned |
| 01 | Install pinned libraries | import checks succeed |
| 02 | Read Colab Secrets | no values printed |
| 03 | AWS STS identity | authenticated AWS caller |
| 04 | DeepSeek LiteLLM test | first small model response |
| 05 | Understand the backend | agent object created, tools listed |
| 06 | Run local Gradio UI | generated share URL; demo works |
| 07 | HF token / account | correct HF username |
| 08 | Upload to Gradio Space | four files at repo root |
| 09 | Check Space runtime | status and file list |
| 10 | Evaluate system | test prompt and A/B evidence checklist |

## How to interpret outputs

**AWS STS success** ≠ **Bedrock inference authorized**. **HF upload success** ≠ **running chatbot**. **Photo query success** ≠ **correct attraction match**. Each requires its own validation.

## Custom functions from professor's Cell 8

`infer_user_profile_from_conversation` and `infer_task_commonground_from_conversation` were used in the professor baseline. The deployed standalone backend uses a smaller set of generic web tools and explicit session context in `gr.State`; it does **not** import the professor's original Colab Cell 8. Avoid stating that those custom tools are deployed when they are not present in `space/agent_backend.py`.

## Notebook design choice

The included reproducible notebook clones the GitHub code and imports `space/app.py`. That intentionally tests the **exact hosted implementation**, instead of maintaining another independently edited UI that can diverge from deployed files. The professor's original baseline and the previously developed Cell 14/16 remain available as reference files under `notebooks/Professor_Cell_*_Reference.py`.
