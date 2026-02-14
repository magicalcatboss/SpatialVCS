# SpatialVCS Backend Capabilities (Web-First Edition)

目前后端已完成核心逻辑开发，版本为 **v2.1.0**。支持 WebSocket 实时流 (推荐) 和 REST API (备用)。

---

## 🏗️ 核心模块能力

### 1. 📷 视频流处理 (`video_processor.py`)
- **接收 Probe 数据包**：处理 `Image (Base64/JPEG)` + `Pose (Gyroscope)`。
- **物体检测**：集成 `YOLOv8n`，自动识别画面中的 80 类常见物体。
- **3D 坐标计算**：结合陀螺仪位姿 + 估算深度，计算物体在房间坐标系中的 (x, y, z)。

### 2. 🧠 空间记忆 (`spatial_memory.py`)
- **语义向量化**：使用 `sentence-transformers` 生成语义向量。
- **FAISS 索引**：高性能向量库，支持毫秒级相似度搜索。
- **元数据存储**：存储物体标签、3D 坐标、时间戳和帧路径。

### 3. 🤖 Gemini 智能 (`llm.py`)
- **看图说话**：对检测到的物体进行详细描述。
- **自然语言问答**：将搜索结果包装成自然语言回答。
- **差异检测**：(通过 REST Diff 接口) 对比两次扫描的变化。

---

## 🔌 API 接口清单 (对接用)

### A. 实时通信 (WebSocket) - **推荐**

| 端点 | 客户端 | 方向 | 数据包示例 |
|------|-------|------|------------|
| `/ws/probe/{id}` | **手机 Web** | 发送 | `{"type": "frame", "image": "base64...", "pose": {alpha: 0, beta: 0}}` |
| `/ws/dashboard/{id}` | **电脑 Web** | 接收 | `{"type": "update", "objects": [{"label": "cup", "position": {...}}]}` |

### B. 采集/查询 (REST API) - **备用/低频**

| 方法 | 端点 | 参数 | 作用 |
|------|------|------|------|
| `POST` | `/spatial/scan/frame` | `image`, `pose`, `scan_id` | **备用采集**. 接收单帧数据 (不支持实时流体验)。 |
| `POST` | `/spatial/query` | `query`, `scan_id` | **搜索接口**. 返回最匹配的物体列表 + 自然语言回答。 |
| `POST` | `/spatial/diff` | `scan_id_before`, `scan_id_after` | **Diff 接口**. 对比变化。 |

### C. 资源获取

| 方法 | 端点 | 作用 |
|------|------|------|
| `GET` | `/spatial/frame/{scan_id}/{file}` | 获取原始帧图片。 |
| `GET` | `/spatial/scans` | 列出所有扫描记录。 |

---

## 🚀 快速开始

**1. 启动后端 (Mac)**
```bash
cd /Users/shengyuanhe/Savage/gemini_toolkit
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**2. 手机端连接**
- 确保手机和电脑在同一 WiFi。
- 前端通过 `ws://YOUR_MAC_IP:8000/ws/probe/iphone` 连接。

**3. 电脑端连接**
- 前端通过 `ws://localhost:8000/ws/dashboard/screen` 连接。
