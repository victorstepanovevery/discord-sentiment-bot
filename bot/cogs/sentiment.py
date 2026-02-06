"""App feedback monitor - listens for mentions of Cora, Spiral, Sparkle, Monologue."""

import json
import logging
import random
import time
from collections import deque
from datetime import datetime
from typing import TYPE_CHECKING

import anthropic
from nextcord import Message
from nextcord.ext import commands, tasks

from ..config import Config
from ..database import Database, FeedbackRecord

if TYPE_CHECKING:
    from nextcord.ext.commands import Bot

log = logging.getLogger(__name__)

# Focused prompt for app feedback analysis
FEEDBACK_SYSTEM = """You analyze Discord messages about apps (Cora, Spiral, Sparkle, Monologue).
Classify the feedback sentiment and extract key points.

Return JSON:
{
  "sentiment": "positive" | "negative" | "neutral" | "mixed",
  "feedback_type": "bug" | "feature_request" | "praise" | "complaint" | "question" | "general",
  "summary": "brief 1-sentence summary of what they're saying about the app",
  "actionable": true | false
}

Examples:
- "Cora keeps crashing when I try to export" → {"sentiment": "negative", "feedback_type": "bug", "summary": "Export feature causing crashes", "actionable": true}
- "I love how Spiral organizes my thoughts!" → {"sentiment": "positive", "feedback_type": "praise", "summary": "User loves the organization feature", "actionable": false}
- "Can Monologue add dark mode?" → {"sentiment": "neutral", "feedback_type": "feature_request", "summary": "Requesting dark mode feature", "actionable": true}"""


