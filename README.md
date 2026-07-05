# 音频大模型服务 - 背景音乐智能描述

> 基于 Qwen-Audio-Chat 的本地化部署方案，为 AI 短视频项目提供高精度的背景音乐理解能力。
> this is change1222
> it is change2
=======
> this is change1


## 📋 目录
- [功能特性](#-功能特性)
- [环境要求](#-环境要求)
- [快速开始](#-快速开始)
- [API 接口文档](#-api-接口文档)

---

## ✨ 功能特性

- 🖼️ **背景音乐智能描述**：自动解析背景音乐的风格、乐器、氛围感，并输出适用于短视频制作的中文描述
- 🐳 **Docker 容器化**：一键部署，支持 GPU 直通，便于跨环境迁移
- ⚡ **vLLM 加速推理**：支持 Flash Attention 等优化，提升吞吐与响应速度
- 🔧 **灵活配置**：支持显存利用率、最大序列数、多模态输入限制等参数动态调整

---
## 💻 环境要求

| 组件        | 最低要求                | 推荐配置                                 |
|------------|------------------------|---------------------------------------|
| GPU        | NVIDIA RTX 3090 (24GB) | RTX 4090 / A100 (40GB+)               |
| CUDA       | 12.1+                  | 12.4                                  |
| Docker     | 24.0+                  | 29.0.1 with nvidia-container-toolkit  |
| 显存        | ≥20GB                  | ≥32GB（支持更长音频）                     |
| 系统        | Linux / WSL2           | Ubuntu 22.04 LTS                      |

> ⚠️ 请确保已安装 [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html) 以支持 Docker GPU 直通。

---

## 🚀 快速开始

```bash
git clone http://gogs.km360.cn/lituo/bgm-service.git

cd bgm_service

docker compose up
```

---

## 📡 API 接口文档

### 🔍 健康检查
```http
GET http://localhost:8011/health
```
**响应**：
```json
{
  "status": "healthy",
  "model": "Qwen-Audio-Chat",
  "timestamp": "当前时间"
}
```
### 🖼️ 背景音乐描述（必须是http网络音频）
```http
POST http://localhost:8011/summarize_bgm
Content-Type: application/json

{
  "bgm_path": "https://example.com/audio.mp3"
}
```
**响应**：
```json
{
    "overall_summary": "音频的中文描述。本项目中的音频主要是背景音乐，描述中会包含风格、乐器、氛围感，以及适用于何种短视频制作。"
}
```

