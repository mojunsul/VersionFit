"""명세 4장 검증 중 자동으로 확인할 수 있는 항목을 실행하고 결과를 출력한다. 결과는 docs/verification.md에 옮긴다.

실행: python -m scripts.verify
설정을 바꾸는 실험(청크 크기, Top-k)과 키 없음·색인 없음 상태는 메모리에서만 흉내 내고,
config.toml과 chroma_db는 그대로 둔다. 키는 load_dotenv()로 불러온 값으로만 검색하고 출력하지 않는다.
"""
import json
import os
import subprocess
import time
from unittest import mock

from fastapi.testclient import TestClient

import server
from config import CONFIG
from data_prep.boot_docs import doc_id_for_item, load_docs
from data_prep.initializr import load_items
from rag import graph
from rag.collect import collect
from scripts.build_items import main as build_items
from services.explore import explore
from services.guide import guide
from vector_store.chunking import chunk
from vector_store.store import get_collection

results = []


def head(title: str) -> None:
    print(f"\n## {title}")


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append(ok)
    print(f"- [{'통과' if ok else '실패'}] {name}" + (f" — {detail}" if detail else ""))


def sse_events(client: TestClient, path: str, payload: dict) -> list[tuple[str, object]]:
    events, buf = [], ""
    with client.stream("POST", path, json=payload) as r:
        for part in r.iter_text():
            buf += part
            while "\n\n" in buf:
                raw, buf = buf.split("\n\n", 1)
                lines = dict(line.split(": ", 1) for line in raw.split("\n"))
                events.append((lines["event"], json.loads(lines["data"])))
    return events


