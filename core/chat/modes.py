from core.chat.schemas import ChatContext, ChatMode
from core.rag.models import DocumentCategory


def resolve_categories(mode: ChatMode, query: str, context: ChatContext) -> list[DocumentCategory]:
    lower = query.lower()

    if mode == ChatMode.HELP:
        categories = [DocumentCategory.SYSTEM]
        if any(token in lower for token in ("доставк", "логистик", "гарант", "сервис")):
            categories.append(DocumentCategory.COMPANY)
        return categories

    categories: list[DocumentCategory] = []
    if any(
        token in lower
        for token in ("как добавить", "пароль", "роль", "экспорт", "настройк", "интерфейс", "кнопк")
    ):
        categories.append(DocumentCategory.SYSTEM)

    if any(
        token in lower
        for token in ("вентилятор", "пву", "продукт", "овик", "воздуховод", "автоматик", "клапан")
    ):
        categories.extend(
            [DocumentCategory.PRODUCT, DocumentCategory.SALES, DocumentCategory.SEGMENTS]
        )

    if any(
        token in lower
        for token in ("вопрос", "возражен", "скрипт", "квалифик", "звонок", "клиент", "лид")
    ):
        categories.extend(
            [DocumentCategory.SALES, DocumentCategory.SEGMENTS]
        )

    if context.lead_id or context.segment:
        if DocumentCategory.SEGMENTS not in categories:
            categories.append(DocumentCategory.SEGMENTS)
        if DocumentCategory.SALES not in categories:
            categories.append(DocumentCategory.SALES)

    if not categories:
        categories = [
            DocumentCategory.SYSTEM,
            DocumentCategory.SALES,
            DocumentCategory.SEGMENTS,
        ]
    return list(dict.fromkeys(categories))
