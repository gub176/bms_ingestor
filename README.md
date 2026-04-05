# BMS Cloud Platform - FastAPI Backend

户储 BMS 云平台核心业务中台 API

## 项目概述

本项目是基于 FastAPI 构建的户储 BMS 云平台核心业务中台，提供设备管理、告警管理、阈值管理、OTA 升级、MQTT 通信等功能。

### 技术栈

- **框架**: FastAPI 0.115.0
- **Python**: 3.11
- **数据库**: Supabase (PostgreSQL)
- **MQTT Broker**: EMQX
- **日志**: Loguru
- **定时任务**: APScheduler

## 功能模块

### 1. 设备管理模块
- 设备列表查询（支持分页、过滤、排序）
- 设备详情查询（聚合实时数据、告警统计）
- 设备绑定
- 设备离线检测（定时任务，每 5 分钟执行）

### 2. 告警管理模块
- 告警列表查询（支持多级筛选）
- 告警关闭（单个/批量）
- 告警统计
- 告警判断服务（基于阈值）
- 告警去重机制

### 3. 阈值管理模块
- 获取阈值配置
- 更新阈值配置
- 创建阈值模板
- 应用模板到设备

### 4. OTA 管理模块
- 创建 OTA 升级任务
- 查询 OTA 升级列表
- 查询 OTA 进度
- MQTT OTA 进度 Webhook
- OTA 失败重试机制（定时任务，每 10 分钟执行）

### 5. MQTT 服务模块
- MQTT 订阅服务（可选，支持直接订阅模式）
- MQTT 数据接收 Webhook
- 设备控制命令
- 查询命令执行状态

## 快速开始

### 环境要求

- Python 3.11+
- Docker & Docker Compose
- Supabase 账号（或使用本地 PostgreSQL）
- EMQX MQTT Broker（Docker 部署）

### 安装依赖

```bash
cd fastapi_backend
pip install -r requirements.txt
```

### 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，填写 Supabase 配置等
```

### 使用 Docker Compose 启动

```bash
docker-compose up --build
```

服务将在 http://localhost:8000 启动

### 本地开发

```bash
# 启动 EMQX (Docker)
docker run -d -p 1883:1883 -p 18083:18083 emqx:5.0

# 启动 FastAPI（本地模式，不启用 MQTT 订阅）
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 或者启用 MQTT 订阅模式（需要在 .env 中设置 ENABLE_MQTT_SUBSCRIPTION=true）
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## API 文档

启动服务后访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API 端点

### 设备管理
- `GET /api/v1/devices` - 获取设备列表
- `GET /api/v1/devices/{device_id}` - 获取设备详情
- `POST /api/v1/devices/bind` - 绑定设备

### 告警管理
- `GET /api/v1/alerts` - 获取告警列表
- `GET /api/v1/alerts/stats` - 获取告警统计
- `PATCH /api/v1/alerts/{alert_id}/close` - 关闭告警
- `PATCH /api/v1/alerts/close-multiple` - 批量关闭告警

### 阈值管理
- `GET /api/v1/thresholds/{device_id}` - 获取阈值配置
- `PATCH /api/v1/thresholds/{device_id}` - 更新阈值配置
- `GET /api/v1/thresholds/templates` - 获取阈值模板
- `POST /api/v1/thresholds/templates` - 创建阈值模板

### OTA 管理
- `POST /api/v1/ota/upgrades` - 创建 OTA 升级任务
- `GET /api/v1/ota/upgrades` - 获取 OTA 升级列表
- `GET /api/v1/ota/upgrades/{upgrade_id}/progress` - 获取 OTA 进度
- `POST /api/v1/ota/upgrades/{upgrade_id}/progress` - 更新 OTA 进度 (Webhook)
- `POST /api/v1/ota/upgrades/{upgrade_id}/retry` - 重试 OTA 升级

### 设备控制
- `POST /api/v1/commands` - 发送设备控制命令
- `GET /api/v1/commands/{command_id}` - 获取命令执行状态
- `GET /api/v1/commands` - 获取命令列表

