# BMS 云平台 - 操作手册

户储 BMS 云平台核心业务中台 API 使用指南

---

## 目录

1. [项目简介](#1-项目简介)
2. [快速开始](#2-快速开始)
3. [配置说明](#3-配置说明)
4. [功能模块详解](#4-功能模块详解)
5. [API 使用指南](#5-api-使用指南)
6. [MQTT 数据接入](#6-mqtt-数据接入)
7. [监控与运维](#7-监控与运维)
8. [常见问题](#8-常见问题)

---

## 1. 项目简介

### 1.1 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                    BMS Cloud Platform                        │
│                     FastAPI Backend                          │
├─────────────────────────────────────────────────────────────┤
│  API Layer (REST)         │  MQTT Ingestion Layer          │
│  - 设备管理               │  - Webhook 模式                 │
│  - 告警管理               │  - 直接订阅模式                 │
│  - 阈值管理               │  - 批处理 Worker                │
│  - OTA 管理                │  - 位图告警检测                 │
│  - 设备控制               │                                 │
├─────────────────────────────────────────────────────────────┤
│                    Data Layer (Supabase)                    │
│  - devices | telemetry | alerts | thresholds | ota          │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 技术栈

| 组件 | 技术 | 说明 |
|------|------|------|
| Web 框架 | FastAPI 0.115.0 | 高性能异步 API |
| 语言 | Python 3.11 | 类型安全 |
| 数据库 | Supabase (PostgreSQL) | 云原生数据库 |
| MQTT Broker | EMQX | 消息队列 |
| 日志 | Loguru | 结构化日志 |
| 定时任务 | APScheduler | 后台调度 |

### 1.3 核心功能

- **设备管理**：设备列表、详情、绑定、离线检测
- **告警管理**：告警列表、统计、关闭、位图去重
- **阈值管理**：阈值配置、模板管理
- **OTA 升级**：升级任务、进度跟踪、失败重试
- **设备控制**：远程命令、状态查询
- **MQTT 接入**：Webhook / 直接订阅两种模式
- **监控告警**：实时指标、错误日志、HTML 仪表盘

---

## 2. 快速开始

### 2.1 环境要求

- Python 3.11+
- Docker & Docker Compose（可选，用于 EMQX）
- Supabase 账号

### 2.2 安装依赖

```bash
cd fastapi_backend
pip install -r requirements.txt
```

### 2.3 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 文件，填写必要配置：

```bash
# Supabase 数据库
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-key

# EMQX MQTT Broker
EMQX_HOST=k5f33d11.ala.cn-hangzhou.emqxsl.cn
EMQX_PORT=8883
EMQX_USERNAME=your-username
EMQX_PASSWORD=your-password

# JWT 配置
JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256

# 批处理配置
BATCH_SIZE=50
BATCH_TIMEOUT=6

# MQTT 订阅模式（可选）
ENABLE_MQTT_SUBSCRIPTION=false
MQTT_TLS_ENABLE=true
```

### 2.4 启动服务

#### 方式 1：直接启动（推荐开发环境）

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### 方式 2：Docker Compose（推荐生产环境）

```bash
docker-compose up --build
```

#### 方式 3：启用 MQTT 订阅模式

在 `.env` 中设置 `ENABLE_MQTT_SUBSCRIPTION=true`，然后启动：

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2.5 验证启动

访问以下地址：

- **API 文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/health
- **监控面板**: http://localhost:8000/metrics

---

## 3. 配置说明

### 3.1 完整配置项

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `SUPABASE_URL` | - | Supabase 项目 URL |
| `SUPABASE_SERVICE_KEY` | - | Supabase 服务密钥 |
| `EMQX_HOST` | localhost | EMQX Broker 地址 |
| `EMQX_PORT` | 1883 | EMQX 端口（TLS 推荐 8883） |
| `EMQX_USERNAME` | admin | MQTT 用户名 |
| `EMQX_PASSWORD` | public | MQTT 密码 |
| `JWT_SECRET_KEY` | - | JWT 签名密钥 |
| `JWT_ALGORITHM` | HS256 | JWT 算法 |
| `BATCH_SIZE` | 50 | 批处理大小 |
| `BATCH_TIMEOUT` | 6 | 批处理超时（秒） |
| `ENABLE_MQTT_SUBSCRIPTION` | false | 启用直接订阅模式 |
| `MQTT_TLS_ENABLE` | true | 启用 TLS 加密 |

### 3.2 部署配置

#### Railway 部署

项目包含 `railway.toml` 配置文件，可直接部署到 Railway：

1. 推送代码到 GitHub
2. Railway Dashboard → New Project → Deploy from GitHub
3. 添加环境变量（见 3.1）
4. 自动部署完成

访问地址：
- API: `https://your-app.railway.app/health`
- Metrics: `https://your-app.railway.app/metrics`

---

## 4. 功能模块详解

### 4.1 设备管理模块

#### 功能列表

- 设备列表查询（分页、过滤、排序）
- 设备详情查询（聚合实时数据、告警统计）
- 设备绑定
- 设备离线检测（定时任务，每 5 分钟执行）

#### 使用示例

```python
# 获取设备列表
GET /api/v1/devices?page=1&page_size=20&user_id=user123&status=online

# 获取设备详情
GET /api/v1/devices/{device_id}

# 绑定设备
POST /api/v1/devices/bind
{
    "serial_number": "BMS123456",
    "user_id": "user123"
}
```

### 4.2 告警管理模块

#### 功能列表

- 告警列表查询（多级筛选）
- 告警关闭（单个/批量）
- 告警统计
- 告警判断服务（基于阈值）
- **位图告警去重机制**

#### 告警去重原理

系统使用位图（bitmap）跟踪告警状态：

| 信号 ID | 类型 | 位数 | 说明 |
|--------|------|------|------|
| 01003001 | 预警 | 10 位 | 一般告警 |
| 01002001 | 故障 | 12 位 | 严重告警 |

**去重逻辑**：
1. 应用启动时从数据库加载活跃告警
2. 接收新状态数据时，比较位图变化
3. 仅当告警位从 0→1 时创建新告警
4. 已存在的告警不会重复插入
5. 告警位从 1→0 时，自动关闭告警

#### 使用示例

```python
# 获取告警列表
GET /api/v1/alerts?device_id=xxx&severity=1&page=1

# 获取告警统计
GET /api/v1/alerts/stats?device_id=xxx

# 关闭单个告警
PATCH /api/v1/alerts/{alert_id}/close

# 批量关闭告警
PATCH /api/v1/alerts/close-multiple
{
    "alert_ids": [1, 2, 3],
    "device_id": "xxx"
}
```

### 4.3 阈值管理模块

#### 功能列表

- 获取/更新设备阈值配置
- 创建阈值模板
- 应用模板到设备

#### 使用示例

```python
# 获取设备阈值
GET /api/v1/thresholds/{device_id}

# 更新阈值
PATCH /api/v1/thresholds/{device_id}
{
    "over_voltage": 54.0,
    "under_voltage": 42.0,
    "over_current": 100.0,
    "over_temperature": 60.0
}

# 创建模板
POST /api/v1/thresholds/templates
{
    "name": "标准模板",
    "over_voltage": 54.0,
    "under_voltage": 42.0
}

# 应用模板到设备
POST /api/v1/thresholds/templates/{template_id}/apply/{device_id}
```

### 4.4 OTA 管理模块

#### 功能列表

- 创建 OTA 升级任务
- 查询升级列表/进度
- MQTT OTA 进度 Webhook
- **OTA 失败重试机制**（定时任务，每 10 分钟执行）

#### 升级流程

```
1. 创建升级任务 → status=pending
2. 发送 MQTT 命令到设备 → status=downloading
3. 设备下载固件 → 进度更新
4. 设备刷写固件 → status=flashing
5. 升级完成 → status=completed
6. 失败自动重试（最多 3 次）
```

#### 使用示例

```python
# 创建升级任务
POST /api/v1/ota/upgrades
{
    "device_id": "xxx",
    "firmware_version": "v2.1.0",
    "firmware_url": "https://..."
}

# 查询升级列表
GET /api/v1/ota/upgrades?device_id=xxx&status=pending

# 查询进度
GET /api/v1/ota/upgrades/{upgrade_id}/progress

# 重试失败升级
POST /api/v1/ota/upgrades/{upgrade_id}/retry
```

### 4.5 设备控制模块

#### 功能列表

- 发送远程命令
- 查询命令执行状态
- 命令历史记录

#### 使用示例

```python
# 发送命令
POST /api/v1/commands
{
    "device_id": "xxx",
    "command": "reboot",
    "params": {"delay": 5}
}

# 查询命令状态
GET /api/v1/commands/{command_id}

# 获取命令列表
GET /api/v1/commands?device_id=xxx&status=pending
```

### 4.6 批处理 Worker

#### 工作原理

```
MQTT 消息 → 异步队列 → 批处理 Worker → 批量写入 Supabase
           (最大 10000)   (每 6 秒或满 50 条)
```

#### 批处理条件

满足任一条件即触发写入：
- 队列消息达到 50 条
- 距离上次写入超过 6 秒

#### 优势

- 减少数据库连接开销
- 提高写入吞吐量
- 降低 Supabase 调用次数

### 4.7 离线检测服务

#### 工作机制

- **定时检测**：每 5 分钟扫描一次
- **Will 消息**：设备断开时立即触发
- **自动恢复**：设备重连后自动更新状态

---

## 5. API 使用指南

### 5.1 完整端点列表

| 模块 | 端点 | 方法 | 说明 |
|------|------|------|------|
| 设备 | `/api/v1/devices` | GET | 设备列表 |
| 设备 | `/api/v1/devices/{id}` | GET | 设备详情 |
| 设备 | `/api/v1/devices/bind` | POST | 绑定设备 |
| 告警 | `/api/v1/alerts` | GET | 告警列表 |
| 告警 | `/api/v1/alerts/stats` | GET | 告警统计 |
| 告警 | `/api/v1/alerts/{id}/close` | PATCH | 关闭告警 |
| 告警 | `/api/v1/alerts/close-multiple` | PATCH | 批量关闭 |
| 阈值 | `/api/v1/thresholds/{id}` | GET/PUT | 阈值配置 |
| 阈值 | `/api/v1/thresholds/templates` | GET/POST | 模板管理 |
| OTA | `/api/v1/ota/upgrades` | GET/POST | 升级任务 |
| OTA | `/api/v1/ota/upgrades/{id}/progress` | GET/POST | 进度更新 |
| 命令 | `/api/v1/commands` | GET/POST | 设备控制 |
| MQTT | `/api/v1/mqtt/telemetry` | POST | 遥测 Webhook |
| MQTT | `/api/v1/mqtt/ota/progress` | POST | OTA Webhook |
| 监控 | `/health` | GET | 健康检查 |
| 监控 | `/metrics` | GET | 监控面板 |

### 5.2 认证说明

当前版本所有端点无需认证。生产环境建议：

1. 配置 JWT 认证
2. 使用 API Key 保护 Webhook
3. 启用 CORS 限制

### 5.3 错误响应格式

```json
{
    "error": {
        "code": "DEVICE_NOT_FOUND",
        "message": "设备不存在",
        "details": {}
    }
}
```

---

## 6. MQTT 数据接入

### 6.1 两种接入模式

#### 模式 1：EMQX Webhooks（推荐）

**架构**：
```
设备 → EMQX → Webhook → /api/v1/mqtt/telemetry → FastAPI
```

**配置步骤**：

1. 登录 EMQX Dashboard
2. 创建 Webhook 规则
3. 配置 Topic：`ess/bms/+/up`
4. 配置 URL：`http://your-server/api/v1/mqtt/telemetry`

**优点**：
- 配置简单
- 无需维护 MQTT 连接
- 适合云部署

#### 模式 2：直接订阅

**架构**：
```
设备 → EMQX → FastAPI 订阅 → 批处理 → Supabase
```

**配置步骤**：

1. 在 `.env` 中设置：
```bash
ENABLE_MQTT_SUBSCRIPTION=true
MQTT_TLS_ENABLE=true
EMQX_HOST=your-emqx-host
EMQX_PORT=8883
EMQX_USERNAME=your-username
EMQX_PASSWORD=your-password
```

2. 启动服务（自动连接 MQTT Broker）

**订阅的 Topic**：
- `ess/bms/+/up` - 设备上行数据
- `ess/bms/+/will` - 设备离线事件

**优点**：
- 低延迟
- 直接控制
- 适合本地部署

### 6.2 消息格式

#### 通用格式

```json
{
    "devId": "DEVICE_001",
    "timestamp": "2026-04-01T12:00:00Z",
    "msgType": 300,
    "data": {...}
}
```

#### msgType 说明

| msgType | 说明 | 处理逻辑 |
|---------|------|----------|
| 100 | 登录请求 | 更新设备在线状态 |
| 200 | 心跳请求 | 更新设备在线状态 |
| 300 | 遥测数据 | 解析并存储遥测数据 |
| 310 | 遥信数据 | 解析状态，检测告警 |

#### 遥测数组字段

| 前缀 | 字段名 | 单位 | 说明 |
|------|--------|------|------|
| 011170xx | cell_voltages | mV | 电芯电压 |
| 011290xx | cell_socs | 0.1% | 电芯 SOC |
| 011190xx | cell_temperatures | 0.1℃ | 电芯温度 |

**示例**：
```json
{
    "devId": "BMS001",
    "timestamp": "2026-04-01T12:00:00Z",
    "msgType": 300,
    "data": {
        "01117001": 3500,
        "01117002": 3510,
        "01117003": 3490,
        "voltage": 48.5,
        "current": 10.2,
        "soc": 85
    }
}
```

#### 遥信告警位图

```json
{
    "devId": "BMS001",
    "timestamp": "2026-04-01T12:00:00Z",
    "msgType": 310,
    "data": {
        "01003001": 2,
        "01002001": 4
    }
}
```

**告警位说明**：

| 信号 ID | 位 0 | 位 1 | 位 2 | ... |
|--------|------|------|------|-----|
| 01003001 (预警) | 电压低 | 电压高 | 温度低 | ... |
| 01002001 (故障) | 短路 | 欠压 | 过压 | ... |

---

## 7. 监控与运维

### 7.1 监控端点

| 端点 | 格式 | 说明 |
|------|------|------|
| `/health` | JSON | 健康检查 |
| `/metrics` | HTML | 监控仪表盘（6 秒刷新） |
| `/metrics/data` | JSON | 指标数据 |
| `/metrics/text` | Text | Prometheus 格式 |

### 7.2 核心指标

| 指标 | 说明 | 告警阈值 |
|------|------|----------|
| `messages_received_total` | 接收消息总数 | - |
| `messages_processed_total` | 处理消息总数 | - |
| `telemetry_received` | 遥测消息数 | - |
| `status_received` | 遥信消息数 | - |
| `alerts_generated` | 生成告警数 | - |
| `queue_size` | 当前队列大小 | > 5000 |
| `supabase_errors` | Supabase 错误数 | > 0 |
| `json_errors` | JSON 解析错误数 | > 0 |
| `messages_dropped_total` | 消息丢弃数 | > 0 |
| `last_message_time` | 上次消息时间 | > 60s |

### 7.3 日志配置

```bash
# 日志级别
LOG_LEVEL=INFO

# 日志文件路径
LOG_FILE=/var/log/fastapi/app.log
```

**日志级别说明**：
- `DEBUG`：调试信息
- `INFO`：运行信息（推荐）
- `WARNING`：警告信息
- `ERROR`：错误信息

### 7.4 后台定时任务

| 任务 | 频率 | 说明 |
|------|------|------|
| 离线检测 | 每 5 分钟 | 检测设备在线状态 |
| OTA 失败恢复 | 每 10 分钟 | 重试失败的 OTA 升级 |

---

## 8. 常见问题

### Q1: 设备无法连接 MQTT？

**排查步骤**：
1. 检查 EMQX 服务状态：`docker ps | grep emqx`
2. 验证用户名密码是否正确
3. 检查防火墙规则，确保端口开放
4. 查看 EMQX 日志：`docker logs emqx-container`

### Q2: OTA 升级失败？

**排查步骤**：
1. 检查设备网络连接
2. 验证固件 URL 可访问性
3. 查看 OTA 升级日志
4. 使用重试接口：`POST /api/v1/ota/upgrades/{id}/retry`

### Q3: 告警未触发？

**排查步骤**：
1. 检查阈值配置：`GET /api/v1/thresholds/{device_id}`
2. 验证遥测数据格式是否正确
3. 检查告警去重状态
4. 查看日志中的告警检测记录

### Q4: 数据库连接失败？

**排查步骤**：
1. 验证 Supabase URL 和密钥
2. 检查网络连接
3. 查看 Supabase Dashboard 确认表结构
4. 检查是否达到数据库连接数限制

### Q5: 队列消息堆积？

**排查步骤**：
1. 查看监控面板队列大小
2. 检查批处理 Worker 日志
3. 增加 `BATCH_SIZE` 或减少 `BATCH_TIMEOUT`
4. 检查 Supabase 写入性能

### Q6: 监控面板无法访问？

**排查步骤**：
1. 确认服务已启动
2. 检查端口 8000 是否开放
3. 验证 `/metrics` 端点响应
4. 查看浏览器控制台错误

---

## 附录 A：数据库表结构

详细表结构请参考 README.md 中的数据库表结构章节。

## 附录 B：项目结构

```
fastapi_backend/
├── app/
│   ├── main.py                 # 应用入口
│   ├── api/v1/                 # API 端点
│   ├── core/                   # 核心配置
│   ├── db/                     # 数据库客户端
│   ├── models/                 # 数据模型
│   ├── schemas/                # Pydantic 模型
│   └── services/               # 业务服务
├── tests/                      # 测试文件
├── requirements.txt            # 依赖列表
├── docker-compose.yml          # Docker 配置
└── README.md                   # 项目说明
```

## 附录 C：版本历史

| 版本 | 日期 | 变更说明 |
|------|------|----------|
| 1.0.0 | 2026-04-01 | 初始版本，集成 MQTT  ingestion |

---

**联系方式**：
- 项目维护者：小码
- 邮箱：support@example.com
