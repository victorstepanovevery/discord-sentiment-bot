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

**2. 💬 FEEDBACK** (genuine feature requests, product suggestions, OR requests for beta access)
- [Request/suggestion]
  > "[Quote]" — @username in #channel
  > [Message link](url)

**3. ✨ OTHER**
Nothing super important.

[Write a brief paragraph summarizing what else was in the messages. Include actual quotes from messages to show what was discussed, but do NOT include usernames or links since this isn't actionable. Write it like a casual brief/report of the vibe and topics. Example: "Mostly casual chat today — someone asked 'when is Android coming?' while comparing to other apps, a few 'thanks!' messages, and some off-topic banter about weekend plans."]

RULES:

1. URGENT: Surface ANY complaint, bug report, or frustration. Even one-offs. We don't want to miss these.

2. FEEDBACK: Include GENUINE product feedback, feature requests, AND beta access requests. Use judgment to filter out:
   - Jokes or sarcasm
   - Casual chatter / small talk
   - Questions that aren't really requests
   - Off-topic conversations
   - Messages that mention the app but aren't actionable feedback
   Ask yourself: "Would a product manager actually want to act on this?" If no, skip it.

3. OTHER: Always write "Nothing super important." then a brief paragraph with quotes showing what was discussed. NO usernames, NO links. Just the vibes and topics.

4. For URGENT and FEEDBACK: If nothing fits, write "Nothing notable today."

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
