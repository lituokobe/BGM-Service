# This file is to use audio LLM to understand music and output description messages and deploy with FastAPI.

# ========= Import dependencies =========
import time
import os
from datetime import datetime
from pathlib import Path
import asyncio
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from config.constant_config import BGM_SUMMARY_PROMPT, MAX_RETRY
from config.path_config import QWEN_AUDIO_CHAT_PATH, STAGING_DIR
from config.schema_config import BGMSummary, SummarizeBGMRequest, APIResponse
from functionals.logger import bgm_logger
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from functionals.utils import is_url, download_file_from_url, get_bgm_duration

# ========= APIs =========
bgm_model = None
bgm_tokenizer = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load model once at startup, clean up on shutdown."""
    global bgm_model, bgm_tokenizer
    bgm_logger.info("🔧 正在加载 Qwen-Audio-Chat 模型...")
    start = time.time()

    bgm_tokenizer = AutoTokenizer.from_pretrained(
        QWEN_AUDIO_CHAT_PATH,
        trust_remote_code=True
    )
    bgm_model = AutoModelForCausalLM.from_pretrained(
        QWEN_AUDIO_CHAT_PATH,
        device_map="cuda",
        trust_remote_code=True
    ).eval()

    bgm_logger.info(f"✅ Qwen-Audio-Chat 模型加载成功，耗时{time.time() - start:.2f}秒")
    yield
    # Cleanup: release GPU memory
    if bgm_model is not None:
        del bgm_model
        torch.cuda.empty_cache()
        bgm_logger.info("🧹 Qwen-Audio-Chat 模型 GPU 显存释放")

app = FastAPI(
    title="BGM Summarization API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url=None
)

@app.post("/summarize_bgm", response_model=APIResponse[BGMSummary])
async def summarize_bgm(request: SummarizeBGMRequest) -> APIResponse[BGMSummary]:
    """Summarize background music to natural language description."""
    staged_file = None
    try:
        # ------ Check if input is URL or local path --------
        if is_url(request.bgm_path):
            # Download from URL
            staged_file = download_file_from_url(request.bgm_path, STAGING_DIR)
        else:
            # Use local file in staging directory
            staged_file = STAGING_DIR / request.bgm_path

        # ------ Create and validate audio path --------
        if not staged_file.exists():
            e_m = f"音频文件在容器的staging路径中不存在: {staged_file}"
            bgm_logger.error(e_m)
            return APIResponse[BGMSummary].fail(e_m, error_code="FILE_NOT_FOUND")
        if not staged_file.is_file():
            e_m = f"音频文件无效:{staged_file}"
            bgm_logger.error(e_m)
            return APIResponse[BGMSummary].fail(e_m, error_code="FILE_INVALID")

        # ------ Get duration ------
        bgm_duration = get_bgm_duration(staged_file)

        # ------ Describe the BGM --------
        query = bgm_tokenizer.from_list_format([
            {'audio': str(staged_file)},
            {'text': BGM_SUMMARY_PROMPT},
        ])

        bgm_summary = None

        for attempt in range(MAX_RETRY):
            try:
                # Invoke model
                start_time = time.time()
                bgm_summary, _ = bgm_model.chat(
                    bgm_tokenizer,
                    query=query,
                    history=None,
                    temperature=0.0,
                    top_k=1,
                    do_sample=False  # greedy and deterministic
                )
                latency = round(time.time() - start_time, 2)
                bgm_logger.info(f"{staged_file}总结完成，耗时{latency}秒。")

                if not isinstance(bgm_summary, str):
                    e_m = f"未能总结背景音乐{staged_file}"
                    bgm_logger.error(e_m)
                    return APIResponse[BGMSummary].fail(e_m, error_code="SUMMARY_INVALID")

            except Exception as e:
                em = f"第{attempt + 1}/{MAX_RETRY}次总结背景音乐{staged_file}，报错: {e}"
                bgm_logger.error(e_m)
                if attempt < (MAX_RETRY-1):
                    await asyncio.sleep(0.1)
                    continue
                return APIResponse[BGMSummary].fail(e_m , error_code="LLM_INFERENCE_FAILED")

        return APIResponse.ok(data=BGMSummary(overall_summary=bgm_summary, duration=bgm_duration))

    except Exception as e:
        e_m = f"背景音乐描述失败: {e}"
        bgm_logger.error(e_m)
        return APIResponse[BGMSummary].fail(e_m, error_code="LLM_INTERNAL_ERROR")

    finally:
        # 🔥 Guaranteed cleanup
        if staged_file and Path(staged_file).exists():
            try:
                if os.access(staged_file, os.W_OK):
                    Path(staged_file).unlink()
                    bgm_logger.debug(f"清理: {staged_file}")
            except Exception as e:
                bgm_logger.warning(f"{staged_file} 清理失败: {e}")

@app.get("/health")
async def health_check():
    """Production health check endpoint [[30]]."""
    if bgm_model is None or bgm_tokenizer is None:
        raise HTTPException(status_code=503, detail="Qwen-Audio-Chat 模型未加载")
    return {
        "status": "healthy",
        "model": "Qwen-Audio-Chat",
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    # BGM (music) summary
    result3 = {}
    for bgm in [
        # r"E:\Li_Tuo_work\bgm_service\bg_music\always_online.mp3",
        # r"E:\Li_Tuo_work\bgm_service\bg_music\chinese-happiness.mp3",
        # r"E:\Li_Tuo_work\bgm_service\bg_music\chinese-magnificent.mp3",
        # r"E:\Li_Tuo_work\bgm_service\bg_music\classic_ad.mp3",
        # r"E:\Li_Tuo_work\bgm_service\bg_music\classic_business.mp3",
        r"E:\Li_Tuo_work\bgm_service\bg_music\drum.mp3",
        # r"E:\Li_Tuo_work\bgm_service\bg_music\epic.mp3",
        # r"E:\Li_Tuo_work\bgm_service\bg_music\family.mp3",
        # r"E:\Li_Tuo_work\bgm_service\bg_music\fashionable.mp3",
        # r"E:\Li_Tuo_work\bgm_service\bg_music\guitar_solo.mp3",
        # r"E:\Li_Tuo_work\bgm_service\bg_music\hip-hop_rock_stylish.mp3",
        # r"E:\Li_Tuo_work\bgm_service\bg_music\inspiring_rock.mp3",
        # r"E:\Li_Tuo_work\bgm_service\bg_music\rock_trailer.mp3",
    ]:
        res = summarize_bgm(SummarizeBGMRequest(bgm_path=bgm))
        result3[bgm] = res

    print(result3)