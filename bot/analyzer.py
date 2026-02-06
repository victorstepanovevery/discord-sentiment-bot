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
[See rules below]

RULES:

1. URGENT: Surface ANY complaint, bug report, or frustration. Even one-offs. We don't want to miss these.

2. FEEDBACK: Include GENUINE product feedback, feature requests, AND beta access requests. Use judgment to filter out:
   - Jokes or sarcasm
   - Casual chatter / small talk
   - Questions that aren't really requests
   - Off-topic conversations
   - Messages that mention the app but aren't actionable feedback
   Ask yourself: "Would a product manager actually want to act on this?" If no, skip it.

3. OTHER: This section should ONLY exist if there's something genuinely interesting to share. Write an engaging paragraph with specific quotes that reveal interesting insights about our users or community.

   GOOD example: "Interesting discussion about productivity workflows — one user shared 'I've been using Spiral for my morning routine and it's completely changed how I start my day' while another asked about integrating with Notion. There's clear interest in how our apps fit into broader productivity systems."

   BAD examples (DO NOT write these):
   - "Someone shared a tweet" (who cares)
   - "One conversation moved to DMs" (not meaningful)
   - "A few thank you messages" (generic)
   - "Some off-topic banter" (filler)

   If you can't write something genuinely interesting with meaningful quotes, just write:
   "Nothing super important. Check back later."

4. For URGENT and FEEDBACK: If nothing fits, write "Nothing notable today."

5. Include Discord message links (labeled "Message link") for URGENT and FEEDBACK items only. NO links in OTHER."""

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
