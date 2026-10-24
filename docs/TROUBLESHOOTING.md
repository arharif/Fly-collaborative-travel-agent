# Troubleshooting — diagnose one layer at a time

## Dependency hierarchy

1. **AWS credentials** → STS test.
2. **Bedrock authorization / model** → short direct LiteLLM test.
3. **Smolagents** → create/run agent.
4. **Gradio** → Preview UI without AWS.
5. **Wikimedia** → optional images and links; should not block results.
6. **Hugging Face** → right SDK, root files, secrets, running logs.

## Known project-specific errors

| Symptom | Explanation | Fix |
|---|---|---|
| `SignatureDoesNotMatch` | wrong AWS key/secret pair or stale session | refresh both secrets; restart boto3; include STS session token if required |
| `AccessDeniedException` | IAM/model onboarding wrong | verify action `bedrock:InvokeModel`, target ARN, region, model access |
| `stopSequences` unsupported | DeepSeek V3.2 Bedrock rejects stop sequence | use tested `stop=REMOVE_PARAMETER` in backend |
| `Chatbot.__init__ got unexpected keyword 'type'` | Gradio 6 removed parameter | remove `type`, pin Gradio 6.5.1 |
| `css`/`theme` move warning | Gradio 6 changed APIs | supply `css=` and `theme=` to `launch()` |
| `gradio.components.Component` missing | inconsistent package versions/partial install | reinstall from requirements, restart runtime |
| `HTTP 400 Invalid metadata` | Space README `short_description` too long | keep <=60 chars; run repo validation |
| `HTTP 402 Payment Required` | account lacks eligible PRO for CPU Gradio | check HF PRO active under publishing username |
| `404 repo revision/main` | Space not created, wrong ID/type or unauthorized | check space exists, SDK Gradio, token rights |
| Space says “Running” but chat doesn't respond | backend/container or missing secrets | look at Space → Logs → Container |
| “Fly is not yet connected to AWS” | secrets not present in HF runtime | configure Space Settings → Secrets, restart |
| “refused to connect” | HF page loaded inside blocked iframe | open top-level tab or correct Static-vs-Gradio confusion |
| no photo cards | Wikimedia unavailable/unmatched | click Preview; inspect logs, don't fabricate images |
| Colab Cell 16 keeps running | Gradio server blocking behavior | stop the cell; for local test use `prevent_thread_lock=True`, `debug=False` |
| source upload successful, UI old | wrong Space or cached rebuild | verify commit, wait for rebuild, hard-refresh browser |

## Recovery flow

**First** test Preview: if Preview fails, diagnose Gradio/media independently of Bedrock. **Next** test small AWS call; if that fails, diagnose credentials/IAM. **Then** run Generate; if model works but agent fails, inspect agent logs/action limit. Do not rotate valid credentials to fix an unrelated front-end bug.

## Logs and privacy

Before sharing a traceback, remove AWS access key IDs, secret keys, session tokens, HF tokens, Gradio passwords, private customer information and account identifiers. Avoid enabling highly verbose request logging during public demo.

## Deployment rollback

Hugging Face Spaces are git repositories. If a new commit breaks the app, use repository history to restore the last known-good files, or re-upload the validated `space/` folder from the prior GitHub commit. Verify secrets remain configured and test again.
