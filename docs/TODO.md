# Travel Copilot — 待优化事项

## 已知问题

### 1. 地理编码准确性不足
- 小型本地餐厅（如 Dining CHORO、cafe&bar anthem）在 Azure Maps 中无法精确定位，返回错误地点
- 中文地名对应日本地点时，部分仍无法识别（如"百年麻婆"、"须磨海洋世界"）
- **建议**：允许用户在地图上手动点击修正地点坐标；或增加二次搜索逻辑（先用 name_local 搜，失败再用 name + 地区搜）

### 2. AI Plan 偶尔遗漏地点
- 已增加兜底机制（未分配的地点自动加到最少的天），但 AI 有时不严格遵循"分配所有地点"的指令
- **建议**：可在前端显示提示"X 个地点被自动分配，请检查"

### 3. 内存数据库重启丢失
- 当前本地模式使用内存存储，后端重启后所有数据清空
- **建议**：可用 SQLite 或 JSON 文件替代内存存储实现持久化

## 前端待优化

### 4. 地图交互体验
- 地图上点击 marker 显示详情/备注（已有基础实现，待验证实际体验）
- 支持在地图上点击修正地点坐标
- 地图的 marker 聚合（地点过密时）

### 5. 拖拽体验
- 跨天拖拽后需重新排序 order_in_day（当前只更新被拖拽的地点，不调整同天其他地点顺序）
- 拖拽时的视觉反馈（当前较基础）

### 6. 错误处理 & 加载状态
- AI 提取/规划可能耗时较长（10-30 秒），需要更好的 loading 提示
- 网络错误、API 限流等场景的用户提示

### 7. 地点编辑
- 在 Planner 页面支持编辑地点名称、类型、备注
- 支持删除地点

## 后端待优化

### 8. AI 模型
- 当前使用 `gpt-4o`（GitHub Models 不支持 `claude-sonnet-4.6`）
- 如需切换模型，修改 `.env` 中的 `AI_MODEL`

### 9. 地理编码并发
- 当前逐个 geocode，地点多时较慢
- **建议**：改为并发请求（`asyncio.gather`）

### 10. 图片提取结果中的 name_local
- AI 提取的 `name_local` 字段目前仅用于 geocoding，未存入 Place 数据模型
- **建议**：扩展 Place 模型增加 `name_local` 字段，前端可展示双语名称

## 部署相关

### 11. Azure 服务配置
- Cosmos DB：需创建账号并配置 `COSMOS_ENDPOINT` 和 `COSMOS_KEY`
- Blob Storage：需创建存储账号并配置 `BLOB_CONNECTION_STRING`
- Azure Maps：已配置（当前 key 同时用于前后端）
- Google OAuth：需在 Google Cloud Console 配置 OAuth 2.0 凭据

### 12. 生产环境安全
- `JWT_SECRET` 需替换为强随机字符串
- 关闭 `USE_LOCAL_DB`
- 移除 `/api/auth/dev-login` 端点（或确保生产环境不可用）
- CORS origins 需配置为实际域名
