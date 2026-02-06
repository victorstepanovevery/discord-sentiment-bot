"""Feedback analyzer using Claude API."""
import anthropic
import logging
from bot.config import Config

logger = logging.getLogger(__name__)

# Team members to exclude (they're replying to users, not providing feedback)
TEAM_MEMBERS = {"naveen_z", "kieran_2", "yash49494", "marcusevery"}


class FeedbackAnalyzer:
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=Config.ANTHROPIC_API_KEY)

    async def analyze_batch(self, messages: list[dict]) -> str:
        if not messages:
            return "Nothing new found. Check back later."

        # Filter out team member messages
        filtered_messages = [
            msg for msg in messages
            if msg['author'].split('#')[0].lower() not in TEAM_MEMBERS
        ]

        if not filtered_messages:
            return "Only team member messages found. No user feedback to analyze."

        formatted = []
        for msg in filtered_messages:
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
  > [Message link](url)

**2. 💬 FEEDBACK** (genuine feature requests or product suggestions)
- [Request/suggestion]
  > "[Quote]" — @username in #channel
  > [Message link](url)

**3. ✨ OTHER** (anything else worth noting)
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

3. OTHER: Anything noteworthy that doesn't fit above categories.

4. If a category has nothing meaningful, write "Nothing notable today" AND then briefly summarize what WAS in the messages (without links) so we know what was analyzed. For example: "Nothing notable today. Messages were mostly casual greetings, thank-you's, and general chat about unrelated topics."

5. Include Discord message links (labeled "Message link") for URGENT and FEEDBACK items only."""

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
