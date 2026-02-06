"""Tests for the database layer."""

import pytest
from datetime import datetime, timedelta
from pathlib import Path
import tempfile

from bot.database import Database, FeedbackRecord


@pytest.fixture
async def database():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)

    db = Database(db_path)
    await db.connect()
    yield db
    await db.close()

    # Cleanup
    db_path.unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_feedback_record_insert(database):
    """Test inserting feedback records."""
    record = FeedbackRecord(
        guild_id="123456789",
        channel_id="111222333",
        channel_name="discussions",
        message_id="999888777",
        author_id="444555666",
        author_name="TestUser",
        content="Cora keeps crashing when I export!",
        apps_mentioned="cora",
        sentiment="negative",
        feedback_type="bug",
        summary="Export feature causing crashes",
        actionable=True,
        message_timestamp=datetime.utcnow(),
        jump_url="https://discord.com/channels/123/456/789"
    )

    record_id = await database.insert_feedback_record(record)
    assert record_id is not None
    assert record_id > 0


@pytest.mark.asyncio
async def test_feedback_record_upsert(database):
    """Test upserting feedback records (same message_id replaces)."""
    record1 = FeedbackRecord(
        guild_id="123456789",
        channel_id="111222333",
        channel_name="discussions",
        message_id="999888777",  # Same message ID
        author_id="444555666",
        author_name="TestUser",
        content="Original content",
        apps_mentioned="cora",
        sentiment="neutral",
        feedback_type="general",
        summary="Original summary",
        actionable=False,
        message_timestamp=datetime.utcnow(),
        jump_url="https://discord.com/channels/123/456/789"
    )

    await database.insert_feedback_record(record1)

    # Insert with same message_id should replace
    record2 = FeedbackRecord(
        guild_id="123456789",
        channel_id="111222333",
        channel_name="discussions",
        message_id="999888777",  # Same message ID
        author_id="444555666",
        author_name="TestUser",
        content="Updated content",
        apps_mentioned="cora",
        sentiment="negative",
        feedback_type="bug",
        summary="Updated summary",
        actionable=True,
        message_timestamp=datetime.utcnow(),
        jump_url="https://discord.com/channels/123/456/789"
    )

    await database.insert_feedback_record(record2)

    # Verify only one record exists and it's the updated one
    start_time = datetime.utcnow() - timedelta(hours=24)
    feedback = await database.get_feedback_since(start_time)
    assert len(feedback) == 1
    assert feedback[0]["content"] == "Updated content"
    assert feedback[0]["sentiment"] == "negative"


@pytest.mark.asyncio
async def test_get_feedback_since(database):
    """Test getting feedback since a given time."""
    now = datetime.utcnow()

    # Insert some records
    for i in range(5):
        record = FeedbackRecord(
            guild_id="123456789",
            channel_id="111222333",
            channel_name="discussions",
            message_id=str(1000 + i),
            author_id="444555666",
            author_name="TestUser",
            content=f"Testing Cora feature {i}",
            apps_mentioned="cora",
            sentiment="positive",
            feedback_type="praise",
            summary=f"Summary {i}",
            actionable=False,
            message_timestamp=now - timedelta(hours=1),
            jump_url=f"https://discord.com/channels/123/456/{1000 + i}"
        )
        await database.insert_feedback_record(record)

    # Get feedback from last 24 hours
    start_time = now - timedelta(hours=24)
    feedback = await database.get_feedback_since(start_time)
    assert len(feedback) == 5


@pytest.mark.asyncio
async def test_get_feedback_since_with_app_filter(database):
    """Test filtering feedback by app."""
    now = datetime.utcnow()

    # Insert records for different apps
    apps = ["cora", "spiral", "cora", "sparkle", "cora"]
    for i, app in enumerate(apps):
        record = FeedbackRecord(
            guild_id="123456789",
            channel_id="111222333",
            channel_name="discussions",
            message_id=str(2000 + i),
            author_id="444555666",
            author_name="TestUser",
            content=f"Testing {app}",
            apps_mentioned=app,
            sentiment="positive",
            feedback_type="praise",
            summary=f"{app} is great",
            actionable=False,
            message_timestamp=now - timedelta(hours=1),
            jump_url=f"https://discord.com/channels/123/456/{2000 + i}"
        )
        await database.insert_feedback_record(record)

    # Filter by cora
    start_time = now - timedelta(hours=24)
    cora_feedback = await database.get_feedback_since(start_time, "cora")
    assert len(cora_feedback) == 3

    # Filter by spiral
    spiral_feedback = await database.get_feedback_since(start_time, "spiral")
    assert len(spiral_feedback) == 1


@pytest.mark.asyncio
async def test_get_feedback_stats(database):
    """Test getting feedback statistics."""
    now = datetime.utcnow()

    # Insert records with various sentiments and types
    test_data = [
        ("cora", "positive", "praise", False),
        ("cora", "negative", "bug", True),
        ("spiral", "positive", "praise", False),
        ("spiral", "neutral", "feature_request", True),
        ("sparkle", "negative", "complaint", False),
    ]

    for i, (app, sentiment, ftype, actionable) in enumerate(test_data):
        record = FeedbackRecord(
            guild_id="123456789",
            channel_id="111222333",
            channel_name="discussions",
            message_id=str(3000 + i),
            author_id="444555666",
            author_name="TestUser",
            content=f"Testing {app}",
            apps_mentioned=app,
            sentiment=sentiment,
            feedback_type=ftype,
            summary=f"Summary for {app}",
            actionable=actionable,
            message_timestamp=now - timedelta(hours=1),
            jump_url=f"https://discord.com/channels/123/456/{3000 + i}"
        )
        await database.insert_feedback_record(record)

    # Get stats
    start_time = now - timedelta(hours=24)
    stats = await database.get_feedback_stats(start_time)

    # Check totals
    assert stats["total"] == 5
    assert stats["actionable_count"] == 2

    # Check by sentiment
    assert stats["by_sentiment"]["positive"] == 2
    assert stats["by_sentiment"]["negative"] == 2
    assert stats["by_sentiment"]["neutral"] == 1

    # Check by type
    assert stats["by_type"]["praise"] == 2
    assert stats["by_type"]["bug"] == 1
    assert stats["by_type"]["feature_request"] == 1
    assert stats["by_type"]["complaint"] == 1

    # Check by app
    assert stats["by_app"]["cora"] == 2
    assert stats["by_app"]["spiral"] == 2
    assert stats["by_app"]["sparkle"] == 1