### MQTT Webhooks
- `POST /api/v1/mqtt/telemetry` - 接收设备遥测数据
- `POST /api/v1/mqtt/ota/progress` - 接收 OTA 进度更新
- `POST /api/v1/ota/upgrades/{upgrade_id}/progress` - 接收 OTA 进度更新 (OTA 模块)

## MQTT 数据摄取

平台支持两种模式接收设备数据：

### 模式 1：EMQX Webhooks（推荐）

配置 EMQX 规则引擎，将 MQTT 消息转发到 `/api/v1/mqtt/telemetry`

### 模式 2：直接订阅（Direct Subscription）

设置 `ENABLE_MQTT_SUBSCRIPTION=true` 直接订阅 MQTT 主题：
- `ess/bms/+/up` - 设备上行数据（遥测/遥信）
- `ess/bms/+/will` - 设备离线事件

### 消息格式

设备应发送 JSON 格式数据：
```json
{
  "devId": "DEVICE_001",
  "timestamp": "2026-04-01T12:00:00Z",
  "msgType": 300,
  "data": {...}
}
```

### 支持的 msgType 值

| msgType | 说明 | 处理 |
|---------|------|------|
| 100 | 登录请求 | 更新设备在线状态 |
| 200 | 心跳请求 | 更新设备在线状态 |
| 300 | 遥测数据 | 解析并存储遥测数据 |
| 310 | 遥信数据 | 解析状态，检测告警 |

### 遥测数组字段

| 前缀 | 字段名 | 单位 |
|------|--------|------|
| 011170xx | cell_voltages | mV |
| 011290xx | cell_socs | 0.1% |
| 011190xx | cell_temperatures | 0.1℃ |

### 告警检测

平台使用位图检测告警：
- **01003001** (预警): 10 个告警位
- **01002001** (故障): 12 个告警位

支持告警去重，避免重复插入。

**注意**：告警判断服务在应用启动时自动从数据库加载活跃告警，并在接收到新遥测数据时自动进行告警判断。

## 监控端点

- `/health` - 健康检查
- `/metrics` - HTML 监控面板（6 秒自动刷新）
- `/metrics/data` - JSON 格式指标
- `/metrics/text` - Prometheus 格式指标

### 指标说明

| 指标 | 说明 |
|------|------|
| messages_received_total | 接收消息总数 |
| messages_processed_total | 处理消息总数 |
| telemetry_received | 遥测消息数 |
| status_received | 遥信消息数 |
| alerts_generated | 生成告警数 |
| queue_size | 当前队列大小 |
| supabase_errors | Supabase 错误数 |
| last_message_time | 上次消息时间 |
| json_errors | JSON 解析错误数 |
| messages_dropped_total | 消息丢弃数（队列满时）|

监控面板支持：
- HTML 仪表盘（6 秒自动刷新）
- JSON 格式数据 (`/metrics/data`)
- Prometheus 格式文本 (`/metrics/text`)
- 最近错误日志显示

## 测试

### 运行单元测试

```bash
pytest --cov=app --cov-report=html
```

### 查看测试覆盖率

```bash
# HTML 报告
open htmlcov/index.html  # macOS
start htmlcov\index.html  # Windows
```

## 项目结构

```
fastapi_backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI 应用入口
│   ├── api/
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── devices.py   # 设备 API
│   │       ├── alerts.py    # 告警 API
│   │       ├── thresholds.py # 阈值 API
│   │       ├── ota.py       # OTA API
│   │       ├── commands.py  # 命令 API
│   │       ├── mqtt.py      # MQTT API
│   │       └── metrics.py   # 监控端点
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py        # 配置管理
│   │   ├── exceptions.py    # 异常处理
│   │   └── logging_config.py # 日志配置
│   ├── db/
│   │   ├── __init__.py
│   │   └── supabase.py      # Supabase 客户端
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py       # 数据模型（MQTT 摄取）
│   ├── schemas/
│   │   ├── device.py        # 设备 Schema
│   │   ├── alert.py         # 告警 Schema
│   │   ├── threshold.py     # 阈值 Schema
│   │   ├── ota.py           # OTA Schema
│   │   └── command.py       # 命令 Schema
│   └── services/
│       ├── device_service.py
│       ├── alert_service.py
│       ├── alert_judgment.py
│       ├── alert_detector.py    # 位图告警检测
│       ├── threshold_service.py
│       ├── ota_service.py
│       ├── ota_recovery.py
│       ├── mqtt_service.py
│       ├── mqtt_subscription_service.py  # MQTT 订阅服务
│       ├── batch_worker.py    # 批处理 Worker
│       ├── command_service.py
│       └── offline_detection.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_device_service.py
│   ├── test_alert_service.py
│   ├── test_ota_service.py
│   └── test_api.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── pytest.ini
└── README.md
```

