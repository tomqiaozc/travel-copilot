# Travel Copilot — 待优化事项

## 已知问题

### ~~1. 地理编码准确性不足~~ ✅ 已完成
- ~~小型本地餐厅（如 Dining CHORO、cafe&bar anthem）在 Azure Maps 中无法精确定位，返回错误地点~~
- ~~中文地名对应日本地点时，部分仍无法识别（如"百年麻婆"、"须磨海洋世界"）~~
- 已实现：多策略并行 geocoding（name_local > name_en > 中文名）、集群验证 + 离群点重试、用户可通过粘贴 Google Maps 链接修正地点

### ~~2. AI Plan 偶尔遗漏地点~~ ✅ 已完成
- ~~已增加兜底机制（未分配的地点自动加到最少的天），但 AI 有时不严格遵循"分配所有地点"的指令~~
- 已实现：后端自动将未分配地点补入最少的天，prompt 强制要求分配所有地点

### 3. 内存数据库重启丢失
- 当前本地模式使用内存存储，后端重启后所有数据清空
- **建议**：可用 SQLite 或 JSON 文件替代内存存储实现持久化

## 前端待优化

### 4. 地图交互体验（部分完成）
- ~~地图上点击 marker 显示详情/备注~~ ✅ 已实现 InfoWindow（名称、类型、天数、备注、Google Maps 链接）
- 支持在地图上点击修正地点坐标
- ~~地图的 marker 聚合（地点过密时）~~ ✅ 已实现 @googlemaps/markerclusterer 自动聚合

### 5. 拖拽体验
- 跨天拖拽后需重新排序 order_in_day（当前只更新被拖拽的地点，不调整同天其他地点顺序）
- 拖拽时的视觉反馈（当前较基础）

### 6. 错误处理 & 加载状态（部分完成）
- ~~AI 提取/规划可能耗时较长（10-30 秒），需要更好的 loading 提示~~ ✅ 已有基础 loading 文字提示
- ~~网络错误、API 限流等场景的用户提示~~ ✅ 已实现 sonner 全局 toast 通知，所有 store action 错误自动弹出提示
- 可进一步优化：进度条、骨架屏、预估时间等

### ~~7. 地点编辑~~ ✅ 已完成
- ~~在 TripDetail 页面支持编辑地点名称、类型、备注、Google Maps 链接~~ ✅ 已完成
- ~~支持删除地点~~ ✅ 已完成
- ~~在 Planner 页面支持编辑和删除地点~~ ✅ 已完成（内联编辑表单 + Google Maps 链接验证）

## 后端待优化

### ~~8. AI 模型~~ ✅ 已完成
- ~~统一使用 `gpt-4o`（GitHub Models API）~~
- ~~如需切换模型，修改 `.env` 中的 `AI_MODEL`~~
- 已实现：通过 `AI_MODEL` 环境变量统一配置，所有 AI 调用走同一设置

### ~~9. 地理编码并发~~ ✅ 已完成
- ~~当前逐个 geocode，地点多时较慢~~
- 已实现：`asyncio.gather` 并发执行多策略搜索和批量 geocoding

### ~~10. 图片提取结果中的 name_local~~ ✅ 已完成
- ~~AI 提取的 `name_local` 字段目前仅用于 geocoding，未存入 Place 数据模型~~
- 已实现：Place 模型已包含 `name_local` 字段，前端 ExtractionModal 展示双语名称

## 下期改进计划

### 13. 酒店跨天复用
- 多天住同一家酒店时，酒店应自动出现在对应的多天行程中，而非只属于某一天
- 需要对 hotel 类型做特殊处理：支持关联多个 day_number，或标记入住/退房日期

### 14. 地点信息扩展（营业时间等）
- 利用 Google Places API 获取更丰富的地点信息：营业时间、评分、电话、照片等
- 营业时间需注意每天可能不同（周一~周日分别展示）
- 可在地点卡片和 Planner 中展示，帮助用户合理安排时间

### 15. 地点标签系统
- 为地点增加自定义标签（如"必去"、"备选"、"美食"、"拍照打卡"等）
- 基于标签做筛选、分组、优先级排序
- AI 规划时可参考标签权重（如优先安排"必去"标签的地点）

### 16. 从 Google Maps 收藏导入
- 支持导入用户在 Google Maps 中收藏（Saved/Starred）的地点
- 导入后根据地点间的相对距离，自动进行日程规划分配
- 可通过 Google Takeout 导出的 GeoJSON/CSV，或 Google Maps API 读取收藏列表

### 17. 将 Google Maps 收藏智能插入现有行程
- 用户已有行程后，导入 Google Maps 收藏的地点
- 根据收藏地点与现有行程中景点的距离，智能地插入到最合适的天和位置
- 例如：收藏了一家餐厅距离 Day 2 的景点最近，就自动推荐插入 Day 2

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
