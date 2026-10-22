"""검색 방식 비교: similarity vs MMR (F2014). 결과 표는 docs/rag-design.md 6절에 옮긴다.

실행: python -m scripts.compare_search
답변은 만들지 않고 근거 검색(retrieve)만 비교한다. 색인이 없는 질문은 collect로 먼저 채운다.
"""
from config import CONFIG
from data_prep.initializr import load_items
from rag.collect import collect
from rag.graph import retrieve

# (항목, 버전, 질문, 정답 근거를 판별할 단어들)
CASES = [
    ("kafka", "4.0.x", "JSON 값 역직렬화 설정에는 어떤 클래스를 쓰나? KafkaProperties의 패키지는?",
     ["JacksonJsonDeserializer", "kafka.autoconfigure.KafkaProperties"]),
    ("pulsar", "3.5.x", "리액티브 Pulsar 스타터를 쓸 수 있나?", ["spring-boot-starter-pulsar-reactive"]),
    ("web", "4.0.x", "JSON 직렬화(Jackson)를 설정할 때 쓰는 패키지는?", ["tools.jackson"]),
    ("springdoc-openapi", "4.1.x", "Swagger UI 경로를 바꾸려면 어떤 속성을 쓰나?", ["springdoc.swagger-ui.path"]),
    ("springdoc-openapi", "3.5.x", "Swagger UI 경로를 바꾸려면 어떤 속성을 쓰나?", ["springdoc.swagger-ui.path"]),
]


def measure(item: dict, version: str, question: str, words: list[str], mode: str, collected: dict) -> dict:
    CONFIG["search"]["mode"] = mode
    state = {"item": item, "version": version, "question": question, "doc_ids": collected["doc_ids"], "terms": collected["terms"]}
    docs = [s for s in retrieve(state)["sources"]
            if not s["source_type"].startswith("Initializr")]
    ranks = {w: next((i for i, s in enumerate(docs, 1) if w in s["text"]), None) for w in words}
    return {"n": len(docs), "sections": len({s["title"] for s in docs}), "ranks": ranks}


def main():
    items = {i["id"]: i for i in load_items()}
    original = CONFIG["search"]["mode"]
    print(f"top_k={CONFIG['search']['top_k']} (항목 정보 1 + 문서), fetch_k={CONFIG['search']['fetch_k']}, "
          f"lambda_mult={CONFIG['search']['lambda_mult']}\n")
    print("| 항목·버전 | 방식 | 근거 수 | 고유 섹션 | 정답 근거 순위 |")
    print("|---|---|---|---|---|")
    try:
        for item_id, version, question, words in CASES:
            collected = collect(items[item_id], version, question)
            for mode in ("similarity", "mmr"):
                m = measure(items[item_id], version, question, words, mode, collected)
                ranks = ", ".join(f"`{w}` {r or '없음'}" for w, r in m["ranks"].items())
                print(f"| {item_id} {version} | {mode} | {m['n']} | {m['sections']} | {ranks} |")
    finally:
        CONFIG["search"]["mode"] = original


if __name__ == "__main__":
    main()
