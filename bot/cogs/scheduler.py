"""Daily summary scheduler with history fetching."""
import nextcord
from nextcord.ext import commands, tasks
from nextcord import Interaction, SlashOption, Color
from datetime import datetime, timedelta
from typing import Optional
import pytz
import logging

from bot.config import Config
from bot.analyzer import FeedbackAnalyzer

logger = logging.getLogger(__name__)


class DailySummaryScheduler(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.analyzer = FeedbackAnalyzer()
        self.summary_channel_id: Optional[str] = "1467997889987874980"
        self.last_run: Optional[datetime] = None
        self.schedule_daily.start()

    def cog_unload(self):
        self.schedule_daily.cancel()

    async def _fetch_recent_messages(self) -> list[dict]:
        messages = []
        if self.last_run:
            cutoff = self.last_run
        else:
            cutoff = datetime.now(pytz.UTC) - timedelta(hours=24)

        for channel_id in Config.MONITORED_CHANNEL_IDS:
            try:
                channel = self.bot.get_channel(int(channel_id))
                if not channel:
                    continue
                async for msg in channel.history(after=cutoff, limit=500):
                    if msg.author.bot:
                        continue
                    messages.append({
                        "content": msg.content,
                        "author": str(msg.author),
                        "channel": channel.name,
                        "timestamp": msg.created_at.isoformat(),
                        "jump_url": msg.jump_url
                    })
            except Exception as e:
                logger.error(f"Error fetching channel {channel_id}: {e}")

        self.last_run = datetime.now(pytz.UTC)
        logger.info(f"Fetched {len(messages)} messages")
        return messages

    async def generate_summary(self) -> tuple[str, list[dict]]:
        messages = await self._fetch_recent_messages()
        if not messages:
            return "Nothing new found. Check back later.", []
        summary = await self.analyzer.analyze_batch(messages)
        return summary, messages

    @tasks.loop(hours=24)
    async def schedule_daily(self):
        if not self.summary_channel_id:
            return
        channel = self.bot.get_channel(int(self.summary_channel_id))
        if not channel:
            return
        summary, messages = await self.generate_summary()
        embed = nextcord.Embed(
            title="Daily Feedback Summary",
            description=summary,
            color=Color.blue(),
            timestamp=datetime.now(pytz.UTC)
        )
        embed.set_footer(text=f"Analyzed {len(messages)} messages")
        await channel.send(embed=embed)

    @schedule_daily.before_loop
    async def before_schedule_daily(self):
        await self.bot.wait_until_ready()
        et = pytz.timezone(Config.SUMMARY_TIMEZONE)
        now = datetime.now(et)
        target = now.replace(hour=Config.SUMMARY_HOUR, minute=0, second=0, microsecond=0)
        if now >= target:
            target += timedelta(days=1)
        wait_seconds = (target - now).total_seconds()
        logger.info(f"Daily summary scheduled for {Config.SUMMARY_HOUR}:00 AM ET")
        import asyncio
        await asyncio.sleep(wait_seconds)

    @nextcord.slash_command(name="summary", description="Get a feedback summary now")
    async def summary_command(self, interaction: Interaction):
        await interaction.response.defer()
        summary, messages = await self.generate_summary()
        embed = nextcord.Embed(
            title="Feedback Summary",
            description=summary,
            color=Color.blue(),
            timestamp=datetime.now(pytz.UTC)
        )
        embed.set_footer(text=f"Analyzed {len(messages)} messages")
        await interaction.followup.send(embed=embed)

    @nextcord.slash_command(name="setchannel", description="Set the channel for daily summaries")
    async def set_channel_command(self, interaction: Interaction, channel: nextcord.TextChannel):
        self.summary_channel_id = str(channel.id)
        await interaction.response.send_message(f"Summaries will be posted to {channel.mention}")


def setup(bot: commands.Bot):
    bot.add_cog(DailySummaryScheduler(bot))
