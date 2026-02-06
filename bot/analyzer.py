"""Feedback analyzer using Claude API."""
import anthropic
import logging
from bot.config import Config

logger = logging.getLogger(__name__)


class FeedbackAnalyzer:
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=Config.ANTHROPIC_API_KEY)

    async def analyze_batch(self, messages: list[dict]) -> str:
        if not messages:
            return "Nothing new found. Check back later."

        formatted = []
        for msg in messages:
            jump_url = msg.get('jump_url', '')
            formatted.append(f"[#{msg['channel']}] {msg['author']} ({jump_url}): {msg['content']}")

        messages_text = "\n".join(formatted)

        prompt = f"""Analyze these Discord messages from users of our apps: Cora, Spiral, Sparkle, and Monologue.

Messages:
{messages_text}

Provide a summary in this format:

**1. 🚨 URGENT** (any complaints, bugs, crashes, frustrated users - surface ALL of these)
- [Issue description]
  > "[Quote]" — @username in #channel
  > [Link](url)

**2. 💬 FEEDBACK** (genuine feature requests or product suggestions)
- [Request/suggestion]
  > "[Quote]" — @username in #channel
  > [Link](url)

**3. ✨ POSITIVE** (genuine praise)
- [Summary]

RULES:

1. URGENT: Surface ANY complaint, bug report, or frustration. Even one-offs. We don't want to miss these.

2. FEEDBACK: Only include GENUINE product feedback or feature requests. Use judgment to filter out:
   - Jokes or sarcasm
   - Casual chatter / small talk
   - Questions that aren't really requests
   - Off-topic conversations
   - Messages that mention the app but aren't actionable feedback
   Ask yourself: "Would a product manager actually want to act on this?" If no, skip it.

3. POSITIVE: Only include genuine praise. Skip polite acknowledgments or casual "thanks".

4. If a category has nothing meaningful, write "Nothing notable today" — this is PREFERRED over surfacing noise.

5. Include Discord message links for URGENT and FEEDBACK items."""

        try:
            response = self.client.messages.create(
                model=Config.CLAUDE_MODEL,
                max_tokens=1500,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text
        except Exception as e:
            logger.error(f"Error analyzing: {e}")
            return f"Error: {str(e)}"
