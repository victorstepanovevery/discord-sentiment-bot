"""Main entry point for the Discord Sentiment Bot."""
import logging
import nextcord
from nextcord.ext import commands

from bot.config import Config
from bot.database import Database
from bot.cogs.scheduler import DailySummaryScheduler

logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    try:
        Config.validate()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        return

    intents = nextcord.Intents.default()
    intents.message_content = True
    intents.guilds = True

    bot = commands.Bot(intents=intents)
    db = Database(Config.get_database_path())

    @bot.event
    async def on_ready():
        logger.info(f"Bot logged in as {bot.user} (ID: {bot.user.id})")
        logger.info(f"Connected to {len(bot.guilds)} guild(s)")
        for guild in bot.guilds:
            logger.info(f"  - {guild.name} (ID: {guild.id})")
        await db.connect()
        await bot.sync_all_application_commands()
        logger.info("Slash commands synced successfully")

    @bot.event
    async def on_disconnect():
        await db.disconnect()

    try:
        bot.add_cog(DailySummaryScheduler(bot))
        logger.info("All cogs loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load cogs: {e}")
        return

    logger.info("Starting Discord Sentiment Bot...")
    bot.run(Config.DISCORD_TOKEN)


if __name__ == "__main__":
    main()
