from core.chat.schemas import ChatContext, ChatMode


BASE_SUGGESTIONS: dict[str, dict[str, list[str]]] = {
    ChatMode.HELP.value: {
        "rop": [
            "Как добавить нового менеджера?",
            "Как экспортировать список лидов?",
            "Почему не работает кнопка «Аналитика»?",
        ],
        "manager": [
            "Как сменить пароль?",
            "Как экспортировать мои лиды?",
            "Что делать, если поиск пустой?",
        ],
        "admin": [
            "Как настроить роли пользователей?",
            "Как обновить базу знаний?",
            "Где посмотреть логи системы?",
        ],
    },
    ChatMode.SEARCH.value: {
        "rop": [
            "Что означает скоринг 65?",
            "Как отфильтровать только монтажников?",
            "Как интерпретировать конверсию по сегментам?",
        ],
        "manager": [
            "Какие вопросы задать монтажнику?",
            "Как отработать возражение «дорого»?",
            "Почему компания не попала в выдачу?",
        ],
        "admin": [
            "Как настроить фильтры поиска?",
            "Что такое тёплый лид?",
            "Как запустить пакетную аналитику?",
        ],
    },
}


def build_suggestions(
    mode: ChatMode,
    user_role: str,
    context: ChatContext,
) -> list[str]:
    role_key = user_role if user_role in BASE_SUGGESTIONS[mode.value] else "manager"
    suggestions = list(BASE_SUGGESTIONS[mode.value].get(role_key, BASE_SUGGESTIONS[mode.value]["manager"]))

    if context.lead_id and context.score is not None:
        if context.score < 50:
            suggestions.insert(0, "Почему скоринг низкий?")
        elif context.score < 80:
            suggestions.insert(0, "Какие вопросы задать этому клиенту?")
        else:
            suggestions.insert(0, "Как подготовиться к звонку по этому лиду?")

    if context.segment == "installer":
        suggestions.append("Как отработать возражение «дорого» у монтажников?")
    if context.page == "analytics":
        suggestions.insert(0, "Как интерпретировать метрики аналитики?")
    if context.page == "search":
        suggestions.insert(0, "Какие ОКВЭД подходят для монтажников?")

    seen: set[str] = set()
    unique: list[str] = []
    for item in suggestions:
        if item not in seen:
            seen.add(item)
            unique.append(item)
    return unique[:5]
