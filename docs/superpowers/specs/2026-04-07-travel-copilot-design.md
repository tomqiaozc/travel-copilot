# Travel Copilot — 产品设计文档

## 概述

Travel Copilot 是一款旅行规划 Web App，帮助用户将小红书等平台收藏的攻略截图，通过 AI 自动提取结构化地点信息，并按地理距离智能规划每日行程，最终在地图上可视化展示并导出到 Google Maps。

### 目标用户

个人使用，通过 Google 账号登录。用户已有 Google Cloud 和 GitHub Copilot 订阅。

### 核心价值

截图攻略 → 结构化数据 → 智能排程 → 地图可视化 → 导出 Google Maps，一站式完成旅行规划。

---

## 技术架构

### 技术栈

| 层级 | 技术选型 | 部署 |
|------|---------|------|
| 前端 | React SPA | Azure Static Web Apps |
| 后端 | Python FastAPI | Azure App Service |
| AI | GitHub Models (claude-sonnet-4.6) | 外部 API |
| 地图 | Azure Maps SDK (前端) + Azure Maps REST API (后端地理编码/距离) | Azure |
| 存储 | Azure Blob Storage (截图) | Azure |
| 数据库 | Azure Cosmos DB (用户 + 行程数据) | Azure |
| 认证 | Google OAuth 2.0 → JWT | — |

### 架构决策

- **AI 选型 GitHub Models (claude-sonnet-4.6) 而非 Azure OpenAI**：复用用户现有的 GitHub Copilot 订阅，避免额外 AI 服务费用。统一使用 claude-sonnet-4.6 处理 Vision（截图提取）和文本推理（行程排程），简化后端代码。
- **claude-sonnet-4.6 Vision 一步完成 OCR + 结构化提取**：无需单独的 OCR 服务，截图直接发送给 claude-sonnet-4.6 的多模态能力，一步返回结构化 POI 数据。
- **Azure Maps 而非 Google Maps**：保持 Azure 技术栈统一。应用内展示用 Azure Maps，最终导出生成 Google Maps URL 链接（不需要 Google Maps API）。

### 数据流

1. **上传阶段**：用户批量上传截图 → Blob Storage 存储 → claude-sonnet-4.6 Vision 一步提取结构化 POI
2. **补充阶段**：用户手动添加地点 + 备注 → 合并到 POI 列表
3. **规划阶段**：POI 列表 → Azure Maps 地理编码获取坐标 → claude-sonnet-4.6 按距离聚类排程（支持用户自然语言指令引导） → 生成每日行程
4. **展示阶段**：前端 Azure Maps 渲染地图 → 按天着色标注 → 用户拖拽调整 → 一键导出 Google Maps URL

---

## 前端页面设计

### 页面 1：首页 / 行程列表

- 顶部导航栏：应用名称 + 用户头像/登出
- 行程卡片列表：显示名称、日期范围、地点数量、状态（已规划/待规划）
- 新建行程按钮：输入名称和日期范围

### 页面 2：上传 & 添加地点

- **截图上传区域**：拖拽或点击上传，支持 JPG/PNG，最多 10 张，上传后显示缩略图
- **AI 提取按钮**：点击后调用后端，返回提取的 POI 列表供用户勾选确认
- **手动添加表单**：地点名称、类型（景点/餐厅/酒店/其他）、备注文本框

### 页面 3：行程规划（核心页面）

- **左侧面板**：按天分组的地点列表
  - 每天用不同颜色标识（与地图标注颜色一致）
  - 地点卡片显示名称、类型、备注、与上一站距离
  - 支持拖拽排序：在天内调整顺序，跨天移动地点
  - 底部"未分配"区域：尚未安排到某天的地点
- **右侧面板**：Azure Maps 地图
  - 按天用不同颜色标注地点
  - 同一天的地点用线连接显示路线
  - 点击标注可查看详情/备注
  - 底部图例：每天的颜色对应