def main():
    items = {i["id"]: i for i in load_items()}
    kafka = items["kafka"]
    client = TestClient(server.app)

    head("4.1 데이터와 색인 (F2001~F2002)")
    build_items()
    first = get_collection("items")._collection.count()
    build_items()
    second = get_collection("items")._collection.count()
    check("로드한 항목 수와 색인된 청크 수가 같다", len(items) == first, f"항목 {len(items)}, 청크 {first}")
    check("두 번 색인해도 청크 수가 늘지 않는다", first == second, f"{first} → {second}")
    text = get_collection("items").get(ids=["kafka"])["documents"][0]
    print("  kafka 색인 텍스트:", text.replace("\n", " / "))
    check("색인 텍스트에 이름·id·분류·설명이 모두 있다", all(k in text for k in ("이름:", "id:", "분류:", "설명:")))

    head("4.2 문서 수집과 색인 (F2003~F2005)")
    version, q = "4.1.x", "Kafka 리스너의 동시 실행 수(concurrency)는 어떻게 설정하나?"
    t = time.time()
    r = collect(kafka, version, q, on_step=lambda m: print("  ·", m))
    first_seconds = time.time() - t
    print("  프롬프트1 검색어:", r["terms"])
    print("  후보:", r["candidates"])
    print("  선택(색인):", r["selected"], "| 버려진 후보:", [c for c in r["candidates"] if c not in r["selected"]])
    print(f"  새 청크 {r['added_chunks']}개, {first_seconds:.1f}초")
    check("프롬프트1이 검색어 목록을 만든다", len(r["terms"]) > 1)
    must = doc_id_for_item(kafka["doc_url"])
    # 두 번째 실행부터는 캐시로 수집을 건너뛰어 selected가 비므로, 실제 색인 여부로 판정한다
    where = {"$and": [{"item_id": "kafka"}, {"boot_version": version}, {"doc_id": must}]}
    check("항목 자체 문서가 빠지지 않는다", bool(get_collection("docs").get(where=where, limit=1)["ids"]), must)
    t = time.time()
    again = collect(kafka, version, q)
    check("같은 질문을 다시 해도 수집하지 않는다", not again["new_terms"] and again["added_chunks"] == 0,
          f"새 검색어 {again['new_terms']}, 새 청크 {again['added_chunks']}, {time.time() - t:.1f}초")
    doc = load_docs(version)[must]
    counts = {}
    for size, overlap in ((1000, 200), (500, 100)):
        with mock.patch.dict(CONFIG["chunk"], {"size": size, "overlap": overlap}):
            counts[(size, overlap)] = len(chunk(doc))
    check("청크 크기·중복을 바꾸면 청크 수가 달라진다", len(set(counts.values())) > 1,
          ", ".join(f"{s}/{o} → {n}개" for (s, o), n in counts.items()))

    head("4.3 답변과 근거 (F2006~F2008)")
    lists = {}
    for k in (4, 8):
        with mock.patch.dict(CONFIG["search"], {"top_k": k}):
            lists[k] = [s["title"] for s in graph.retrieve({"item": kafka, "version": version, "question": q})["sources"]]
        print(f"  top_k={k}: {lists[k]}")
    check("Top-k를 바꾸면 근거 목록이 달라진다", len(lists[4]) != len(lists[8]), f"{len(lists[4])}개 → {len(lists[8])}개")
    g = graph._build().get_graph()
    print("  그래프 구조:\n" + "\n".join("    " + line for line in g.draw_mermaid().splitlines()))
    check("LangGraph가 retrieve·generate 두 노드다", {"retrieve", "generate"} <= set(g.nodes),
          f"노드 {sorted(n for n in g.nodes if not n.startswith('__'))}")
    unknown = graph.answer(kafka, "4.0.x", "Kafka 브로커에 권장되는 JVM 힙 메모리 크기는?")["answer"]
    print("  문서에 없는 질문 답:", unknown[:120].replace("\n", " "))
    check("문서에 없는 것을 물으면 확인되지 않는다고 답한다", "확인되지 않" in unknown)

    head("4.4 서비스 기능과 화면 (F2009~F2012)")
    found = explore("메시징 큐에 쓸 수 있는 의존성")
    print("  '메시징 큐' 탐색:", [(f["item_id"], f["group"]) for f in found])
    check("조건 탐색 결과가 모두 메시징 분류다", bool(found) and all("Messaging" in f["group"] for f in found))
    nothing = explore("냉장고 온도를 조절하는 의존성")
    check("조건과 무관한 항목을 섞지 않는다 (무관한 조건 → 빈 결과)", not nothing, str([f["item_id"] for f in nothing]))
    g_result = guide(kafka, "4.0.x")
    types = sorted({s["source_type"] for s in g_result["sources"]})
    check("특화 기능(가이드) 결과에 근거가 함께 있다", "[근거" in g_result["answer"] and len(types) > 1, str(types))
    steps = [d for e, d in sse_events(client, "/api/ask", {"item_id": "kafka", "version": "4.0.x",
                                                           "question": "JSON 값 역직렬화 설정에는 어떤 클래스를 쓰나?"}) if e == "step"]
    check("수집·생성 중 진행 단계가 전달된다 (SSE step)", len(steps) >= 2, str(steps))
    with mock.patch.dict(os.environ, {"GMS_KEY": ""}):
        status = client.get("/api/status").json()
    check("API 키가 없으면 상태에 표시된다 (화면 배너)", status["gms_key"] is False, str(status))
    empty = mock.Mock()
    empty._collection.count.return_value = 0
    with mock.patch.object(server, "collection", return_value=empty):
        status = client.get("/api/status").json()
    check("항목 색인이 없으면 상태에 표시된다 (화면 배너)", status["items_total"] == 0, str(status))

    head("4.7 비기능 (NF2001~NF2007)")
    t = time.time()
    sse_events(client, "/api/ask", {"item_id": "kafka", "version": "4.0.x", "question": "JSON 값 역직렬화 설정에는 어떤 클래스를 쓰나?"})
    cached = time.time() - t
    check("대표 질문 처리 시간 (NF2001)", cached < 30, f"이미 색인된 질문 {cached:.1f}초, 4.2 수집 단계 {first_seconds:.1f}초 (처음 수집이면 수집 시간, 이후엔 캐시)")
    key = os.environ.get("GMS_KEY", "")
    history = subprocess.run(["git", "log", "-p", "--all"], capture_output=True, text=True, encoding="utf-8",
                             errors="replace").stdout
    tracked = subprocess.run(["git", "grep", "-I", "-F", "-c", key or "\0", "--", "."], capture_output=True, text=True).stdout
    ignored = subprocess.run(["git", "check-ignore", ".env"], capture_output=True, text=True).stdout.strip()
    check("저장소와 git 이력에 API 키가 없다 (NF2003)", bool(key) and key not in history and not tracked and ignored == ".env",
          f".env gitignore={ignored == '.env'}, 이력·추적 파일 검색 결과 0건")
    with mock.patch.object(server, "answer", side_effect=RuntimeError("secret internal detail")):
        events = sse_events(client, "/api/ask", {"item_id": "kafka", "version": "4.0.x", "question": "오류 시험"})
    last = events[-1]
    leaked = any(w in json.dumps(last, ensure_ascii=False) for w in ("Traceback", "secret internal detail", "RuntimeError"))
    check("오류가 나도 화면 응답에 오류 추적이 없다 (NF2004)", last[0] == "error" and not leaked, str(last))
    with mock.patch.object(server, "explore", side_effect=RuntimeError("secret internal detail")):
        r = client.post("/api/explore", json={"condition": "오류 시험"})
    check("조건 탐색 오류도 짧은 안내만 보낸다 (NF2004)", r.status_code == 502 and "secret" not in r.text, r.text)

    print(f"\n자동 확인 {sum(results)}/{len(results)} 통과")


if __name__ == "__main__":
    main()
