"""Spring Initializr 메타데이터 API에서 항목(의존성) 목록을 받아 items.json으로 저장한다. (F2001)"""
import json

import requests

from config import CONFIG, ROOT

URL = "https://start.spring.io/metadata/client"
HEADERS = {"Accept": "application/json", "User-Agent": "ssafy-rag-project/0.1 (student project)"}


def fetch_items() -> list[dict]:
    resp = requests.get(URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    items = []
    for group in resp.json()["dependencies"]["values"]:
        for dep in group["values"]:
            ref = dep.get("_links", {}).get("reference", {})
            if isinstance(ref, list):
                ref = ref[0]
            items.append({
                "id": dep["id"],
                "name": dep["name"],
                "group": group["name"],
                "description": dep.get("description", ""),
                "doc_url": ref.get("href", ""),
            })
    return items


def load_items(refresh: bool = False) -> list[dict]:
    path = ROOT / CONFIG["paths"]["items_json"]
    if refresh or not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(fetch_items(), ensure_ascii=False, indent=1), encoding="utf-8")
    return json.loads(path.read_text(encoding="utf-8"))


def item_text(item: dict) -> str:
    """항목 1건을 검색용 텍스트 하나로 묶는다. 사용자는 이름·기능(설명)·분류로 항목을 찾는다."""
    return (
        f"이름: {item['name']}\nid: {item['id']}\n분류: {item['group']}\n설명: {item['description']}"
    )
