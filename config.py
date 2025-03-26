from environs import Env

env = Env()
env.read_env()

BOT_TOKEN = env.str("BOT_TOKEN")
ADMIN_IDS = list(map(int, env.list("ADMIN_IDS")))