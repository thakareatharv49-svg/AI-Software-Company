from runtime.providers.ollama import OllamaProvider
from runtime.service import AIRuntime

ollama_provider = OllamaProvider()
ai_runtime = AIRuntime(ollama_provider)
