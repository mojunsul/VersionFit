"""조건 기반 항목 탐색: 자연어 조건에 맞는 의존성을 고르고 이유를 붙인다. (F2011)

항목 설명이 영어라 한국어 조건으로 바로 검색하면 맞는 항목이 후보에 오르지 않는다 (progress.md 4.1).
조건을 영어 검색 문장으로 바꿔 후보를 넓게 모은 뒤, LLM이 조건에 맞는 것만 고른다.
"""
from config import CONFIG
from rag.collect import json_list, chat_model
from rag.prompts import EXPLORE_QUERY, EXPLORE_SELECT
from vector_store.store import get_collection


def explore(condition: str) -> list[dict]:
    """[{"item_id", "name", "group", "description", "reason"}], 잘 맞는 순서. 맞는 항목이 없으면 빈 목록."""
    llm, cfg = chat_model(), CONFIG["explore"]
    query = llm.invoke(EXPLORE_QUERY.format(condition=condition)).content.strip()
    found = get_collection("items").similarity_search(query, k=cfg["candidates"])
    candidates = {d.metadata["item_id"]: d for d in found}
    lines = "\n".join(f"{i} | {d.metadata['name']} | {d.metadata['group']} | "
                      f"{d.page_content.rsplit('설명: ', 1)[-1]}" for i, d in candidates.items())
    reply = llm.invoke(EXPLORE_SELECT.format(condition=condition, candidates=lines,
                                             max_items=cfg["max_items"])).content
    picked, seen = [], set()
    for row in json_list(reply):
        item_id = row.get("id") if isinstance(row, dict) else None
        if item_id in candidates and item_id not in seen:  # 후보 밖 id(지어낸 id)는 버린다
            seen.add(item_id)
            d = candidates[item_id]
            picked.append({"item_id": item_id, "name": d.metadata["name"], "group": d.metadata["group"],
                           "description": d.page_content.rsplit("설명: ", 1)[-1],
                           "reason": str(row.get("reason", ""))})
    return picked[:cfg["max_items"]]
