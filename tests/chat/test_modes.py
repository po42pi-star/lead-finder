from core.chat.modes import resolve_categories
from core.chat.schemas import ChatContext, ChatMode
from core.rag.models import DocumentCategory


def test_help_mode_uses_system():
    categories = resolve_categories(ChatMode.HELP, "Как сменить пароль?", ChatContext())
    assert DocumentCategory.SYSTEM in categories


def test_search_mode_with_lead_context():
    ctx = ChatContext(segment="installer", lead_id="00000000-0000-0000-0000-000000000001")
    categories = resolve_categories(ChatMode.SEARCH, "Какие вопросы задать?", ctx)
    assert DocumentCategory.SEGMENTS in categories
    assert DocumentCategory.SALES in categories
