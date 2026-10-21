"""LangGraph 답변 흐름: retrieve(근거 검색·병합) → generate(근거 기반 답변). (F2006, F2007)

문서 수집(collect)은 화면이 진행 상태를 보여 줘야 해서 그래프 밖에서 먼저 실행한다.
"""
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from config import CONFIG
from rag.collect import chat_model
from rag.prompts import ANSWER
from vector_store.store import get_collection


class State(TypedDict, total=False):
    item: dict
    version: str
    question: str
    extra_sources: list[dict]  # 검색 밖에서 온 근거 (예: 의존성 좌표). 항목 정보 바로 뒤에 붙인다
    sources: list[dict]
    answer: str


def label(source_type: str, version: str) -> str:
    """근거 출처 유형 표시 이름. Boot 문서는 코드값으로 저장돼 있고, 외부 문서는 표시 이름 그대로 저장된다."""
    return f"Spring Boot {version} 문서" if source_type == "boot-reference" else source_type


def retrieve(state: State) -> State:
    """선택 항목의 items 청크는 검색 없이 항상 넣고, docs는 항목·버전으로 거른 뒤 질문과 비슷한 청크를 붙인다."""
    item, version = state["item"], state["version"]
    sources = []
    got = get_collection("items").get(ids=[item["id"]])
    url = item["doc_url"].replace("{bootVersion}", version.removesuffix(".x")) or "https://start.spring.io/"
    for text in got["documents"]:
        sources.append({"title": item["name"], "url": url,
                        "text": text, "source_type": "Initializr 항목 정보"})

    search, k = CONFIG["search"], CONFIG["search"]["top_k"] - len(sources)
    sources += state.get("extra_sources", [])
    docs = get_collection("docs")
    where = {"$and": [{"item_id": item["id"]}, {"boot_version": version}]}
    if search["mode"] == "mmr":
        found = docs.max_marginal_relevance_search(state["question"], k=k, fetch_k=search["fetch_k"], filter=where)
    else:
        found = docs.similarity_search(state["question"], k=k, filter=where)

    seen = set()
    for d in found:
        key = (d.metadata["doc_id"], d.page_content)
        if key in seen:
            continue
        seen.add(key)
        section = d.page_content.split("\n", 1)[0]
        sources.append({"title": section or d.metadata["doc_title"], "url": d.metadata["source_url"],
                        "text": d.page_content, "source_type": label(d.metadata["source_type"], version)})
    return {"sources": sources}


def generate(state: State) -> State:
    context = "\n\n".join(f"[근거 {i}] {s['title']} ({s['source_type']})\n{s['text']}"
                          for i, s in enumerate(state["sources"], start=1))
    prompt = ANSWER.format(name=state["item"]["name"], version=state["version"],
                           context=context, question=state["question"])
    return {"answer": chat_model().invoke(prompt).content}


def _build():
    g = StateGraph(State)
    g.add_node("retrieve", retrieve)
    g.add_node("generate", generate)
    g.add_edge(START, "retrieve")
    g.add_edge("retrieve", "generate")
    g.add_edge("generate", END)
    return g.compile()


_graph = None


def answer(item: dict, version: str, question: str, extra_sources: list[dict] | None = None) -> dict:
    """{"answer": 답변, "sources": 근거 목록}. 근거 번호는 sources 순서(1부터)와 같다."""
    global _graph
    _graph = _graph or _build()
    out = _graph.invoke({"item": item, "version": version, "question": question,
                         "extra_sources": extra_sources or []})
    return {"answer": out["answer"], "sources": out["sources"]}
