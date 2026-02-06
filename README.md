# Discord App Feedback Monitor

A Discord bot that monitors specific channels for mentions of your apps (Cora, Spiral, Sparkle, Monologue), analyzes feedback using Claude AI, and posts daily summaries at 8 AM ET.

## Features

- **Focused App Monitoring**: Only captures messages that mention your apps (Cora, Spiral, Sparkle, Monologue)
- **Smart Feedback Analysis**: Uses Claude Haiku to classify feedback type (bug, feature request, praise, complaint)
- **Sentiment Detection**: Identifies positive, negative, neutral, and mixed sentiment
- **Daily Summaries at 8 AM ET**: Automated reports with breakdowns by app, type, and sentiment
- **Actionable Items Highlighted**: Bugs and feature requests surfaced for quick attention
- **Jump Links**: Direct links to original messages for context

## Requirements

- Python 3.11+
- Discord Bot Token (with MESSAGE_CONTENT intent enabled)
- Anthropic API Key

## Quick Start

### 1. Clone and Install

```bash
cd discord-sentiment-bot

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"
```

### 2. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit with your credentials
nano .env
```

Required environment variables:
```
DISCORD_BOT_TOKEN=your_discord_bot_token
ANTHROPIC_API_KEY=your_anthropic_api_key
```

### 3. Create Discord Bot

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application
3. Go to "Bot" section and create a bot
4. **Enable MESSAGE CONTENT INTENT** (required!)
5. Copy the bot token to your `.env` file
6. Go to "OAuth2" > "URL Generator"
7. Select scopes: `bot`, `applications.commands`
8. Select permissions: `Send Messages`, `Embed Links`, `Read Message History`
9. Use the generated URL to invite the bot to your server

### 4. Run the Bot

```bash
# Run directly
python3 -m bot.main

# Or using the installed command
sentiment-bot
```

## Monitored Channels

The bot monitors these specific channels (configured in `bot/config.py`):

| Channel ID | Name |
|------------|------|
| 1019678288618205294 | discussions |
| 821856844137758730 | main |
| 797477569195671592 | random |
| 1389667062569242644 | studio |
| 1395804083801165895 | Core-public |
| 1393267393928630473 | Monologue-public |
| 1395804228336750672 | Sparkle-public |
| 1395804148825329777 | Spiral-public |
| 1466104194644836620 | Proof-public |

To modify channels, edit `MONITORED_CHANNEL_IDS` in `bot/config.py`.

## Monitored Apps

The bot captures messages mentioning:
- **Cora** 🤖
- **Spiral** 🌀
- **Sparkle** ✨
- **Monologue** 📝

To add or remove apps, edit `MONITORED_APPS` in `bot/config.py`.

## Slash Commands

| Command | Description |
|---------|-------------|
| `/setchannel #channel` | Set where daily summaries are posted |
| `/feedbacknow [#channel]` | Manually trigger a summary (Admin) |
| `/recentfeedback [app] [hours]` | View recent feedback filtered by app |

## How It Works

1. **Message Capture**: Bot listens to monitored channels and captures messages mentioning your apps
2. **Hourly Processing**: Every hour, captured messages are analyzed using Claude Haiku
3. **Feedback Classification**: Claude identifies:
   - **Sentiment**: positive, negative, neutral, mixed
   - **Type**: bug, feature_request, praise, complaint, question, general
   - **Actionable**: whether it needs attention (bugs and feature requests)
4. **Daily Summary**: At 8 AM ET, posts a comprehensive summary with:
   - Total feedback count
   - Breakdown by app
   - Breakdown by feedback type
   - Sentiment distribution
   - Actionable items list with jump links
   - Negative feedback alerts

## Daily Summary

The 8 AM ET summary includes:

- **📊 Main Summary**: Total mentions, breakdown by app, type, and sentiment
- **⚡ Actionable Feedback**: Bugs and feature requests with jump links
- **⚠️ Negative Feedback**: Complaints and concerns to address

## Architecture

```
discord-sentiment-bot/
├── bot/
│   ├── __init__.py
│   ├── main.py           # Entry point
│   ├── config.py         # Channel IDs, app names, settings
│   ├── database.py       # SQLite data layer (FeedbackRecord)
│   └── cogs/
│       ├── sentiment.py  # Message listener & Claude API
│       └── scheduler.py  # 8 AM ET summary scheduler
├── tests/
│   ├── test_database.py
│   └── test_sentiment.py
├── .env.example
├── pyproject.toml
└── README.md
```

## Cost Estimation

Using Claude Haiku for feedback analysis:
- ~100 tokens per message analysis
- At $1/M input tokens: **~$1 per 10,000 feedback messages**
- Hourly batch processing minimizes API calls

## Development

### Run Tests

```bash
pytest tests/ -v
```

### Run with Coverage

```bash
pytest tests/ -v --cov=bot --cov-report=term-missing
```

### Linting

```bash
ruff check bot/ tests/
ruff format bot/ tests/
```

## Deployment

### Systemd Service (Linux VPS)

Create `/etc/systemd/system/feedback-bot.service`:

```ini
[Unit]
Description=Discord App Feedback Monitor
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/discord-sentiment-bot
Environment=PATH=/path/to/discord-sentiment-bot/.venv/bin
ExecStart=/path/to/discord-sentiment-bot/.venv/bin/python -m bot.main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable feedback-bot
sudo systemctl start feedback-bot
```

## Troubleshooting

### Bot not capturing messages
- Ensure MESSAGE_CONTENT intent is enabled in Discord Developer Portal
- Verify channel IDs in `bot/config.py` are correct
- Messages must mention one of the monitored apps (Cora, Spiral, Sparkle, Monologue)

### Slash commands not appearing
- Wait a few minutes for Discord to sync commands
- Try kicking and re-inviting the bot

### No daily summary posted
- Use `/setchannel #channel` to configure where summaries go
- Check bot has permission to post embeds in that channel

### Rate limiting
- The bot automatically handles Claude API rate limits with exponential backoff
- Batch processing runs hourly to minimize API calls

## License

MIT License - see LICENSE file for details.
