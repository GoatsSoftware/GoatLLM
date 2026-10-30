"""Planned: OllamaProvider using an injected, application-owned httpx.AsyncClient.

POST /api/chat with stream=false and bounded generation settings. Return only
message.content. Model, keep_alive, and thinking policy belong to this adapter.
"""
