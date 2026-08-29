# Audio LLM Service - Background Music Description

> 🌐 English | [简体中文](README_cn.md)
>
> A local deployment solution based on [Qwen-Audio-Chat](https://huggingface.co/Qwen/Qwen-Audio-Chat), providing high-precision background music understanding for AI short-video projects.
> Given a piece of background music, it outputs a 200–250 character Chinese description covering overall style, genre, core instruments, and suitable scenarios.

## 📋 Table of Contents

- [Features](#-features)
- [Project Structure](#-project-structure)
- [Requirements](#-requirements)
- [Quick Start](#-quick-start)
- [Local Development (without Docker)](#-local-development-without-docker)
- [Configuration](#-configuration)
- [API Reference](#-api-reference)
- [Error Codes](#-error-codes)

---

## ✨ Features

- 🎵 **Intelligent BGM description**: Automatically parses a track's style, instruments, and mood, and outputs a Chinese description tailored for short-video production
- 🐳 **Dockerized**: One-command deployment with GPU passthrough, easy to migrate across environments
- ⚡ **Accelerated inference**: Ships with a prebuilt Flash Attention 2.7.4 wheel for higher throughput and lower latency
- 🔧 **Flexible configuration**: Tunable GPU memory utilization, max sequences, and multimodal input limits
- 📝 **Unified response envelope**: Generic `APIResponse[T]` wrapper with a consistent `success / data / error / error_code` shape
- 🔄 **Built-in retry & cleanup**: Auto-retry on inference failure (`MAX_RETRY`), auto-removal of staging temp files after each request
- 🪵 **Automatic log rotation**: Hourly cleanup of logs older than 24h to prevent disk bloat

---

## 📂 Project Structure

```
bgm_service/
├── bgm_summarization.py     # FastAPI entry (lifespan model load + /summarize_bgm + /health)
├── config/
│   ├── constant_config.py   # Constants: MAX_RETRY, log retention/prefix
│   ├── path_config.py       # Paths: model path, staging dir, log dir
│   └── schema_config.py     # Pydantic schema: request/response/APIResponse generic
├── functionals/
│   ├── download.py          # ModelScope model download script (snapshot_download)
│   ├── logger.py            # Logger + background cleanup thread
│   ├── prompts.py           # BGM_SUMMARY_PROMPT prompt
│   └── utils.py             # URL detection, audio download, duration extraction
├── flash-attn/              # Prebuilt flash-attn wheel (gitignored)
├── models/                  # Local model weights (gitignored, must be downloaded manually)
├── staging/                 # Audio staging dir (container path /app/staging)
├── logs/                    # Runtime logs (gitignored)
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml           # uv dependency declaration
└── uv.lock                  # Dependency lockfile
```

> `models/`, `logs/`, `flash-attn/`, and `staging/` are all in `.gitignore` — you must prepare them yourself after cloning (see below).

---

## 💻 Requirements

| Component | Minimum                   | Recommended                            |
| --------- | ------------------------- | -------------------------------------- |
| GPU       | NVIDIA RTX 3090 (24GB)    | RTX 4090 / A100 (40GB+)                |
| CUDA      | 12.1+                     | 12.4                                   |
| Docker    | 24.0+                     | 29.0.1 + nvidia-container-toolkit      |
| VRAM      | ≥20GB                     | ≥32GB (for longer audio)               |
| OS        | Linux / WSL2              | Ubuntu 22.04 LTS                       |

> ⚠️ Make sure [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html) is installed for Docker GPU passthrough. Verify with `docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi`.

---

## 🚀 Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/lituokobe/BGM-Service.git
cd bgm_service
```

### 2. Download the Qwen-Audio-Chat model weights (**required, otherwise the container cannot start**)

The `models/` directory is gitignored and is not distributed with the repo. The service loads the model from `models/Qwen/Qwen-Audio-Chat` at startup, so **you must download the weights before first deployment**.

**Option A — ModelScope (recommended, faster in mainland China)**

```bash
pip install "modelscope>=1.36.2"

python -c "from modelscope import snapshot_download; \
  snapshot_download('Qwen/Qwen-Audio-Chat', cache_dir='./models')"
```

After download, the directory should look like:

```
models/Qwen/Qwen-Audio-Chat/
├── config.json
├── model-*.safetensors (or .bin)
├── tokenizer_config.json
└── ...
```

**Option B — Hugging Face**

```bash
pip install -U "huggingface_hub[cli]"

huggingface-cli download Qwen/Qwen-Audio-Chat \
  --local-dir ./models/Qwen/Qwen-Audio-Chat
```

> The repo's `functionals/download.py` also provides a `snapshot_download` example — uncomment the relevant line and run `python functionals/download.py`.

### 3. Prepare the flash-attn wheel (optional, already bundled)

The `flash-attn/` directory ships with a prebuilt wheel (`flash_attn-*.whl`, matching torch 2.4 + cu124), which the Dockerfile installs automatically. If the directory is empty, download the matching version from [flash-attention releases](https://github.com/Dao-AILab/flash-attention/releases) and place it there.

### 4. Build and start the service

```bash
docker compose up --build
```

The first start builds the image and loads the model (~5–8 minutes). The service is ready when the logs show `✅ Qwen-Audio-Chat 模型加载成功`.

### 5. Verify

```bash
curl http://localhost:8011/health
# {"status":"healthy","model":"Qwen-Audio-Chat","timestamp":"..."}
```

---

## 🛠️ Local Development (without Docker)

To run directly on the host without Docker (Linux x86_64 + CUDA 12.4 only):

```bash
# 1. Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Sync dependencies (includes torch 2.4 + cu124)
uv sync --frozen

# 3. Install flash-attn (must match torch/cuda version)
uv pip install flash-attn/flash_attn-*.whl --no-deps

# 4. Set the model path and start
export QWEN_AUDIO_CHAT_PATH="$(pwd)/models/Qwen/Qwen-Audio-Chat"
export PYTHONPATH="$(pwd)"
uv run uvicorn bgm_summarization:app --host 0.0.0.0 --port 8011
```

> ⚠️ `pyproject.toml` pins `required-environments` to `linux/x86_64`; macOS / Windows native is not supported — use Docker or WSL2.

---

## ⚙️ Configuration

### Environment variables

| Variable                 | Default                              | Description                                       |
| ------------------------ | ----------------------------------- | ------------------------------------------------- |
| `QWEN_AUDIO_CHAT_PATH`   | `/app/models/Qwen/Qwen-Audio-Chat`  | Model weights path (configured in docker-compose) |
| `OMP_NUM_THREADS`        | 2                                   | OpenMP thread count                               |
| `TOKENIZERS_PARALLELISM` | false                               | Disable tokenizer parallelism to avoid deadlock   |
| `TZ`                     | Asia/Shanghai                       | Container timezone                                |

### Key constants (`config/constant_config.py`)

| Constant             | Value | Description                       |
| -------------------- | ----- | --------------------------------- |
| `MAX_RETRY`          | 2     | Inference failure retry count     |
| `LOG_KEEPING_HOURS`  | 24    | Log retention in hours            |
| `LOG_PREFIX`         | bgm   | Log filename prefix               |

### Mount volumes (`docker-compose.yml`)

| Host path       | Container path        | Mode | Purpose                              |
| --------------- | --------------------- | ---- | ------------------------------------ |
| `./staging`     | `/app/staging`        | rw   | Audio staging (URL download / local) |
| `./models`      | `/app/models`         | ro   | Model weights                        |
| `./logs`        | `/app/logs`           | rw   | Runtime logs                         |
| `./config`      | `/app/config`         | ro   | Configuration code                   |
| `./functionals` | `/app/functionals`    | ro   | Functional code                      |

> After editing `bgm_summarization.py` / `config/` / `functionals/`, just restart the container — no image rebuild needed.

---

## 📡 API Reference

Full interactive docs: `http://localhost:8011/docs` (Swagger UI).

### 🔍 Health check

```http
GET http://localhost:8011/health
```

**Response**

```json
{
  "status": "healthy",
  "model": "Qwen-Audio-Chat",
  "timestamp": "2026-08-29T22:57:00"
}
```

> Returns `503` when the model is not loaded — usable as a readiness probe.

### 🎵 Background music description

```http
POST http://localhost:8011/summarize_bgm
Content-Type: application/json

{
  "bgm_path": "https://example.com/audio.mp3"
}
```

`bgm_path` accepts two forms:
- **HTTP(S) URL**: the service downloads it to staging and cleans up automatically after processing
- **Local filename**: relative to the staging dir (e.g. `drum.mp3` → `/app/staging/drum.mp3`)

**Success response**

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

**Failure response**

```json
{
  "success": false,
  "data": null,
  "error": "音频文件在容器的staging路径中不存在: /app/staging/missing.mp3",
  "error_code": "FILE_NOT_FOUND"
}
```

**curl example**

```bash
curl -X POST http://localhost:8011/summarize_bgm \
  -H "Content-Type: application/json" \
  -d '{"bgm_path": "https://example.com/audio.mp3"}'
```

---

## 🚨 Error Codes

| error_code             | Trigger                                             |
| ---------------------- | --------------------------------------------------- |
| `FILE_NOT_FOUND`       | Specified audio file not found in staging            |
| `FILE_INVALID`         | Path exists but is not a file                       |
| `SUMMARY_INVALID`      | Model returned a non-string result                 |
| `LLM_INFERENCE_FAILED` | Still failing after `MAX_RETRY` attempts            |
| `LLM_INTERNAL_ERROR`   | Other uncaught exception                            |
