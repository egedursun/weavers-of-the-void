import json
from dataclasses import dataclass, field
from enum import StrEnum

from aerona.core.total import total
from aerona.domain.enums.providers import ModelRole, ProviderFamily, ProviderKind

HOME = "{home}"
SUBSCRIPTION_TERMS = (
    "Using a subscription inside another program may be against the provider's terms. The provider can limit or close the account; the risk is yours."
)
ANSWER_TOOL = "answer"
ANSWER_DESCRIPTION = "Hand in the finished result. The input of this tool is the result itself."
ANSWER_INSTRUCTION = "When the result is ready, call the tool named answer once, with the whole result as its input."
ANSWER_RECORDED = "Recorded."
CHECK_TOOL = "echo"
CHECK_TOOL_DESCRIPTION = "Repeat a word back."
CHECK_WORD = "ready"
CHECK_SYSTEM = "Follow the instruction exactly."
CHECK_PROMPT = "Call the tool named echo with the word ready as its input, then answer with the single word done."
CHECK_PICTURE_PROMPT = "Which colour fills this picture? Answer with one English word."
CHECK_PICTURE_ANSWER = "red"
TEAM_SUBSCRIPTION_REASON = "A subscription belongs to one person, so it can only be logged in to in a personal workspace."
GEMINI_OWN_TOOLS = (
    "update_topic",
    "list_directory",
    "read_file",
    "grep_search",
    "glob",
    "replace",
    "write_file",
    "web_fetch",
    "run_shell_command",
    "list_background_processes",
    "read_background_output",
    "google_web_search",
    "enter_plan_mode",
    "invoke_agent",
    "activate_skill",
)
CODEX_OWN_FEATURES = (
    "shell_tool",
    "unified_exec",
    "goals",
    "multi_agent",
    "view_image",
    "image_generation",
    "apps",
    "browser_use",
    "computer_use",
    "skill_search",
    "shell_snapshot",
)


class LoginDone(StrEnum):
    EXIT = "exit"
    FILE = "file"
    TOKEN = "token"


@dataclass(frozen=True)
class LoginSpec:
    program: str
    arguments: tuple[str, ...]
    done: LoginDone
    environment: dict[str, str] = field(default_factory=dict)
    file: str = ""
    token_pattern: str = ""


@dataclass(frozen=True)
class AgentSpec:
    program: str
    arguments: tuple[str, ...]
    environment: dict[str, str]
    login: LoginSpec
    files: dict[str, str] = field(default_factory=dict)
    secret_variable: str = ""
    auth_method: str = ""
    session_meta: dict[str, object] = field(default_factory=dict)
    session_mode: str = ""
    marks_messages: bool = False


@dataclass(frozen=True)
class ProviderSpec:
    label: str
    family: ProviderFamily
    roles: frozenset[ModelRole]
    asks_key: bool = False
    asks_address: bool = False
    gateway_name: str = ""
    key_page: str = ""
    agent: AgentSpec | None = None


TEXT_ROLES = frozenset({ModelRole.WORLD_AGENTS, ModelRole.WRITING, ModelRole.CONVERSATION})
TEXT_AND_IMAGES = TEXT_ROLES | {ModelRole.IMAGES}

CODEX_CONFIG = "\n".join(('web_search = "disabled"', "[features]", *(f"{name} = false" for name in CODEX_OWN_FEATURES), ""))
GEMINI_SETTINGS = json.dumps(
    {
        "security": {"auth": {"selectedType": "oauth-personal"}, "folderTrust": {"enabled": False}},
        "tools": {"exclude": list(GEMINI_OWN_TOOLS)},
        "skills": {"enabled": False},
    },
    indent=2,
)


def api(label: str, gateway_name: str, key_page: str, roles: frozenset[ModelRole] = TEXT_ROLES) -> ProviderSpec:
    return ProviderSpec(label, ProviderFamily.API, roles, asks_key=True, gateway_name=gateway_name, key_page=key_page)


