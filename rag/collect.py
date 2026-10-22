"""질문 시점 문서 수집: 검색어 추출 → 캐시 확인 → 후보 검색·선별 → 청킹·색인. (F2003~F2005)

캐시 단위는 (항목, 버전, 검색어)다. 새 문서를 만들지 못한 검색어도 기록해야 재수집하지 않으므로
Chroma 메타데이터가 아니라 별도 파일(`paths.collect_log`)에 남긴다. 질문별 검색어도 같은 파일에 둔다.
"""
import json
import os
import re
from datetime import date

from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_openai import ChatOpenAI

from config import CONFIG, ROOT
from data_prep import external_docs
from data_prep.boot_docs import doc_id_for_item, doc_title, load_docs, repo_url, search, source_url
from rag.prompts import SEARCH_TERMS, SELECT_DOCS
from vector_store.chunking import chunk
from vector_store.store import get_collection

load_dotenv()


def chat_model() -> ChatOpenAI:
    key = os.environ.get("GMS_KEY")
    if not key:
        raise RuntimeError("GMS_KEY가 없습니다. .env를 확인하세요.")
    return ChatOpenAI(model=CONFIG["models"]["chat"], api_key=key, base_url=CONFIG["models"]["base_url"])


def json_list(text: str) -> list:
    """LLM 답에서 JSON 배열만 꺼낸다. 코드 블록으로 감싸거나 설명을 붙여도 동작하게 한다."""
    m = re.search(r"\[.*\]", text, re.S)
    try:
        value = json.loads(m[0]) if m else []
    except json.JSONDecodeError:
        return []
    return value if isinstance(value, list) else []


def extract_terms(item: dict, version: str, question: str, llm: ChatOpenAI) -> list[str]:
    """프롬프트1. 항목 이름은 항상 포함한다. 파싱에 실패하면 항목 이름만 쓴다."""
    reply = llm.invoke(SEARCH_TERMS.format(
        name=item["name"], description=item["description"], version=version, question=question)).content
    terms = [str(t).strip().lower() for t in json_list(reply) if str(t).strip()]
    return list(dict.fromkeys([item["name"].lower()] + terms))


def select_docs(item: dict, version: str, question: str, candidates: list[str], docs: dict[str, str],
                llm: ChatOpenAI) -> list[str]:
    """프롬프트2. 후보의 제목과 경로만 보여 주고 번호를 받는다. 범위를 벗어난 번호는 버린다."""
    lines = "\n".join(f"[{i}] {doc_title(docs[d])} ({d})" for i, d in enumerate(candidates, start=1))
    max_docs = CONFIG["collect"]["max_docs"]
    reply = llm.invoke(SELECT_DOCS.format(
        version=version, name=item["name"], question=question, candidates=lines, max_docs=max_docs)).content
    picked = [candidates[n - 1] for n in json_list(reply) if isinstance(n, int) and 1 <= n <= len(candidates)]
    return list(dict.fromkeys(picked))[:max_docs]


def _log_path():
    return ROOT / CONFIG["paths"]["collect_log"]


def _load_log() -> dict[str, list[str]]:
    path = _log_path()
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def _save_log(log: dict[str, list[str]]) -> None:
    path = _log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(log, ensure_ascii=False, indent=1), encoding="utf-8")


def _is_indexed(col, item_id: str, version: str, doc_id: str) -> bool:
    where = {"$and": [{"item_id": item_id}, {"boot_version": version}, {"doc_id": doc_id}]}
    return bool(col.get(where=where, limit=1)["ids"])


def collect(item: dict, version: str, question: str, on_step=lambda message: None) -> dict:
    """질문에 필요한 문서를 docs 컬렉션에 채운다. on_step은 화면 진행 표시용 콜백이다. (F2012)

    결과의 doc_ids는 이 질문을 위해 고른 문서(캐시된 검색어 포함)와 항목 자체 문서다. 답변 검색은 이 범위로
    좁힌다. 같은 (항목, 버전)이라도 다른 질문 때문에 색인된 무관한 문서가 섞이지 않게 하기 위해서다.
    """
    llm = chat_model()
    log = _load_log()
    # 프롬프트1은 같은 질문에도 다른 검색어를 내므로 질문별 검색어도 기록한다 (같은 질문 재수집 방지)
    question_key = f"question|{item['id']}|{version}|{question.strip()}"
    if question_key in log:
        terms = log[question_key]
    else:
        on_step("검색어를 뽑는 중")
        terms = log[question_key] = extract_terms(item, version, question, llm)
    key = lambda term: f"{item['id']}|{version}|{term}"
    new_terms = [t for t in terms if key(t) not in log]
    result = {"terms": terms, "new_terms": new_terms, "candidates": [], "selected": [], "added_chunks": 0}
    must = doc_id_for_item(item["doc_url"])
    if not new_terms:
        on_step("이미 수집한 검색어라 수집을 건너뜀")
        _save_log(log)  # 질문별 검색어는 새로 기록됐을 수 있다
        return {**result, "doc_ids": _question_docs(log, key, terms, must)}

    docs = load_docs(version)
    if not docs:
        raise RuntimeError(f"{version} 원문 사본이 없습니다. python -m scripts.fetch_docs 를 먼저 실행하세요.")
    docs |= external_docs.load(item["id"], version)  # 항목에 외부 문서 출처가 있으면 함께 후보로 검색
    on_step("후보 문서를 찾는 중")
    candidates = search(docs, new_terms, CONFIG["collect"]["candidates"])
    selected = select_docs(item, version, question, candidates, docs, llm) if candidates else []
    if must in docs and must not in selected:
        selected.insert(0, must)  # 항목이 가리키는 문서는 선별과 무관하게 포함
    result.update(candidates=candidates, selected=selected)

    col = get_collection("docs")
    for doc_id in selected:
        if _is_indexed(col, item["id"], version, doc_id):
            continue
        title = doc_title(docs[doc_id])
        on_step(f"색인하는 중: {title}")
        if ":" in doc_id:  # 외부 문서 (출처:경로)
            origin = external_docs.describe(doc_id, version)
        else:
            origin = {"source_url": source_url(version, doc_id), "repo_url": repo_url(version, doc_id),
                      "source_type": "boot-reference", "license": "Apache-2.0"}
        meta = {"item_id": item["id"], "boot_version": version, "doc_title": title, "doc_id": doc_id,
                "query": ", ".join(new_terms), "collected_at": date.today().isoformat(), **origin}
        chunks = chunk(docs[doc_id])
        col.add_documents([Document(page_content=c, metadata=meta) for c in chunks],
                          ids=[f"{item['id']}:{version}:{doc_id}:{i}" for i in range(len(chunks))])
        result["added_chunks"] += len(chunks)

    for term in new_terms:
        log[key(term)] = selected
    _save_log(log)
    return {**result, "doc_ids": _question_docs(log, key, terms, must)}


def _question_docs(log: dict, key, terms: list[str], must: str | None) -> list[str]:
    return list(dict.fromkeys(([must] if must else []) + [d for t in terms for d in log.get(key(t), [])]))
