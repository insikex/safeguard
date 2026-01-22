"""
CAPTCHA Service
===============
Generates various types of CAPTCHA challenges for verification.
"""

import random
import string
from dataclasses import dataclass
from typing import List, Tuple, Optional
from enum import Enum


class CaptchaType(Enum):
    """Types of CAPTCHA challenges"""
    BUTTON = "button"
    MATH = "math"
    EMOJI = "emoji"
    PORTAL = "portal"


@dataclass
class CaptchaChallenge:
    """CAPTCHA challenge data"""
    captcha_type: CaptchaType
    question: str
    answer: str
    options: Optional[List[str]] = None  # For emoji/button options


class CaptchaService:
    """Service for generating CAPTCHA challenges"""
    
    # Emoji sets for emoji CAPTCHA
    EMOJI_SETS = [
        ("🐶", "Anjing", "Dog"),
        ("🐱", "Kucing", "Cat"),
        ("🐭", "Tikus", "Mouse"),
        ("🐰", "Kelinci", "Rabbit"),
        ("🦊", "Rubah", "Fox"),
        ("🐻", "Beruang", "Bear"),
        ("🐼", "Panda", "Panda"),
        ("🐨", "Koala", "Koala"),
        ("🦁", "Singa", "Lion"),
        ("🐯", "Harimau", "Tiger"),
        ("🐮", "Sapi", "Cow"),
        ("🐷", "Babi", "Pig"),
        ("🐸", "Kodok", "Frog"),
        ("🐵", "Monyet", "Monkey"),
        ("🦄", "Unicorn", "Unicorn"),
        ("🐝", "Lebah", "Bee"),
        ("🦋", "Kupu-kupu", "Butterfly"),
        ("🐢", "Kura-kura", "Turtle"),
        ("🐍", "Ular", "Snake"),
        ("🦎", "Kadal", "Lizard"),
        ("🦀", "Kepiting", "Crab"),
        ("🐙", "Gurita", "Octopus"),
        ("🦈", "Hiu", "Shark"),
        ("🐬", "Lumba-lumba", "Dolphin"),
        ("🐳", "Paus", "Whale"),
    ]
    
    # Fruit emojis
    FRUIT_EMOJIS = [
        ("🍎", "Apel", "Apple"),
        ("🍊", "Jeruk", "Orange"),
        ("🍋", "Lemon", "Lemon"),
        ("🍌", "Pisang", "Banana"),
        ("🍉", "Semangka", "Watermelon"),
        ("🍇", "Anggur", "Grapes"),
        ("🍓", "Stroberi", "Strawberry"),
        ("🍑", "Persik", "Peach"),
        ("🍍", "Nanas", "Pineapple"),
        ("🥭", "Mangga", "Mango"),
        ("🍒", "Ceri", "Cherry"),
        ("🥝", "Kiwi", "Kiwi"),
    ]
    
    # Object emojis
    OBJECT_EMOJIS = [
        ("⭐", "Bintang", "Star"),
        ("❤️", "Hati", "Heart"),
        ("🔥", "Api", "Fire"),
        ("💧", "Air", "Water"),
        ("🌈", "Pelangi", "Rainbow"),
        ("☀️", "Matahari", "Sun"),
        ("🌙", "Bulan", "Moon"),
        ("⚡", "Petir", "Lightning"),
        ("🎵", "Musik", "Music"),
        ("🎈", "Balon", "Balloon"),
    ]
    
    # Math operators
    OPERATORS = [
        ("+", lambda a, b: a + b),
        ("-", lambda a, b: a - b),
        ("×", lambda a, b: a * b),
    ]
    
    @classmethod
    def generate_button_captcha(cls) -> CaptchaChallenge:
        """Generate simple button CAPTCHA"""
        return CaptchaChallenge(
            captcha_type=CaptchaType.BUTTON,
            question="",
            answer="verify",
            options=None
        )
    
    @classmethod
    def generate_math_captcha(cls, difficulty: str = "easy") -> CaptchaChallenge:
        """
        Generate math CAPTCHA
        
        Args:
            difficulty: 'easy' (single digit), 'medium' (double digit), 'hard' (with multiplication)
        """
        if difficulty == "easy":
            num1 = random.randint(1, 10)
            num2 = random.randint(1, 10)
            op_symbol, op_func = random.choice(cls.OPERATORS[:2])  # Only + and -
        elif difficulty == "medium":
            num1 = random.randint(10, 50)
            num2 = random.randint(1, 20)
            op_symbol, op_func = random.choice(cls.OPERATORS[:2])
        else:  # hard
            num1 = random.randint(2, 12)
            num2 = random.randint(2, 12)
            op_symbol, op_func = random.choice(cls.OPERATORS)
        
        # Ensure no negative results for subtraction
        if op_symbol == "-" and num2 > num1:
            num1, num2 = num2, num1
        
        answer = op_func(num1, num2)
        
        return CaptchaChallenge(
            captcha_type=CaptchaType.MATH,
            question=f"{num1} {op_symbol} {num2}",
            answer=str(answer),
            options=cls._generate_math_options(answer)
        )
    
    @classmethod
    def _generate_math_options(cls, correct_answer: int) -> List[str]:
        """Generate multiple choice options for math CAPTCHA"""
        options = [str(correct_answer)]
        
        # Generate wrong answers
        while len(options) < 4:
            # Generate plausible wrong answers
            offset = random.randint(1, 5) * random.choice([-1, 1])
            wrong = correct_answer + offset
            
            if str(wrong) not in options and wrong >= 0:
                options.append(str(wrong))
        
        random.shuffle(options)
        return options
    
    @classmethod
    def generate_emoji_captcha(cls) -> CaptchaChallenge:
        """Generate emoji selection CAPTCHA"""
        # Choose emoji set
        emoji_set = random.choice([cls.EMOJI_SETS, cls.FRUIT_EMOJIS, cls.OBJECT_EMOJIS])
        
        # Select correct emoji and some wrong ones
        selected = random.sample(emoji_set, min(4, len(emoji_set)))
        correct = selected[0]
        
        # Create options (just emojis)
        options = [item[0] for item in selected]
        random.shuffle(options)
        
        return CaptchaChallenge(
            captcha_type=CaptchaType.EMOJI,
            question=correct[0],  # The emoji to find
            answer=correct[0],    # The correct emoji
            options=options       # All emoji options
        )
    
    @classmethod
    def generate_portal_captcha(cls) -> CaptchaChallenge:
        """Generate portal verification token"""
        # Generate unique token
        token = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
        
        return CaptchaChallenge(
            captcha_type=CaptchaType.PORTAL,
            question="",
            answer=token,
            options=None
        )
    
    @classmethod
    def generate(cls, captcha_type: str = "button", **kwargs) -> CaptchaChallenge:
        """
        Generate CAPTCHA based on type
        
        Args:
            captcha_type: 'button', 'math', 'emoji', or 'portal'
            **kwargs: Additional arguments for specific captcha types
        """
        if captcha_type == "button":
            return cls.generate_button_captcha()
        elif captcha_type == "math":
            return cls.generate_math_captcha(kwargs.get("difficulty", "easy"))
        elif captcha_type == "emoji":
            return cls.generate_emoji_captcha()
        elif captcha_type == "portal":
            return cls.generate_portal_captcha()
        else:
            return cls.generate_button_captcha()
    
    @classmethod
    def verify(cls, challenge: CaptchaChallenge, user_answer: str) -> bool:
        """Verify user's answer against challenge"""
        if challenge.captcha_type == CaptchaType.BUTTON:
            return user_answer == "verify"
        else:
            return str(user_answer).strip().lower() == str(challenge.answer).strip().lower()


# Global instance
captcha_service = CaptchaService()
