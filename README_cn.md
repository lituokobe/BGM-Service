# 音频大模型服务 - 背景音乐智能描述

> 🌐 [English](README.md) | 简体中文
>
> 基于 [Qwen-Audio-Chat](https://huggingface.co/Qwen/Qwen-Audio-Chat) 的本地化部署方案，为 AI 短视频项目提供高精度的背景音乐理解能力。
> 输入一段背景音乐，输出 200–250 字的纯中文描述，涵盖总体风格、音乐类型、核心乐器与适配场景。

## 📋 目录

- [功能特性](#-功能特性)
- [项目结构](#-项目结构)
- [环境要求](#-环境要求)
- [快速开始](#-快速开始)
- [本地开发（非 Docker）](#-本地开发非-docker)
- [配置说明](#-配置说明)
- [API 接口文档](#-api-接口文档)

---

## ✨ 功能特性

- 🎵 **背景音乐智能描述**：自动解析背景音乐的风格、乐器、氛围感，并输出适用于短视频制作的中文描述
- 🐳 **Docker 容器化**：一键部署，支持 GPU 直通，便于跨环境迁移
- ⚡ **vLLM 加速推理**：内置 Flash Attention 2.7.4 预编译 wheel，提升吞吐与响应速度
- 🔧 **灵活配置**：支持显存利用率、最大序列数、多模态输入限制等参数动态调整
- 📝 **统一响应封装**：`APIResponse[T]` 泛型包装，统一 `success / data / error / error_code` 结构
- 🔄 **内置重试与清理**：推理失败自动重试（`MAX_RETRY`），请求结束自动清理 staging 临时文件
- 🪵 **日志自动轮转**：按小时清理 24h 以上日志，避免磁盘膨胀

---

## 📂 项目结构

```
bgm_service/
├── bgm_summarization.py     # FastAPI 入口（lifespan 加载模型 + /summarize_bgm + /health）
├── config/
│   ├── constant_config.py   # 常量：MAX_RETRY、日志保留时长/前缀
│   ├── path_config.py       # 路径：模型路径、staging 目录、日志目录
│   └── schema_config.py     # Pydantic schema：请求/响应/APIResponse 泛型
├── functionals/
│   ├── download.py          # ModelScope 模型下载脚本（snapshot_download）
│   ├── logger.py            # 日志器 + 后台清理线程
│   ├── prompts.py           # BGM_SUMMARY_PROMPT 提示词
│   └── utils.py             # URL 判定、音频下载、时长提取
├── flash-attn/              # 预编译 flash-attn wheel（gitignore）
├── models/                  # 本地模型权重（gitignore，需手动下载）
├── staging/                 # 音频暂存目录（容器内 /app/staging）
├── logs/                    # 运行日志（gitignore）
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml           # uv 依赖声明
└── uv.lock                  # 依赖锁定
```

> `models/`、`logs/`、`flash-attn/`、`staging/` 均在 `.gitignore` 中，clone 后需自行准备（见下文）。

---

## 💻 环境要求

| 组件     | 最低要求                   | 推荐配置                              |
|--------|------------------------|-----------------------------------|
| GPU    | NVIDIA RTX 3090 (24GB) | RTX 4090 / A100 (40GB+)           |
| CUDA   | 12.1+                  | 12.4                              |
| Docker | 24.0+                  | 29.0.1 + nvidia-container-toolkit |
| 显存     | ≥20GB                  | ≥32GB（支持更长音频）                     |
| 系统     | Linux / WSL2           | Ubuntu 22.04 LTS                  |

> ⚠️ 请确保已安装 [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html) 以支持 Docker GPU 直通。可用 `docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi` 验证。

---

## 🚀 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/lituokobe/BGM-Service.git
cd bgm_service
```

### 2. 下载 Qwen-Audio-Chat 模型权重（**必需，否则容器无法启动**）

`models/` 目录被 gitignore，不会随仓库下发。服务启动时会从 `models/Qwen/Qwen-Audio-Chat` 加载模型，因此**首次部署必须先下载权重**。

**方式 A — ModelScope（推荐，国内网络更快）**

```bash
pip install "modelscope>=1.36.2"

python -c "from modelscope import snapshot_download; \
  snapshot_download('Qwen/Qwen-Audio-Chat', cache_dir='./models')"
```

下载完成后，目录结构应为：

```
models/Qwen/Qwen-Audio-Chat/
├── config.json
├── model-*.safetensors (或 .bin)
├── tokenizer_config.json
└── ...
```

**方式 B — Hugging Face**

```bash
pip install -U "huggingface_hub[cli]"

huggingface-cli download Qwen/Qwen-Audio-Chat \
  --local-dir ./models/Qwen/Qwen-Audio-Chat
```

> 仓库内 `functionals/download.py` 也提供了 `snapshot_download` 调用示例，可按需取消注释后执行 `python functionals/download.py`。

### 3. 准备 flash-attn wheel（可选，已随仓库提供）

`flash-attn/` 目录默认包含预编译 wheel（`flash_attn-*.whl`，对应 torch 2.4 + cu124）。Dockerfile 会自动安装。若该目录为空，可从 [flash-attention releases](https://github.com/Dao-AILab/flash-attention/releases) 下载对应版本放入。

### 4. 构建并启动服务

```bash
docker compose up --build
```

首次启动需编译镜像并加载模型（约 5–8 分钟）。日志中出现 `✅ Qwen-Audio-Chat 模型加载成功` 即代表就绪。

### 5. 验证

```bash
curl http://localhost:8011/health
# {"status":"healthy","model":"Qwen-Audio-Chat","timestamp":"..."}
```

---

## 🛠️ 本地开发（非 Docker）

如需脱离 Docker 在宿主机直接运行（仅限 Linux x86_64 + CUDA 12.4）：

```bash
# 1. 安装 uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. 同步依赖（含 torch 2.4 + cu124）
uv sync --frozen

# 3. 安装 flash-attn（需与 torch/cuda 版本匹配）
uv pip install flash-attn/flash_attn-*.whl --no-deps

# 4. 设置模型路径并启动
export QWEN_AUDIO_CHAT_PATH="$(pwd)/models/Qwen/Qwen-Audio-Chat"
export PYTHONPATH="$(pwd)"
uv run uvicorn bgm_summarization:app --host 0.0.0.0 --port 8011
```

> ⚠️ `pyproject.toml` 中 `required-environments` 限定为 `linux/x86_64`，macOS / Windows 原生不支持，请使用 Docker 或 WSL2。

---

## ⚙️ 配置说明

### 环境变量

| 变量                       | 默认值                                | 说明                         |
|--------------------------|------------------------------------|----------------------------|
| `QWEN_AUDIO_CHAT_PATH`   | `/app/models/Qwen/Qwen-Audio-Chat` | 模型权重路径（docker-compose 已配置） |
| `OMP_NUM_THREADS`        | 2                                  | OpenMP 线程数                 |
| `TOKENIZERS_PARALLELISM` | false                              | 关闭 tokenizer 并行，避免死锁       |
| `TZ`                     | Asia/Shanghai                      | 容器时区                       |

### 关键常量（`config/constant_config.py`）

| 常量                  | 值   | 说明            |
|---------------------|-----|---------------|
| `MAX_RETRY`         | 2   | 推理失败重试次数      |
| `LOG_KEEPING_HOURS` | 24  | 日志保留小时数       |
| `LOG_PREFIX`        | bgm | 日志文件名前缀       |

### 挂载卷（docker-compose.yml）

| 宿主机路径           | 容器路径               | 模式   | 用途                |
|-----------------|--------------------|------|-------------------|
| `./staging`     | `/app/staging`     | rw   | 音频暂存（URL 下载/本地输入） |
| `./models`      | `/app/models`      | ro   | 模型权重              |
| `./logs`        | `/app/logs`        | rw   | 运行日志              |
| `./config`      | `/app/config`      | ro   | 配置代码              |
| `./functionals` | `/app/functionals` | ro   | 功能代码              |

> 改动 `bgm_summarization.py` / `config/` / `functionals/` 后，重启容器即可生效，无需重新 build 镜像。

---

## 📡 API 接口文档

完整交互文档：`http://localhost:8011/docs`（Swagger UI）。

### 🔍 健康检查

```http
GET http://localhost:8011/health
```

**响应**

```json
{
  "status": "healthy",
  "model": "Qwen-Audio-Chat",
  "timestamp": "2026-08-29T22:57:00"
}
```

> 模型未加载时返回 `503`，可用于就绪探针。

### 🎵 背景音乐描述

```http
POST http://localhost:8011/summarize_bgm
Content-Type: application/json

{
  "bgm_path": "https://example.com/audio.mp3"
}
```

`bgm_path` 支持两种形式：
- **HTTP(S) URL**：服务自动下载到 staging，处理完自动清理
- **本地文件名**：相对 staging 目录（如 `drum.mp3` → `/app/staging/drum.mp3`）

**成功响应**

```json
{
  "success": true,
  "data": {
    "overall_summary": "该段音乐为轻快治愈风格的轻音乐，以钢琴与弦乐为主导，辅以合成器铺底，氛围温暖明亮。适合用于生活、家庭、幼儿类短视频，能够营造温馨治愈的画面感。",
    "duration": 28.413
  },
  "error": null,
  "error_code": null
}
```

**失败响应**

```json
{
  "success": false,
  "data": null,
  "error": "音频文件在容器的staging路径中不存在: /app/staging/missing.mp3",
  "error_code": "FILE_NOT_FOUND"
}
```

**curl 示例**

```bash
curl -X POST http://localhost:8011/summarize_bgm \
  -H "Content-Type: application/json" \
  -d '{"bgm_path": "https://example.com/audio.mp3"}'
```

---

## 🚨 错误码

| error_code             | 触发场景                  |
|------------------------|-----------------------|
| `FILE_NOT_FOUND`       | staging 中找不到指定音频文件    |
| `FILE_INVALID`         | 路径存在但不是文件             |
| `SUMMARY_INVALID`      | 模型返回非字符串结果            |
| `LLM_INFERENCE_FAILED` | 重试 `MAX_RETRY` 次后仍失败  |
| `LLM_INTERNAL_ERROR`   | 其他未捕获异常               |

