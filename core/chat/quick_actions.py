from core.chat.schemas import ChatContext, ChatMode, QuickAction


def build_quick_actions(
    mode: ChatMode,
    user_role: str,
    context: ChatContext,
    *,
    has_questions: bool = False,
) -> list[QuickAction]:
    actions = [
        QuickAction(id="ask_more", label="💬 Спросить ещё", action_type="focus_input"),
    ]
    if has_questions:
        actions.insert(
            0,
            QuickAction(id="copy_questions", label="📋 Скопировать вопросы", action_type="copy_questions"),
        )
    if context.lead_id:
        actions.insert(
            0,
            QuickAction(id="open_analytics", label="🔍 Запустить аналитику", action_type="open_analytics"),
        )
    if user_role in {"rop", "admin"} and context.lead_id:
        actions.append(
            QuickAction(id="export_lead", label="📤 Экспорт", action_type="export_lead"),
        )
    return actions