@pytest.mark.asyncio
async def test_get_actionable_feedback(database):
    """Test getting actionable feedback items."""
    now = datetime.utcnow()

    # Insert mix of actionable and non-actionable
    test_data = [
        ("cora", "bug", True),
        ("cora", "praise", False),
        ("spiral", "feature_request", True),
        ("sparkle", "complaint", False),
        ("monologue", "bug", True),
    ]

    for i, (app, ftype, actionable) in enumerate(test_data):
        record = FeedbackRecord(
            guild_id="123456789",
            channel_id="111222333",
            channel_name="discussions",
            message_id=str(4000 + i),
            author_id="444555666",
            author_name="TestUser",
            content=f"Testing {app}",
            apps_mentioned=app,
            sentiment="negative" if actionable else "positive",
            feedback_type=ftype,
            summary=f"{ftype} for {app}",
            actionable=actionable,
            message_timestamp=now - timedelta(hours=1),
            jump_url=f"https://discord.com/channels/123/456/{4000 + i}"
        )
        await database.insert_feedback_record(record)

    # Get actionable feedback
    start_time = now - timedelta(hours=24)
    actionable = await database.get_actionable_feedback(start_time, limit=10)

    assert len(actionable) == 3
    for item in actionable:
        assert item["actionable"] == 1  # SQLite stores bool as int


@pytest.mark.asyncio
async def test_get_negative_feedback(database):
    """Test getting negative feedback."""
    now = datetime.utcnow()

    # Insert records with various sentiments
    sentiments = ["positive", "negative", "neutral", "negative", "mixed"]
    for i, sentiment in enumerate(sentiments):
        record = FeedbackRecord(
            guild_id="123456789",
            channel_id="111222333",
            channel_name="discussions",
            message_id=str(5000 + i),
            author_id="444555666",
            author_name="TestUser",
            content=f"Testing message {i}",
            apps_mentioned="cora",
            sentiment=sentiment,
            feedback_type="general",
            summary=f"Summary {i}",
            actionable=False,
            message_timestamp=now - timedelta(hours=1),
            jump_url=f"https://discord.com/channels/123/456/{5000 + i}"
        )
        await database.insert_feedback_record(record)

    # Get negative feedback (includes 'mixed')
    start_time = now - timedelta(hours=24)
    negative = await database.get_negative_feedback(start_time, limit=10)

    assert len(negative) == 3  # 2 negative + 1 mixed
    for item in negative:
        assert item["sentiment"] in ["negative", "mixed"]


@pytest.mark.asyncio
async def test_get_feedback_by_type(database):
    """Test getting feedback by type."""
    now = datetime.utcnow()

    # Insert records with various types
    types = ["bug", "bug", "feature_request", "praise", "bug"]
    for i, ftype in enumerate(types):
        record = FeedbackRecord(
            guild_id="123456789",
            channel_id="111222333",
            channel_name="discussions",
            message_id=str(6000 + i),
            author_id="444555666",
            author_name="TestUser",
            content=f"Testing message {i}",
            apps_mentioned="cora",
            sentiment="neutral",
            feedback_type=ftype,
            summary=f"Summary {i}",
            actionable=ftype == "bug",
            message_timestamp=now - timedelta(hours=1),
            jump_url=f"https://discord.com/channels/123/456/{6000 + i}"
        )
        await database.insert_feedback_record(record)

    # Get bugs
    start_time = now - timedelta(hours=24)
    bugs = await database.get_feedback_by_type(start_time, "bug", limit=10)

    assert len(bugs) == 3
    for item in bugs:
        assert item["feedback_type"] == "bug"


@pytest.mark.asyncio
async def test_multiple_apps_mentioned(database):
    """Test handling multiple apps in a single message."""
    now = datetime.utcnow()

    record = FeedbackRecord(
        guild_id="123456789",
        channel_id="111222333",
        channel_name="discussions",
        message_id="7000",
        author_id="444555666",
        author_name="TestUser",
        content="I use Cora, Spiral, and Sparkle every day!",
        apps_mentioned="cora,spiral,sparkle",
        sentiment="positive",
        feedback_type="praise",
        summary="User loves multiple apps",
        actionable=False,
        message_timestamp=now - timedelta(hours=1),
        jump_url="https://discord.com/channels/123/456/7000"
    )
    await database.insert_feedback_record(record)

    # Get stats - each app should be counted
    start_time = now - timedelta(hours=24)
    stats = await database.get_feedback_stats(start_time)

    assert stats["total"] == 1
    assert stats["by_app"]["cora"] == 1
    assert stats["by_app"]["spiral"] == 1
    assert stats["by_app"]["sparkle"] == 1
