/** Синхронизировано с backend/app/schemas/review_reasons.py */
export const REVIEW_REASON_OPTIONS: { id: string; label: string }[] = [
  { id: "insufficient_context", label: "Недостаточно контекста" },
  { id: "wrong_risk_level", label: "Неверный уровень риска" },
  { id: "weak_citations", label: "Слабые цитаты / источники" },
  { id: "bad_draft_tone", label: "Тон / стиль черновика" },
  { id: "incorrect_legal_basis", label: "Неверная правовая база" },
  { id: "too_generic", label: "Слишком общий ответ" },
  { id: "hallucination_suspected", label: "Подозрение на галлюцинацию" },
  { id: "formatting_problem", label: "Форматирование" },
  { id: "operator_preferred_manual", label: "Предпочтительно вручную" },
  { id: "bad_price_range", label: "Цена / диапазон не рынок" },
  { id: "other", label: "Другое" },
];
