import yaml
import dotenv
from pathlib import Path

config_dir = Path(__file__).parent.parent.resolve() / "config"

# load yaml config
with open(config_dir / "config.yml", 'r') as f:
    config_yaml = yaml.safe_load(f)

# load .env config
config_env = dotenv.dotenv_values(config_dir / "config.env")

# config parameters
telegram_token = config_yaml["telegram_token"]
allowed_telegram_usernames = config_yaml["allowed_telegram_usernames"]

hugging_face_as_openai_api_key = config_yaml["hugging_face_as_openai_api_key"]
openai_api_base = config_yaml.get("openai_api_base", None)

new_dialog_timeout = config_yaml["new_dialog_timeout"]
enable_message_streaming = config_yaml.get("enable_message_streaming", True)
sqlite_database_uri = config_env['SQLITE_DATABASE_PATH']

fusion_brain_auth_token = config_yaml["fusion_brain_auth_token"]
