# Minimal FastAPI example

```bash
cd ardkit-py
uv run --extra fastapi uvicorn examples.fastapi_min.app:app --reload
```

```bash
curl -s localhost:8000/.well-known/ai-catalog.json | jq
curl -s localhost:8000/robots.txt
curl -s localhost:8000/ard/search -H 'content-type: application/json' \
  -d '{"query":{"text":"weather forecast"}}' | jq
curl -s localhost:8000/ard/explore -H 'content-type: application/json' \
  -d '{"resultType":{"facets":[{"field":"type"}]}}' | jq
curl -s "localhost:8000/ard/agents?filter=type%20=%20'application/a2a-agent-card+json'" | jq
```
