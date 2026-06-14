BACKENDS = {
    "ollama": {
        "base_url": "http://localhost:11434/v1",
        "default_model": "minimax-m3:cloud",
        "env_key": "OLLAMA_API_KEY",
        "pricing": {"input": 0.0, "output": 0.0},
    },
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "default_model": "gemini-3-flash-preview",
        "env_keys": ["GEMINI_API_KEY", "GOOGLE_API_KEY"],
    },
}


def detect_backend() -> str:
    return "ollama"


def validate_backend_dependencies(backend: str) -> None:
    if backend not in BACKENDS:
        raise ValueError(f"unknown backend: {backend}")
