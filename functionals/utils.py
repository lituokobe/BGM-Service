import socket
import uuid
import librosa
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from functionals.logger import bgm_logger

def is_url(path: str) -> bool:
    """Check if path is a URL."""
    return path.startswith(('http://', 'https://', 'ftp://'))

def download_file_from_url(url: str, staging_dir: Path|str) -> Path|None:
    """Download file from URL to staging directory using urllib (no external deps)."""
    if isinstance(staging_dir, str):
        staging_dir = Path(staging_dir)

    local_path = None  # Initialize to avoid scope issues

    try:
        # Generate unique filename
        parsed = urlparse(url)
        original_filename = Path(parsed.path).name or f"download_{uuid.uuid4().hex[:8]}"

        # Determine extension from URL
        if '.' not in original_filename:
            if 'audio' in url.lower() or any(url.lower().endswith(ext) for ext in ['.mp3', '.wav', '.wma', '.m4a', '.acc']):
                original_filename += '.mp3'
            else:
                original_filename += '.bin'

        local_path = staging_dir / original_filename

        bgm_logger.info(f"📥 从该URL下载: {url}")
        bgm_logger.info(f"📁 保存到: {local_path}")

        # 🔑 CRITICAL: Add User-Agent header to avoid 403 errors
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.google.com/',
            'DNT': '1',
            'Connection': 'keep-alive',
        }

        request = Request(url, headers=headers)

        # Set timeout to avoid hanging
        old_timeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(60)

        try:
            # Download with streaming
            with urlopen(request, timeout=60) as response, open(local_path, 'wb') as out_file:
                # Read in chunks to handle large files
                while True:
                    chunk = response.read(8192)
                    if not chunk:
                        break
                    out_file.write(chunk)
        finally:
            socket.setdefaulttimeout(old_timeout)  # Restore original timeout

        # Verify download succeeded
        if not local_path.exists() or local_path.stat().st_size == 0:
            raise RuntimeError(f"下载文件为空或缺失: {url}")

        bgm_logger.info(f"✅ 下载完成: {local_path} ({local_path.stat().st_size} bytes)")
        return local_path

    except Exception as e:
        bgm_logger.error(f"❌ 下载失败{url}: {e}")
        # Clean up partial file if it exists
        if 'local_path' in locals() and local_path.exists():
            try:
                local_path.unlink()
                bgm_logger.debug(f"🗑️ 清理失败下载: {local_path}")
            except:
                pass
        return None

def get_bgm_duration(path: str) -> float:
    """get the duration of a video"""
    try:
        duration = librosa.get_duration(path=path)
        duration = round(duration, 3)
        bgm_logger.info(f"背景音乐{path}时长为{duration}秒。")
    except Exception as e:
        duration = 0.0
        bgm_logger.error(f"背景音乐{path}无法提取时长: {e}")
    return duration

if __name__ == "__main__":
     get_bgm_duration(r"E:\Li_Tuo_work\bgm_service\bg_music\always_online.mp3")