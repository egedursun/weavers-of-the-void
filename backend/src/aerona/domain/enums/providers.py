from enum import StrEnum


class ProviderFamily(StrEnum):
    SUBSCRIPTION = "subscription"
    API = "api"
    LOCAL = "local"


class ProviderKind(StrEnum):
    CLAUDE_SUBSCRIPTION = "claude_subscription"
    CHATGPT_SUBSCRIPTION = "chatgpt_subscription"
    GEMINI_SUBSCRIPTION = "gemini_subscription"
    COPILOT_SUBSCRIPTION = "copilot_subscription"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    MISTRAL = "mistral"
    GROQ = "groq"
    DEEPSEEK = "deepseek"
    XAI = "xai"
    OPENROUTER = "openrouter"
    COHERE = "cohere"
    CEREBRAS = "cerebras"
    PERPLEXITY = "perplexity"
    REPLICATE = "replicate"
    HUGGINGFACE = "huggingface"
    LOCAL_SERVER = "local_server"
    IMAGE_WORKER = "image_worker"


class ModelRole(StrEnum):
    WORLD_AGENTS = "world_agents"
    WRITING = "writing"
    CONVERSATION = "conversation"
    IMAGES = "images"


class LoginState(StrEnum):
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
