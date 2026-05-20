from pathlib import Path

# Get project folder dir
current_file = Path(__file__).resolve()
project_dir = current_file.parent.parent

ENV_PATH = project_dir / ".env"
LOG_PATH = project_dir / "logs"

QWEN_AUDIO_CHAT_PATH = project_dir / "models/Qwen/Qwen-Audio-Chat"
STAGING_DIR = Path("/app/staging")