class SentimentAnalyzer(commands.Cog):
    """Cog that monitors for app feedback in specific channels."""

    def __init__(self, bot: "Bot", database: Database):
        self.bot = bot
        self.db = database
        self.client = anthropic.Anthropic(api_key=Config.ANTHROPIC_API_KEY)
        self.message_queue: deque = deque(maxlen=500)
        self._retry_count = 0
        self._max_retries = 3

    def cog_load(self) -> None:
        """Start the batch processor when cog loads."""
        self.batch_processor.start()
        log.info(f"App feedback monitor loaded - watching {len(Config.MONITORED_CHANNEL_IDS)} channels")
        log.info(f"Monitoring for: {', '.join(Config.MONITORED_APPS)}")

    def cog_unload(self) -> None:
        """Stop the batch processor when cog unloads."""
        self.batch_processor.cancel()
        log.info("App feedback monitor unloaded")

    @commands.Cog.listener()
    async def on_message(self, message: Message) -> None:
        """Listen for messages mentioning monitored apps."""
        # Ignore bots
        if message.author.bot:
            return

        # Ignore DMs
        if not message.guild:
            return

        # Skip empty messages
        if not message.content or not message.content.strip():
            return

        # Only monitor specific channels (hardcoded in config)
        if str(message.channel.id) not in Config.MONITORED_CHANNEL_IDS:
            return

        # Only capture messages that mention our apps
        mentioned_apps = Config.mentions_monitored_app(message.content)
        if not mentioned_apps:
            return  # Skip messages that don't mention any app

        # Add to queue for batch processing
        self.message_queue.append({
            "guild_id": str(message.guild.id),
            "channel_id": str(message.channel.id),
            "channel_name": message.channel.name,
            "message_id": str(message.id),
            "author_id": str(message.author.id),
            "author_name": str(message.author.display_name),
            "content": message.content[:1000],  # Keep more context for feedback
            "apps_mentioned": mentioned_apps,
            "timestamp": message.created_at,
            "jump_url": message.jump_url,
        })

        log.info(f"Captured feedback about {mentioned_apps} from {message.author.display_name}")

    @tasks.loop(seconds=Config.BATCH_INTERVAL_SECONDS)
    async def batch_processor(self) -> None:
        """Process queued messages every hour."""
        if not self.message_queue:
            log.info("Hourly check: No app feedback to process")
            return

        # Collect all queued messages
        batch = []
        while self.message_queue:
            batch.append(self.message_queue.popleft())

        log.info(f"Processing {len(batch)} app feedback messages")

        try:
            results = await self._analyze_batch(batch)
            await self._store_results(results)
            self._retry_count = 0
            log.info(f"Stored {len(results)} feedback records")
        except anthropic.RateLimitError as e:
            log.warning(f"Rate limited by Claude API: {e}")
            await self._handle_rate_limit(batch)
        except anthropic.APIError as e:
            log.error(f"Claude API error: {e}")
            await self._handle_api_error(batch)
        except Exception as e:
            log.exception(f"Batch processing failed: {e}")

    @batch_processor.before_loop
    async def before_batch_processor(self) -> None:
        """Wait until bot is ready before starting."""
        await self.bot.wait_until_ready()
        log.info("App feedback monitor ready")

    async def _analyze_batch(self, messages: list[dict]) -> list[FeedbackRecord]:
        """Analyze feedback using Claude API."""
        results = []

        for msg in messages:
            try:
                response = self.client.messages.create(
                    model=Config.CLAUDE_MODEL,
                    max_tokens=Config.MAX_TOKENS,
                    system=[{
                        "type": "text",
                        "text": FEEDBACK_SYSTEM,
                        "cache_control": {"type": "ephemeral"}
                    }],
                    messages=[{
                        "role": "user",
                        "content": f"Analyze this feedback about {', '.join(msg['apps_mentioned'])}:\n\n{msg['content']}"
                    }]
                )

                response_text = response.content[0].text.strip()

                # Parse JSON response
                try:
                    data = json.loads(response_text)
                except json.JSONDecodeError:
                    import re
                    json_match = re.search(r'\{[^}]+\}', response_text, re.DOTALL)
                    if json_match:
                        data = json.loads(json_match.group())
                    else:
                        log.warning(f"Could not parse response: {response_text[:100]}")
                        # Store with defaults
                        data = {
                            "sentiment": "neutral",
                            "feedback_type": "general",
                            "summary": msg["content"][:100],
                            "actionable": False
                        }

                record = FeedbackRecord(
                    guild_id=msg["guild_id"],
                    channel_id=msg["channel_id"],
                    channel_name=msg["channel_name"],
                    message_id=msg["message_id"],
                    author_id=msg["author_id"],
                    author_name=msg["author_name"],
                    content=msg["content"],
                    apps_mentioned=",".join(msg["apps_mentioned"]),
                    sentiment=data.get("sentiment", "neutral"),
                    feedback_type=data.get("feedback_type", "general"),
                    summary=data.get("summary", ""),
                    actionable=data.get("actionable", False),
                    message_timestamp=msg["timestamp"],
                    jump_url=msg["jump_url"],
                )
                results.append(record)

            except Exception as e:
                log.warning(f"Failed to analyze message {msg['message_id']}: {e}")
                continue

        return results

    async def _store_results(self, results: list[FeedbackRecord]) -> None:
        """Store feedback records in database."""
        for record in results:
            try:
                await self.db.insert_feedback_record(record)
            except Exception as e:
                log.warning(f"Failed to store feedback {record.message_id}: {e}")

    async def _handle_rate_limit(self, batch: list[dict]) -> None:
        """Handle rate limit by re-queuing."""
        self._retry_count += 1
        if self._retry_count <= self._max_retries:
            wait_time = (2 ** self._retry_count) + random.uniform(0, 1)
            log.info(f"Re-queuing {len(batch)} messages after {wait_time:.1f}s")
            time.sleep(wait_time)
            for msg in reversed(batch):
                self.message_queue.appendleft(msg)
        else:
            log.error(f"Max retries exceeded, dropping {len(batch)} messages")
            self._retry_count = 0

    async def _handle_api_error(self, batch: list[dict]) -> None:
        """Handle API errors by re-queuing."""
        for msg in reversed(batch[:20]):
            self.message_queue.appendleft(msg)
        log.info(f"Re-queued 20 messages after API error")


def setup(bot: "Bot") -> None:
    """Setup function for loading cog."""
    pass
