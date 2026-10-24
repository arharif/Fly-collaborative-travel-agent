---
title: Fly - AI Travel Concierge
emoji: ✈️
colorFrom: pink
colorTo: purple
sdk: gradio
sdk_version: 6.5.1
app_file: app.py
python_version: "3.11"
short_description: AI travel concierge using DeepSeek V3.2 on Bedrock
suggested_hardware: cpu-basic
---

# Fly - Collaborative Travel Agent

A premium, pink travel-planning application using **Gradio**, **Smolagents**, **LiteLLM**, and **DeepSeek V3.2** via **AWS Bedrock**. Use your own AWS credentials and limits; never hardcode secrets.

## Space configuration

**Secrets:** `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `FLY_APP_PASSWORD`; optional `FLY_APP_USER` (defaults to `traveler`) and `AWS_SESSION_TOKEN` for temporary credentials.

**Variables:** `AWS_REGION=us-east-1` (use only a region where your model is enabled).

Use Preview (no AWS) before Design my journey. Code deployment and runtime availability depend on external services and credentials. Review the accompanying GitHub tutorial for complete setup and security guidance.
