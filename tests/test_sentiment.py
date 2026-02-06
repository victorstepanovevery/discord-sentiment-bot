"""Tests for app feedback monitoring functionality."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from bot.cogs.sentiment import SentimentAnalyzer, FEEDBACK_SYSTEM
from bot.config import Config


class MockMessage:
    """Mock Discord message for testing."""

    def __init__(
        self,
        content: str = "Test message",
        author_bot: bool = False,
        guild_id: int = 123456789,
        channel_id: int = 1019678288618205294,  # Use a monitored channel
        channel_name: str = "discussions",
        message_id: int = 999888777,
        author_id: int = 444555666,
        author_name: str = "TestUser",
    ):
        self.content = content
        self.author = MagicMock()
        self.author.bot = author_bot
        self.author.id = author_id
        self.author.display_name = author_name
        self.guild = MagicMock()
        self.guild.id = guild_id
        self.channel = MagicMock()
        self.channel.id = channel_id
        self.channel.name = channel_name
        self.id = message_id
        self.created_at = datetime.utcnow()
        self.jump_url = f"https://discord.com/channels/{guild_id}/{channel_id}/{message_id}"


@pytest.fixture
def mock_bot():
    """Create a mock Discord bot."""
    bot = MagicMock()
    bot.wait_until_ready = AsyncMock()
    return bot


@pytest.fixture
def mock_database():
    """Create a mock database."""
    db = MagicMock()
    db.insert_feedback_record = AsyncMock(return_value=1)
    return db


@pytest.fixture
def mock_anthropic_client():
    """Create a mock Anthropic client."""
    client = MagicMock()

    # Mock response for app feedback
    mock_response = MagicMock()
    mock_response.content = [MagicMock()]
    mock_response.content[0].text = json.dumps({
        "sentiment": "negative",
        "feedback_type": "bug",
        "summary": "Export feature causing crashes",
        "actionable": True
    })

    client.messages.create = MagicMock(return_value=mock_response)
    return client


class TestFeedbackSystem:
    """Tests for the feedback analysis system prompt."""

    def test_system_prompt_exists(self):
        """Verify the feedback system prompt is defined."""
        assert FEEDBACK_SYSTEM is not None
        assert "positive" in FEEDBACK_SYSTEM
        assert "negative" in FEEDBACK_SYSTEM
        assert "neutral" in FEEDBACK_SYSTEM
        assert "mixed" in FEEDBACK_SYSTEM

    def test_system_prompt_includes_apps(self):
        """Verify the system prompt mentions the monitored apps."""
        assert "Cora" in FEEDBACK_SYSTEM
        assert "Spiral" in FEEDBACK_SYSTEM
        assert "Sparkle" in FEEDBACK_SYSTEM
        assert "Monologue" in FEEDBACK_SYSTEM

    def test_system_prompt_includes_feedback_types(self):
        """Verify the system prompt includes feedback types."""
        assert "bug" in FEEDBACK_SYSTEM
        assert "feature_request" in FEEDBACK_SYSTEM
        assert "praise" in FEEDBACK_SYSTEM
        assert "complaint" in FEEDBACK_SYSTEM


class TestConfigAppMentions:
    """Tests for app mention detection in Config."""

    def test_detects_single_app(self):
        """Test detection of single app mention."""
        result = Config.mentions_monitored_app("I love using Cora for my work!")
        assert result == ["cora"]

    def test_detects_multiple_apps(self):
        """Test detection of multiple app mentions."""
        result = Config.mentions_monitored_app("Spiral is great but Sparkle needs work")
        assert "spiral" in result
        assert "sparkle" in result

    def test_case_insensitive(self):
        """Test that detection is case insensitive."""
        result = Config.mentions_monitored_app("CORA and MONOLOGUE are awesome")
        assert "cora" in result
        assert "monologue" in result

    def test_no_app_mention(self):
        """Test that non-app messages return empty list."""
        result = Config.mentions_monitored_app("This is a regular message")
        assert result == []

    def test_all_apps(self):
        """Test detection of all four apps."""
        result = Config.mentions_monitored_app("Cora, Spiral, Sparkle, and Monologue are all great!")
        assert len(result) == 4


class TestSentimentAnalyzer:
    """Tests for SentimentAnalyzer cog."""

    @pytest.mark.asyncio
    async def test_ignores_bot_messages(self, mock_bot, mock_database):
        """Test that bot messages are ignored."""
        with patch("bot.cogs.sentiment.anthropic.Anthropic"):
            analyzer = SentimentAnalyzer(mock_bot, mock_database)

            message = MockMessage(content="Cora is great!", author_bot=True)

            await analyzer.on_message(message)

            assert len(analyzer.message_queue) == 0

    @pytest.mark.asyncio
    async def test_ignores_dms(self, mock_bot, mock_database):
        """Test that DMs are ignored."""
        with patch("bot.cogs.sentiment.anthropic.Anthropic"):
            analyzer = SentimentAnalyzer(mock_bot, mock_database)

            message = MockMessage(content="Cora is great!")
            message.guild = None

            await analyzer.on_message(message)

            assert len(analyzer.message_queue) == 0

    @pytest.mark.asyncio
    async def test_ignores_empty_messages(self, mock_bot, mock_database):
        """Test that empty messages are ignored."""
        with patch("bot.cogs.sentiment.anthropic.Anthropic"):
            analyzer = SentimentAnalyzer(mock_bot, mock_database)

            message = MockMessage(content="")

            await analyzer.on_message(message)

            assert len(analyzer.message_queue) == 0

    @pytest.mark.asyncio
    async def test_ignores_unmonitored_channels(self, mock_bot, mock_database):
        """Test that messages from unmonitored channels are ignored."""
        with patch("bot.cogs.sentiment.anthropic.Anthropic"):
            analyzer = SentimentAnalyzer(mock_bot, mock_database)

            # Use a channel ID that's not in the monitored list
            message = MockMessage(content="Cora is great!", channel_id=999999999)

            await analyzer.on_message(message)

            assert len(analyzer.message_queue) == 0

    @pytest.mark.asyncio
    async def test_ignores_messages_without_app_mention(self, mock_bot, mock_database):
        """Test that messages not mentioning monitored apps are ignored."""
        with patch("bot.cogs.sentiment.anthropic.Anthropic"):
            analyzer = SentimentAnalyzer(mock_bot, mock_database)

            # Message in monitored channel but doesn't mention any app
            message = MockMessage(content="This is just a regular message")

            await analyzer.on_message(message)

            assert len(analyzer.message_queue) == 0

    @pytest.mark.asyncio
    async def test_queues_app_feedback_messages(self, mock_bot, mock_database):
        """Test that messages mentioning apps in monitored channels are queued."""
        with patch("bot.cogs.sentiment.anthropic.Anthropic"):
            analyzer = SentimentAnalyzer(mock_bot, mock_database)

            message = MockMessage(content="Cora keeps crashing when I try to export")

            await analyzer.on_message(message)

            assert len(analyzer.message_queue) == 1
            queued = analyzer.message_queue[0]
            assert queued["content"] == "Cora keeps crashing when I try to export"
            assert "cora" in queued["apps_mentioned"]

    @pytest.mark.asyncio
    async def test_captures_multiple_apps(self, mock_bot, mock_database):
        """Test that multiple app mentions are captured."""
        with patch("bot.cogs.sentiment.anthropic.Anthropic"):
            analyzer = SentimentAnalyzer(mock_bot, mock_database)

            message = MockMessage(content="I use Spiral and Sparkle every day!")

            await analyzer.on_message(message)

            assert len(analyzer.message_queue) == 1
            queued = analyzer.message_queue[0]
            assert "spiral" in queued["apps_mentioned"]
            assert "sparkle" in queued["apps_mentioned"]

    @pytest.mark.asyncio
    async def test_truncates_long_messages(self, mock_bot, mock_database):
        """Test that long messages are truncated to 1000 chars."""
        with patch("bot.cogs.sentiment.anthropic.Anthropic"):
            analyzer = SentimentAnalyzer(mock_bot, mock_database)

            # Create message longer than 1000 chars with app mention
            long_content = "Cora " + "x" * 2000
            message = MockMessage(content=long_content)

            await analyzer.on_message(message)

            queued = analyzer.message_queue[0]
            assert len(queued["content"]) == 1000

    @pytest.mark.asyncio
    async def test_analyze_batch_success(self, mock_bot, mock_database, mock_anthropic_client):
        """Test successful batch analysis."""
        with patch("bot.cogs.sentiment.anthropic.Anthropic", return_value=mock_anthropic_client):
            analyzer = SentimentAnalyzer(mock_bot, mock_database)
            analyzer.client = mock_anthropic_client

            batch = [{
                "guild_id": "123",
                "channel_id": "456",
                "channel_name": "discussions",
                "message_id": "789",
                "author_id": "111",
                "author_name": "TestUser",
                "content": "Cora keeps crashing!",
                "apps_mentioned": ["cora"],
                "timestamp": datetime.utcnow(),
                "jump_url": "https://discord.com/channels/123/456/789"
            }]

            results = await analyzer._analyze_batch(batch)

            assert len(results) == 1
            assert results[0].sentiment == "negative"
            assert results[0].feedback_type == "bug"
            assert results[0].actionable == True
            assert results[0].apps_mentioned == "cora"

    def test_parse_various_feedback_responses(self):
        """Test parsing different feedback response formats."""
        test_cases = [
            (
                '{"sentiment": "negative", "feedback_type": "bug", "summary": "App crashes", "actionable": true}',
                "negative", "bug", True
            ),
            (
                '{"sentiment": "positive", "feedback_type": "praise", "summary": "Love the app", "actionable": false}',
                "positive", "praise", False
            ),
            (
                '{"sentiment": "neutral", "feedback_type": "feature_request", "summary": "Wants dark mode", "actionable": true}',
                "neutral", "feature_request", True
            ),
        ]

        for response_text, expected_sentiment, expected_type, expected_actionable in test_cases:
            data = json.loads(response_text)
            assert data["sentiment"] == expected_sentiment
            assert data["feedback_type"] == expected_type
            assert data["actionable"] == expected_actionable


class TestMonitoredChannels:
    """Tests for channel monitoring configuration."""

    def test_monitored_channels_exist(self):
        """Verify monitored channel IDs are configured."""
        assert len(Config.MONITORED_CHANNEL_IDS) == 9

    def test_specific_channels_monitored(self):
        """Verify specific channel IDs are in the monitored set."""
        assert "1019678288618205294" in Config.MONITORED_CHANNEL_IDS  # discussions
        assert "821856844137758730" in Config.MONITORED_CHANNEL_IDS   # main
        assert "1395804083801165895" in Config.MONITORED_CHANNEL_IDS  # Core-public

    def test_monitored_apps_configured(self):
        """Verify monitored apps are configured."""
        assert "cora" in Config.MONITORED_APPS
        assert "spiral" in Config.MONITORED_APPS
        assert "sparkle" in Config.MONITORED_APPS
        assert "monologue" in Config.MONITORED_APPS