## 数据库表结构

需要在 Supabase 中创建以下表：

### devices
```sql
CREATE TABLE devices (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    serial_number VARCHAR(255) UNIQUE NOT NULL,
    user_id VARCHAR(255),
    name VARCHAR(255),
    status VARCHAR(50) DEFAULT 'inactive',
    last_seen TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### telemetry
```sql
CREATE TABLE telemetry (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id UUID REFERENCES devices(id),
    voltage DECIMAL,
    current DECIMAL,
    temperature DECIMAL,
    soc INTEGER,
    soe INTEGER,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);
```

### alerts
```sql
CREATE TABLE alerts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id UUID REFERENCES devices(id),
    level VARCHAR(50),
    type VARCHAR(100),
    message TEXT,
    start_time TIMESTAMPTZ DEFAULT NOW(),
    end_time TIMESTAMPTZ
);
```

### alert_thresholds
```sql
CREATE TABLE alert_thresholds (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id UUID UNIQUE REFERENCES devices(id),
    over_voltage DECIMAL,
    under_voltage DECIMAL,
    over_current DECIMAL,
    over_temperature DECIMAL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### ota_upgrades
```sql
CREATE TABLE ota_upgrades (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id UUID REFERENCES devices(id),
    firmware_version VARCHAR(100),
    firmware_url TEXT,
    status VARCHAR(50),
    progress INTEGER DEFAULT 0,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    error_message TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### remote_adjust
```sql
CREATE TABLE remote_adjust (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id UUID REFERENCES devices(id),
    command VARCHAR(100),
    params JSONB,
    status VARCHAR(50) DEFAULT 'pending',
    result JSONB,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### offline_events
```sql
CREATE TABLE offline_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id UUID REFERENCES devices(id),
    offline_at TIMESTAMPTZ DEFAULT NOW(),
    recovered_at TIMESTAMPTZ
);
```

### threshold_templates
```sql
CREATE TABLE threshold_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    over_voltage DECIMAL,
    under_voltage DECIMAL,
    over_current DECIMAL,
    over_temperature DECIMAL,
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

## EMQX 配置

### Webhook 配置

在 EMQX Dashboard 中配置以下 Webhook：

1. **遥测数据上报**: `http://<your-server>/api/v1/mqtt/telemetry`
   - Topic: `ess/bms/+/up`

2. **OTA 进度更新**: `http://<your-server>/api/v1/mqtt/ota/progress`
   - Topic: `devices/+/ota/progress`

### 直接订阅模式

在 `.env` 文件中配置：

```bash
ENABLE_MQTT_SUBSCRIPTION=true
MQTT_TLS_ENABLE=true
EMQX_HOST=k5f33d11.ala.cn-hangzhou.emqxsl.cn
EMQX_PORT=8883
EMQX_USERNAME=<your-username>
EMQX_PASSWORD=<your-password>
```

## 常见问题

### Q: 设备无法连接 MQTT？
A: 检查 EMQX 服务是否运行，确认用户名密码正确。

### Q: OTA 升级失败？
A: 检查设备网络连接，确认固件 URL 可访问。

### Q: 告警未触发？
A: 检查阈值配置是否正确，确认遥测数据格式。

## 许可证

MIT License

## 联系方式

- 项目维护者：小码
- 邮箱：support@example.com
