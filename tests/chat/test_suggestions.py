from core.chat.schemas import ChatContext, ChatMode
from core.chat.suggestions import build_suggestions


def test_low_score_suggestion():
    ctx = ChatContext(score=42, lead_id="00000000-0000-0000-0000-000000000001")
    items = build_suggestions(ChatMode.SEARCH, "manager", ctx)
    assert any("скоринг" in item.lower() for item in items)