- **顶部操作栏**：
  - 「AI 重新规划」按钮：点击弹出输入框，用户可输入自然语言指令（如"第一天轻松一点"、"把拉面店安排在中午"），AI 结合现有地点 + 用户指令重新排程
  - 「导出 Google Maps」按钮：按天生成 Google Maps 路线链接

### 页面 4：AI 提取结果（弹窗/抽屉）

- 显示 AI 从截图中识别出的地点列表
- 每个地点显示：名称、类型（AI 推断）、来源截图缩略图
- 用户可勾选/取消、修改名称和类型、添加备注
- 确认后批量加入行程

---

## 后端 API 设计

### 认证

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/google` | Google OAuth 回调，返回 JWT token |
| GET | `/api/auth/me` | 获取当前用户信息 |

### 行程管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/trips` | 获取用户的所有行程 |
| POST | `/api/trips` | 创建新行程（名称、日期范围） |
| GET | `/api/trips/{id}` | 获取行程详情（含地点和每日安排） |
| PUT | `/api/trips/{id}` | 更新行程信息 |
| DELETE | `/api/trips/{id}` | 删除行程 |

### 地点管理

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/trips/{id}/places` | 手动添加地点（名称、类型、备注） |
| PUT | `/api/trips/{id}/places/{placeId}` | 更新地点信息/备注 |
| DELETE | `/api/trips/{id}/places/{placeId}` | 删除地点 |

### AI 服务

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/trips/{id}/extract` | 上传截图 → claude-sonnet-4.6 Vision 提取 POI 列表（待用户确认） |
| POST | `/api/trips/{id}/plan` | AI 智能排程，接受可选 `user_prompt` 字段引导规划方向 |

**`/api/trips/{id}/extract` 详情：**
- 请求：`multipart/form-data`，字段 `images[]`（最多 10 张）
- 响应：提取出的 POI 列表，每个包含 `name`、`type`、`source_image_index`
- 用户在前端确认后，通过 `/api/trips/{id}/places` 批量写入

**`/api/trips/{id}/plan` 详情：**
- 请求：`{ "user_prompt": "第一天轻松一点" }`（`user_prompt` 可选）
- 流程：获取行程所有地点 → Azure Maps 地理编码 → 计算距离矩阵 → claude-sonnet-4.6 结合距离数据 + 用户指令生成每日排程
- 响应：按天分组的地点列表，含顺序和预估距离

### 导出

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/trips/{id}/export/google-maps` | 按天生成 Google Maps URL（每天一条路线链接） |

---

## 数据模型

### User（用户）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | string | 主键 |
| google_id | string | Google OAuth 用户 ID |
| email | string | 邮箱 |
| name | string | 显示名称 |
| avatar_url | string | 头像 URL |
| created_at | datetime | 注册时间 |

### Trip（行程）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | string | 主键 |
| user_id | string | 所属用户 |
| name | string | 行程名称（如"东京 5 日游"） |
| start_date | date | 开始日期 |
| end_date | date | 结束日期 |
| created_at | datetime | 创建时间 |

### Place（地点）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | string | 主键 |
| trip_id | string | 所属行程 |
| name | string | 地点名称 |
| type | enum | 景点 / 餐厅 / 酒店 / 其他 |
| note | string | 用户备注（可选） |
| latitude | float | 纬度（地理编码后填入） |
| longitude | float | 经度（地理编码后填入） |
| source | enum | ai_extracted / manual |
| day_number | int | 分配到第几天（null = 未分配） |
| order_in_day | int | 当天内的顺序 |

### Image（截图）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | string | 主键 |
| trip_id | string | 所属行程 |
| blob_url | string | Azure Blob Storage URL |
| uploaded_at | datetime | 上传时间 |

---

## 范围外（不在 MVP 中）

- 多用户协作 / 行程分享
- 实时导航
- 酒店/机票预订集成
- 费用预算追踪
- 移动端原生应用（仅 Web）
- 多语言支持
