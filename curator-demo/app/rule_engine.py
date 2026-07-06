"""КУРАТОР — Rule Engine (демо-реализация).

Реализует формат eligibility и алгоритм из Rule_Engine_MVP_v1.md:
фильтрация → проверка критериев (all/any/none) → Score → категория → Explainability.
Чистая логика без БД — легко тестируется.
"""
from __future__ import annotations
from typing import Any


# ---- Операторы проверки (из §4.1 спецификации) ----
def _as_list(v: Any) -> list:
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


def _op(op: str, actual: Any, expected: Any) -> bool:
    if actual is None and op not in ("not_exists",):
        # отсутствие данных обрабатывается отдельно (missing), здесь считаем «не прошло»
        if op == "exists":
            return False
        return False
    if op == "eq":
        return actual == expected
    if op == "neq":
        return actual != expected
    if op == "in":
        return actual in _as_list(expected)
    if op == "not_in":
        return actual not in _as_list(expected)
    if op == "contains_any":
        return bool(set(_as_list(actual)) & set(_as_list(expected)))
    if op == "contains_all":
        return set(_as_list(expected)).issubset(set(_as_list(actual)))
    if op == "gt":
        return actual > expected
    if op == "gte":
        return actual >= expected
    if op == "lt":
        return actual < expected
    if op == "lte":
        return actual <= expected
    if op == "between":
        lo, hi = expected
        return lo <= actual <= hi
    if op == "is_true":
        return actual is True
    if op == "is_false":
        return actual is False
    if op == "exists":
        return actual is not None
    if op == "not_exists":
        return actual is None
    return False


def _label(field: str, rule: dict) -> str:
    return f'{field} {rule.get("op")} {rule.get("value")}'


def evaluate_measure(context: dict, measure: dict) -> dict:
    """Оценивает одну меру против контекста заявителя. Возвращает результат с Explainability."""
    elig = measure.get("eligibility") or {}
    rules = elig.get("rules", {})
    required = elig.get("required_fields", [])
    soft = elig.get("soft", [])

    matched, unmet, missing = [], [], []

    # 1) required_fields → missing
    for f in required:
        if context.get(f) in (None, "", []):
            missing.append({"field": f, "reason": "нужны данные для проверки"})

    def check_block(block, mode):
        results = []
        for r in block:
            field = r["field"]
            val = context.get(field)
            if val in (None, "", []) and r["op"] not in ("not_exists",):
                # нет данных — это missing, не провал
                missing.append({"field": field, "reason": "нет данных для критерия"})
                results.append(None)
                continue
            ok = _op(r["op"], val, r.get("value"))
            entry = {"field": field, "rule": _label(field, r), "value": val, "ok": ok}
            (matched if ok else unmet).append(entry)
            results.append(ok)
        return results

    all_res = check_block(rules.get("all", []), "all")
    any_res = check_block(rules.get("any", []), "any")
    none_res = check_block(rules.get("none", []), "none")

    # жёсткая логика
    hard_all = all(x for x in all_res if x is not None) if all_res else True
    hard_any = (any(x for x in any_res if x is not None)) if any_res else True
    hard_none = (not any(x for x in none_res if x is not None)) if none_res else True

    # известные (не missing) провалы
    known_fail = any(e for e in unmet)

    # 2) Score
    score = 100
    score -= 20 * len(missing)
    soft_bonus = 0
    for s in soft:
        val = context.get(s["field"])
        if val is not None and _op(s["op"], val, s.get("value")):
            soft_bonus += s.get("weight", 0)

    # категория
    if known_fail and (not hard_all or not hard_none or not hard_any):
        category = "hidden"
        score = min(score, 40)
    elif missing:
        category = "need_info"
        score = max(min(score, 79), 60)
    else:
        category = "eligible"
        score = 100

    # conditional: прошёл жёсткие, но есть незакрытые soft
    if category == "eligible" and soft and soft_bonus < sum(s.get("weight", 0) for s in soft):
        category = "conditional"
        score = 90

    next_step = None
    if category == "need_info" and missing:
        fields = ", ".join(m["field"] for m in missing)
        next_step = f"Укажите: {fields} — чтобы подтвердить право и подать заявку"
    elif category in ("eligible", "conditional"):
        next_step = "Можно готовить документы и подавать заявку"

    return {
        "measure_id": measure["id"],
        "measure_code": measure["code"],
        "title": measure["title"],
        "amount": measure.get("amount"),
        "score": score,
        "category": category,
        "matched": matched,
        "unmet": unmet,
        "missing": missing,
        "next_step": next_step,
        "required_documents": measure.get("required_documents") or [],
    }


CATEGORY_ORDER = {"eligible": 0, "conditional": 1, "need_info": 2, "hidden": 3}


def match(context: dict, measures: list[dict], include_hidden: bool = False) -> list[dict]:
    """Прогон подбора по всем мерам с ранжированием. hidden скрыт для гражданина."""
    results = [evaluate_measure(context, m) for m in measures]
    if not include_hidden:
        results = [r for r in results if r["category"] != "hidden"]
    results.sort(key=lambda r: (CATEGORY_ORDER[r["category"]], -r["score"], -(r["amount"] or 0)))
    return results
