"""
FAQ knowledge base for Aura AI.

HOW TO EXPAND
-------------
Add a new dictionary to ``FAQ_DATA``:

    {
        "category": "Shipping Address",
        "answer": "You can change your address from Account > Addresses.",
        "questions": [
            "How do I change my shipping address?",
            "Can I update my delivery address?",
        ],
    }

Every phrasing in ``questions`` is indexed separately, so the more natural
ways people might ask the same thing you list, the better the matching gets.
"""

FALLBACK_ANSWER = (
    "I'm sorry, I couldn't find an answer to that. "
    "Try asking about passwords, orders, payments, delivery, cancellations, "
    "refunds, or exchanges."
)

FAQ_DATA = [
    {
        "category": "Password",
        "answer": (
            "You can reset your password by clicking on the 'Forgot Password' "
            "option on the login page."
        ),
        "questions": [
            "How can I reset my password?",
            "I forgot my password",
            "How do I reset my login password?",
            "I cannot remember my password",
        ],
    },
    {
        "category": "Order Tracking",
        "answer": "You can track your order from the 'My Orders' section of your account.",
        "questions": [
            "Where is my package?",
            "How can I track my order?",
            "Where is my order?",
            "Track my package",
        ],
    },
    {
        "category": "Payment",
        "answer": "We accept credit cards, debit cards, and online bank payments.",
        "questions": [
            "What payment methods do you accept?",
            "How can I pay?",
            "What payment options are available?",
        ],
    },
    {
        "category": "Delivery",
        "answer": "Standard delivery usually takes 3 to 5 business days.",
        "questions": [
            "How long does delivery take?",
            "When will my order arrive?",
            "How many days does shipping take?",
        ],
    },
    {
        "category": "Cancellation",
        "answer": "Yes, you can cancel your order before it is shipped.",
        "questions": [
            "Can I cancel my order?",
            "I want to cancel my order",
            "How can I cancel my order?",
        ],
    },
    {
        "category": "Refund",
        "answer": "You will receive your refund within 24 hours.",
        "questions": [
            "Can I get a refund?",
            "How do I get my money back?",
            "What is the refund policy?",
        ],
    },
    {
        "category": "Exchange",
        "answer": "Sorry, we don't have an exchange policy.",
        "questions": [
            "Can I exchange my product?",
            "Do you offer exchanges?",
            "Is product exchange available?",
        ],
    },
]