PROVIDERS = total(
    ProviderKind,
    {
        ProviderKind.CLAUDE_SUBSCRIPTION: ProviderSpec(
            "Claude Pro or Max",
            ProviderFamily.SUBSCRIPTION,
            TEXT_ROLES,
            agent=AgentSpec(
                program="claude-agent-acp",
                arguments=(),
                environment={"CLAUDE_CONFIG_DIR": f"{HOME}/.claude", "ENABLE_TOOL_SEARCH": "false", "DISABLE_AUTOUPDATER": "1"},
                secret_variable="CLAUDE_CODE_OAUTH_TOKEN",
                session_meta={"claudeCode": {"options": {"tools": [], "settingSources": []}}},
                session_mode="bypassPermissions",
                marks_messages=True,
                login=LoginSpec("claude", ("setup-token",), LoginDone.TOKEN, token_pattern=r"(sk-ant-oat[0-9A-Za-z_\-]+)"),
            ),
        ),
        ProviderKind.CHATGPT_SUBSCRIPTION: ProviderSpec(
            "ChatGPT Plus or Pro",
            ProviderFamily.SUBSCRIPTION,
            TEXT_ROLES,
            agent=AgentSpec(
                program="codex-acp",
                arguments=(),
                environment={"CODEX_HOME": HOME},
                files={"config.toml": CODEX_CONFIG},
                auth_method="chat-gpt",
                session_mode="read-only",
                marks_messages=True,
                login=LoginSpec("codex", ("login", "--device-auth"), LoginDone.EXIT, environment={"CODEX_HOME": HOME}),
            ),
        ),
        ProviderKind.GEMINI_SUBSCRIPTION: ProviderSpec(
            "Google AI Pro or Ultra",
            ProviderFamily.SUBSCRIPTION,
            TEXT_ROLES,
            agent=AgentSpec(
                program="gemini",
                arguments=("--acp",),
                environment={"GEMINI_CLI_HOME": HOME},
                files={".gemini/settings.json": GEMINI_SETTINGS},
                auth_method="oauth-personal",
                login=LoginSpec("gemini", (), LoginDone.FILE, environment={"GEMINI_CLI_HOME": HOME, "NO_BROWSER": "true"}, file=".gemini/oauth_creds.json"),
            ),
        ),
        ProviderKind.COPILOT_SUBSCRIPTION: ProviderSpec(
            "GitHub Copilot",
            ProviderFamily.SUBSCRIPTION,
            TEXT_ROLES,
            agent=AgentSpec(
                program="copilot",
                arguments=("--acp", "--disable-builtin-mcps", "--no-custom-instructions", "--no-auto-update", "--available-tools", "{tool_server}"),
                environment={"COPILOT_HOME": f"{HOME}/.copilot"},
                marks_messages=True,
                login=LoginSpec("copilot", ("login", "--device-code"), LoginDone.EXIT, environment={"COPILOT_HOME": f"{HOME}/.copilot"}),
            ),
        ),
        ProviderKind.OPENAI: api("OpenAI", "openai", "https://platform.openai.com/api-keys", TEXT_AND_IMAGES),
        ProviderKind.ANTHROPIC: api("Anthropic", "anthropic", "https://console.anthropic.com/settings/keys"),
        ProviderKind.GEMINI: api("Google Gemini", "gemini", "https://aistudio.google.com/apikey", TEXT_AND_IMAGES),
        ProviderKind.MISTRAL: api("Mistral", "mistral", "https://console.mistral.ai/api-keys"),
        ProviderKind.GROQ: api("Groq", "groq", "https://console.groq.com/keys"),
        ProviderKind.DEEPSEEK: api("DeepSeek", "deepseek", "https://platform.deepseek.com/api_keys"),
        ProviderKind.XAI: api("xAI", "xai", "https://console.x.ai"),
        ProviderKind.OPENROUTER: api("OpenRouter", "openrouter", "https://openrouter.ai/keys"),
        ProviderKind.COHERE: api("Cohere", "cohere", "https://dashboard.cohere.com/api-keys"),
        ProviderKind.CEREBRAS: api("Cerebras", "cerebras", "https://cloud.cerebras.ai"),
        ProviderKind.PERPLEXITY: api("Perplexity", "perplexity", "https://www.perplexity.ai/settings/api"),
        ProviderKind.REPLICATE: api("Replicate", "replicate", "https://replicate.com/account/api-tokens", TEXT_AND_IMAGES),
        ProviderKind.HUGGINGFACE: api("Hugging Face", "huggingface", "https://huggingface.co/settings/tokens", TEXT_AND_IMAGES),
        ProviderKind.LOCAL_SERVER: ProviderSpec("Local model server", ProviderFamily.LOCAL, TEXT_ROLES, asks_key=True, asks_address=True),
        ProviderKind.IMAGE_WORKER: ProviderSpec("Local image worker", ProviderFamily.LOCAL, frozenset({ModelRole.IMAGES}), asks_address=True),
    },
)

ROLE_LABELS = total(
    ModelRole,
    {
        ModelRole.WORLD_AGENTS: "World agents",
        ModelRole.WRITING: "Writing",
        ModelRole.CONVERSATION: "Conversation",
        ModelRole.IMAGES: "Images",
    },
)
ROLE_DESCRIPTIONS = total(
    ModelRole,
    {
        ModelRole.WORLD_AGENTS: "The sons, mortals and fallen who act during an age.",
        ModelRole.WRITING: "Genesis, the chronicle, fate, councils, voices, deepening, naming, translation and image prompts.",
        ModelRole.CONVERSATION: "The Divine Will and Presence. A model that sees pictures can read the ones you attach.",
        ModelRole.IMAGES: "Pictures of things and covers. A picture model proves itself when it draws; a failed picture is noted on the image queue.",
    },
)


def is_subscription(kind: ProviderKind) -> bool:
    return PROVIDERS[kind].family is ProviderFamily.SUBSCRIPTION


def serves(kind: ProviderKind, role: ModelRole) -> bool:
    return role in PROVIDERS[kind].roles
