import random
import uuid
from typing import Dict


class MockLLM:
    """Mock LLM client for testing"""

    def __init__(self):
        self.responses = [
            "Skvělá otázka! Rád vám na to odpovím...",
            "To je zajímavé téma. Mohu říct, že...",
            "Podle dostupných informací mohu potvrdit, že...",
            "Rozumím vaší otázce. Odpověď je...",
            "To je komplexní záležitost. Pokusím se to vysvětlit...",
        ]

        self.follow_ups = [
            "Máte nějakou další otázku?",
            "Potřebujete něco upřesnit?",
            "Mohu vám s něčím dalším pomoci?",
            "Je to jasnější?",
            "Chcete vědět víc?",
        ]

    def generate_response(self, message: str, user_email: str) -> str:
        """Generate mock LLM response"""

        # Simple keyword-based responses for demo
        message_lower = message.lower()

        if "ahoj" in message_lower or "hello" in message_lower or "hi" in message_lower:
            return f"Ahoj! Jsem mock LLM asistent. Jak vám mohu pomoci, {user_email}?"

        if "jak se máš" in message_lower or "how are you" in message_lower:
            return "Jako AI model nemám pocity, ale děkuji za optání! Jak vám mohu pomoci?"

        if "token" in message_lower or "auth" in message_lower:
            return "Vidím, že se ptáte na tokeny. Váš access token funguje správně, proto můžete vidět tuto zprávu!"

        if "?" in message:
            # Question
            base = random.choice(self.responses)
            follow = random.choice(self.follow_ups)
            return f"{base} (Mock odpověď na: '{message[:50]}...') {follow}"
        else:
            # Statement
            return f"Rozumím. Zaznamenal jsem: '{message[:50]}...' Mohu s něčím pomoci?"

    def generate_conversation_id(self) -> str:
        """Generate unique conversation ID"""
        return str(uuid.uuid4())
