# Using local models with Ollama (optional)

Ollama runs open-weight models on your own machine. It's free and works offline, but it's slower
and less capable than cloud models. That difference is part of the lesson.

## 1. Install Ollama
- **Windows / macOS:** download the installer from https://ollama.com/download and run it.
- **Linux:** `curl -fsSL https://ollama.com/install.sh | sh`

Check it's running: open http://localhost:11434 in a browser. It should say *"Ollama is running"*.
If not, start it with `ollama serve` (or open the Ollama app).

## 2. Download a model that supports tools
Agents need **tool calling**, and not every model supports it. Pick one based on your RAM:

| Your RAM | Model | Command | Download |
|---|---|---|---|
| 8 GB | Qwen3 4B | `ollama pull qwen3:4b` | ~2.5 GB |
| 8 GB (alternative) | Llama 3.2 3B | `ollama pull llama3.2:3b` | ~2 GB |
| 16 GB+ | Qwen3 8B | `ollama pull qwen3:8b` | ~5 GB |

Try it directly: `ollama run qwen3:4b` (type `/bye` to exit).
Check tool support: `ollama show qwen3:4b`. Look for `tools` under *Capabilities*.

> Download the model **before** the workshop. The Wi-Fi won't handle 12 people downloading GBs at once.

## 3. Point the workshop at Ollama
In `.env`:
```
MODEL_PROVIDER=ollama
OLLAMA_MODEL=qwen3:4b
OLLAMA_API_BASE=http://localhost:11434
```
Then: `python scripts/check_setup.py`. The first call loads the model into memory and can take 10–30 s.

## Troubleshooting
| Problem | Fix |
|---|---|
| `Connection refused` / `APIConnectionError` | Ollama isn't running: start the app or `ollama serve` |
| `model "..." not found` | You haven't pulled it: `ollama pull <model>` (name must match `OLLAMA_MODEL`) |
| Very slow answers | Use a smaller model; close other heavy apps |
| Agent ignores tools / loops calling tools | Typical for small models: try `qwen3:8b` or switch back to Bedrock |
| Ollama on another machine | Set `OLLAMA_API_BASE=http://<that-ip>:11434` (start it there with `OLLAMA_HOST=0.0.0.0`) |
