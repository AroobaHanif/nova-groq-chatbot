import json
from chatbot import build_messages, export_json, export_markdown, export_txt, redact_secrets

def test_build_messages_memory_and_latest_only():
    history=[{"role":"user","content":"old"},{"role":"assistant","content":"answer"}]
    assert build_messages(history,"system",True,2)[0]["role"]=="system"
    assert build_messages(history,"system",False,2,"new")==[{"role":"system","content":"system"},{"role":"user","content":"new"}]

def test_redact_secrets():
    assert "gsk_••••••••" in redact_secrets("failed gsk_1234567890")
    assert "1234567890" not in redact_secrets("failed gsk_1234567890")

def test_exports():
    messages=[{"role":"user","content":"Hello"},{"role":"assistant","content":"Hi"}]
    assert "USER: Hello" in export_txt(messages)
    assert "# NOVA Chat" in export_markdown(messages,"model")
    result=export_json(messages,"model",{"temperature":.7})
    assert json.loads(result)["model"]=="model" and "GROQ_API_KEY" not in result
