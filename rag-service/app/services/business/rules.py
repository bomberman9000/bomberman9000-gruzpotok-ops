from __future__ import annotations

MIN_CLAIM_TEXT_LEN = 20
MIN_ROUTE_FIELD_LEN = 2


def validate_claim_review_input(claim_text: str) -> list[str]:
    t = (claim_text or "").strip()
    if len(t) < MIN_CLAIM_TEXT_LEN:
        return [
            f"Текст претензии слишком короткий (минимум ~{MIN_CLAIM_TEXT_LEN} значимых символов). "
            "Добавьте фабулу, суммы, сроки, ссылки на договор."
        ]
    return []


MIN_TRANSPORT_ORDER_COMPOSE_LEN = 20


def validate_transport_order_compose_input(request_text: str) -> list[str]:
    t = (request_text or "").strip()
    if len(t) < MIN_TRANSPORT_ORDER_COMPOSE_LEN:
        return [
            f"Текст запроса слишком короткий (минимум ~{MIN_TRANSPORT_ORDER_COMPOSE_LEN} символов). "
            "Опишите маршрут, груз, стороны и условия."
        ]
    return []


def validate_claim_compose_input(facts: str) -> list[str]:
    t = (facts or "").strip()
    if len(t) < MIN_CLAIM_TEXT_LEN:
        return [
            f"Описание ситуации слишком короткое (минимум ~{MIN_CLAIM_TEXT_LEN} символов). "
            "Укажите стороны, договор/рейс, что произошло и чего требуете."
        ]
    return []


def validate_route_advice_input(route_request: str, vehicle: str) -> list[str]:
    miss: list[str] = []
    if not (route_request or "").strip():
        miss.append("Поле route_request пустое — укажите маршрут или задачу.")
    if not (vehicle or "").strip():
        miss.append("Поле vehicle пустое — укажите тип ТС или ограничения.")
    return miss
