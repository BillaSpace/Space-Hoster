import os
from dotenv import load_dotenv
load_dotenv()

# Telegram
BOT_TOKEN  = os.getenv("BOT_TOKEN")          # hoster bot token
BOT_USERNAME = "SpaceDeployerBot"

# MongoDB
MONGODB_URI  = os.getenv("MONGODB_URI")
DATABASE_NAME = "space_deployer"

# Privileged users
OWNER_ID  = int(os.getenv("OWNER_ID", "5960968099"))
DEV_ID    = int(os.getenv("DEV_ID", "5960968099"))
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x]

# Channels
UPDATES_CHANNEL = "@billaspace"
SUPPORT_CHAT    = "@billacore"
DEVELOPER       = "@x_ifeelram"
LOGGER_ID       = "-1002068576120"
# Limits
MAX_BOTS_FREE = 1
UPLOAD_MAX_MB = 100

# Paths
UPLOAD_PATH = "uploads"
TEMP_PATH   = "temp"
BOTS_PATH   = "deployed_bots"
BASE_PORT   = 8000
MAX_PORT    = 9000

# Docker
DOCKER_ENABLED = os.getenv("DOCKER_ENABLED", "true").lower() == "true"
DOCKER_NETWORK = "space_deployer_network"
