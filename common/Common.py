
# 意图到智能体的映射
INTENT_TO_AGENT = {
    "RECOMMEND": "recommend_agent",
    "BUY": "buy_agent",
    "CONSULT": "consult_agent",
    "KNOWLEDGE": "knowledge_agent",
    "UNKNOWN": "unknown_agent",
}

# 业务系统网关的微服务名称
GATEWAY_SERVICE_NAME = "gateway-service"

# ============================
# server 配置
# ============================
SERVER_PORT = "server.port"  # 服务端口
SERVER_HOST = "server.host"  # 监听所有网络接口
SERVER_LOGGER_FILE = "server.logger.file"  # 日志输出文件
SERVER_LOGGER_LEVEL = "server.logger.level"  # 日志级别

# ============================
# nacos 配置
# ============================
NACOS_SERVER_ADDR = "nacos.server-addr"  # NACOS 注册中心地址
NACOS_USERNAME = "nacos.username"  # NACOS 用户名
NACOS_PASSWORD = "nacos.password"  # NACOS 密码

NACOS_CONFIG_NAMESPACE = "nacos.config.namespace"  # NACOS 配置 namespace
NACOS_CONFIG_GROUP = "nacos.config.group"  # NACOS 配置 group

NACOS_DISCOVERY_NAME = "nacos.discovery.name"  # 服务注册名称
NACOS_DISCOVERY_NAMESPACE = "nacos.discovery.namespace"  # 服务发现 namespace
NACOS_DISCOVERY_IP = "nacos.discovery.ip"  # 服务注册 IP

# ============================
# AI-agent checkpoint 配置
# ============================
AI_AGENT_CHECKPOINTER_POSTGRES_USER = "ai.agent.checkpointer.postgres.user"  # Postgres 用户名
AI_AGENT_CHECKPOINTER_POSTGRES_PASSWORD = "ai.agent.checkpointer.postgres.password"  # Postgres 密码
AI_AGENT_CHECKPOINTER_POSTGRES_HOST = "ai.agent.checkpointer.postgres.host"  # Postgres host
AI_AGENT_CHECKPOINTER_POSTGRES_PORT = "ai.agent.checkpointer.postgres.port"  # Postgres 端口
AI_AGENT_CHECKPOINTER_POSTGRES_DATABASE = "ai.agent.checkpointer.postgres.database"  # 数据库名
AI_AGENT_CHECKPOINTER_POSTGRES_MIN = "ai.agent.checkpointer.postgres.min"  # 最小连接数
AI_AGENT_CHECKPOINTER_POSTGRES_MAX = "ai.agent.checkpointer.postgres.max"  # 最大连接数
AI_AGENT_CHECKPOINTER_POSTGRES_URL = "ai.agent.checkpointer.postgres.url"  # Postgres 完整 URL

# ============================
# AI OpenAI 配置
# ============================
AI_OPENAI_MODEL = "ai.openai.model"  # 模型名称
AI_OPENAI_API_KEY = "ai.openai.api-key"  # API Key
AI_OPENAI_BASE_URL = "ai.openai.base-url"  # Base URL
AI_OPENAI_TEMPERATURE = "ai.openai.temperature"  # Temperature 参数
AI_OPENAI_TIMEOUT = "ai.openai.timeout"  # 请求超时时间

# ============================
# AI 1001 & 1003 会话配置
# ============================
AI_1001_SESSION_TITLE = "ai.1001.session.title"
AI_1001_SESSION_DESCRIBE = "ai.1001.session.describe"
AI_1001_SESSION_EXAMPLES = "ai.1001.session.examples"

AI_1003_SESSION_TITLE = "ai.1003.session.title"
AI_1003_SESSION_DESCRIBE = "ai.1003.session.describe"
AI_1003_SESSION_EXAMPLES = "ai.1003.session.examples"

# ============================
# prompt 配置
# ============================

INTENT_PROMPT_DATA_ID = "prompt.intent.prompt.data-id"
INTENT_JSON_INSTRUCTION_DATA_ID = "prompt.intent.json-instruction.data-id"
PLANNER_PROMPT_DATA_ID = "prompt.planner.prompt.data-id"
FORMAT_PLAN_PROMPT_DATA_ID = "prompt.planner.format-plan.data-id"
FORMAT_JSON_INSTRUCTION_DATA_ID = "prompt.planner.format-json-instruction.data-id"
KNOWLEDGE_PROMPT_DATA_ID = "prompt.knowledge.prompt.data-id"
OTHER_PROMPT_DATA_ID = "prompt.other.prompt.data-id"
ROUTE_PROMPT_DATA_ID = "prompt.route.prompt.data-id"

# ============================
# db 配置
# ============================
DB_URL = "db.url"  # 数据库连接 URL
DB_POOL_SIZE = "db.pool_size"  # 连接池大小
DB_MAX_OVERFLOW = "db.max_overflow"  # 最大溢出连接数
DB_POOL_TIMEOUT = "db.pool_timeout"  # 无连接时的等待时间
DB_POOL_RECYCLE = "db.pool_recycle"  # 连接回收时间
DB_ECHO = "db.echo"  # 是否输出 SQL

# ============================
# jwt 配置
# ============================
JWT_PRIVATE_KEY = "jwt.private_key"  # JWT 私钥
JWT_PUBLIC_KEY = "jwt.public_key"  # JWT 公钥
JWT_EXPIRE_HOURS = "jwt.expire_hours"  # Token 有效期（小时）

# ============================
# redis 配置
# ============================
REDIS_HOST = "redis.host"  # Redis 主机
REDIS_PORT = "redis.port"  # Redis 端口
REDIS_PASSWORD = "redis.password"  # Redis 密码

# ============================
# a2a 服务
# ============================
A2A_SERVERS = "a2a.servers"  # a2a 服务列表

# ============================
# mcp-servers 配置
# ============================
MCP_SERVERS = "mcp-servers"  # MCP 服务器配置

# ============================
# 高德地图配置（出行 Agent）
# ============================
AMAP_KEY = "amap.key"  # 高德 Web 服务 API Key（需申请「Web服务」类型，不是 JS API Key）
AMAP_TIMEOUT = "amap.timeout"  # 高德接口请求超时时间（秒）

# ============================
# 滴滴 MCP 配置（一键打车基础版）
# ============================
DIDI_MCP_KEY = "didi.mcp.key"  # 滴滴 MCP Key（建议环境变量 DIDI_MCP_KEY 注入）
DIDI_MCP_BASE_URL = "didi.mcp.base-url"  # 正式环境 MCP 地址
DIDI_MCP_SANDBOX_URL = "didi.mcp.sandbox-url"  # 沙箱环境 MCP 地址
DIDI_MCP_SANDBOX = "didi.mcp.sandbox"  # 是否使用沙箱
DIDI_MCP_TIMEOUT = "didi.mcp.timeout"  # 请求超时时间（秒）

# ============================
# langfuse 配置
# ============================
LANGFUSE_ENABLED = "langfuse.enabled"  # 是否启用 Langfuse 追踪
LANGFUSE_PUBLIC_KEY = "langfuse.public-key"  # Langfuse 项目公钥
LANGFUSE_SECRET_KEY = "langfuse.secret-key"  # Langfuse 项目密钥
LANGFUSE_BASE_URL = "langfuse.base-url"  # Langfuse 服务地址
LANGFUSE_ENVIRONMENT = "langfuse.environment"  # 环境标识(development/staging/production)