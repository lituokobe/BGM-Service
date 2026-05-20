FROM nvidia/cuda:12.4.1-cudnn-devel-ubuntu22.04

# 🇨🇳 Use Alibaba Cloud mirror for Ubuntu packages
RUN sed -i 's|http://archive.ubuntu.com/ubuntu|https://mirrors.aliyun.com/ubuntu|g' /etc/apt/sources.list && \
    sed -i 's|http://security.ubuntu.com/ubuntu|https://mirrors.aliyun.com/ubuntu|g' /etc/apt/sources.list && \
    apt-get update && apt-get install -y --no-install-recommends \
    python3.11 python3.11-venv python3-pip python3.11-dev \
    ffmpeg libsndfile1 libgl1 libglib2.0-0 curl ca-certificates \
    build-essential ninja-build \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean \
    && ln -sf /usr/bin/python3.11 /usr/bin/python \
    && ln -sf /usr/bin/pip3 /usr/bin/pip

WORKDIR /app

# Runtime environment variables (these persist in the running container)
ENV DEBIAN_FRONTEND=noninteractive \
    TZ=Asia/Shanghai \
    CUDA_HOME=/usr/local/cuda \
    PATH="/usr/local/cuda/bin:$PATH" \
    LD_LIBRARY_PATH="/usr/local/cuda/lib64:$LD_LIBRARY_PATH" \
    PYTHONPATH="/app" \
    PYTHONUNBUFFERED=1

# Base image nvidia/cuda:12.4.1-cudnn-devel-ubuntu22.04 likely already includes tzdata
# Need to convert it to TZ
RUN apt-get update && apt-get install -y --no-install-recommends tzdata && \
    ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && \
    echo $TZ > /etc/timezone && \
    rm -rf /var/lib/apt/lists/*

# Install uv to a shared, world-readable location
ADD https://astral.sh/uv/0.11.6/install.sh /uv-installer.sh
RUN sh /uv-installer.sh && \
    mv /root/.local/bin/uv /usr/local/bin/uv && \
    rm -rf /root/.local/bin /uv-installer.sh

# Copy dependencies (enables Docker layer caching)
COPY pyproject.toml uv.lock ./

# Copy pre-built flash-attn wheel
COPY flash-attn/*.whl /wheels/

RUN --mount=type=cache,target=/root/.cache/uv \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_DEV=1 \
    UV_HTTP_TIMEOUT=1200 \
    UV_INDEX_URL="https://pypi.tuna.tsinghua.edu.cn/simple" \
    uv sync --frozen --no-install-project

# Install flash-attn separately with build isolation disabled, this ensures torch is already in the venv when flash-attn builds
# flash-attn 2.7.4.post1 is version suitable for torch2.4+cu12, verified from https://github.com/Dao-AILab/flash-attention/releases
# Install flash-attn from local tarball WITH proper error handling
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install /wheels/flash_attn-*.whl --no-deps

# Create a non-root user with fixed UID/GID
RUN useradd -m -u 1008 appuser && chown -R appuser:appuser /app /app/.venv

# Create necessary directories with correct permissions
RUN mkdir -p /app/logs && \
    chown -R appuser:appuser /app/logs

# Switch to non-root user for security
USER appuser

# Expose the service port
EXPOSE 8011