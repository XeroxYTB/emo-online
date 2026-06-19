"""OpenAI-compat message formatting (tool_call_id required for HF/Groq)."""
from emergentintegrations.llm.chat import LlmChat


def test_openai_messages_include_tool_call_id():
    chat = LlmChat(provider="huggingface", model="meta-llama/Llama-3.3-70B-Instruct")
    chat._messages = [
        {"role": "user", "content": "hi"},
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [{"id": "call_1", "type": "function", "function": {"name": "web_search", "arguments": "{}"}}],
        },
        {"role": "tool", "tool_call_id": "call_1", "content": '{"ok": true}'},
    ]
    msgs = chat._openai_messages()
    tool_msgs = [m for m in msgs if m.get("role") == "tool"]
    assert len(tool_msgs) == 1
    assert tool_msgs[0]["tool_call_id"] == "call_1"
