"""버전 인지형 Spring Boot 문서 Q&A 웹 서버. API와 web/ 화면을 함께 제공한다. (F2002, F2008~F2012)

실행:
    uvicorn server:app          # 기본 http://127.0.0.1:8000 (로컬에서만 열림)

수집·생성처럼 오래 걸리는 요청은 SSE(text/event-stream)로 진행 단계(step)를 보내고 마지막에 결과(result)를 보낸다.
오류는 화면에 짧은 안내만 보내고, 추적은 서버 콘솔에만 남긴다 (NF2004).
"""
import json
import logging
import os
import queue
import threading

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from config import ROOT
from data_prep.boot_docs import VERSIONS, doc_id_for_item, docs_dir
from data_prep.initializr import load_items
from rag.collect import collect
from rag.graph import answer
from services.explore import explore
from services.guide import guide
from vector_store.store import get_collection

load_dotenv()
log = logging.getLogger("uvicorn.error")
app = FastAPI(title="Spring Boot 버전별 문서 Q&A")
ITEMS = {i["id"]: i for i in load_items()}
FAILED = "답변을 만들지 못했습니다. 키와 네트워크를 확인한 뒤 다시 시도해 주세요."
_collections = {}


def collection(name: str):
    if name not in _collections:
        _collections[name] = get_collection(name)
    return _collections[name]


def _item(item_id: str) -> dict:
    if item_id not in ITEMS:
        raise HTTPException(404, "알 수 없는 의존성입니다.")
    return ITEMS[item_id]


def _version(version: str) -> str:
    if version not in VERSIONS:
        raise HTTPException(400, "지원하지 않는 Spring Boot 버전입니다.")
    return version


def no_docs_notice(item: dict, version: str, sources: list[dict], retry_hint: bool) -> str | None:
    """Initializr 정보 말고는 근거가 없을 때 이유를 알린다. 항목 문서가 Spring Boot 밖이면 질문을 바꿔도 결과가 같다."""
    if not all(s["source_type"].startswith("Initializr") for s in sources):
        return None
    url = item["doc_url"]
    if url and not doc_id_for_item(url):
        return (f"이 의존성은 Spring Boot 공식 문서가 아니라 외부 문서({url})에서 설명합니다. "
                f"이 서비스는 수집한 문서만 근거로 쓰므로, 설정과 사용법은 원문을 확인하세요.")
    if not url:
        return f"이 의존성은 Initializr에 연결된 문서가 없고, Spring Boot {version} 문서에서도 관련 내용을 찾지 못했습니다."
    return f"Spring Boot {version} 문서에서 관련 내용을 찾지 못했습니다." + (" 질문을 바꿔 보세요." if retry_hint else "")


def _sse(event: str, data) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _stream(work) -> StreamingResponse:
    """work(on_step)를 스레드에서 돌리고, on_step 문구와 최종 결과를 SSE로 흘려보낸다."""
    events = queue.Queue()

    def run():
        try:
            events.put(("result", work(lambda message: events.put(("step", message)))))
        except Exception:
            log.exception("요청 처리 실패")
            events.put(("error", FAILED))
        events.put(None)

    threading.Thread(target=run, daemon=True).start()

    def body():
        while (event := events.get()) is not None:
            yield _sse(*event)

    return StreamingResponse(body(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


class Ask(BaseModel):
    item_id: str
    version: str
    question: str = Field(min_length=1, max_length=1000)


class Target(BaseModel):
    item_id: str
    version: str


class Condition(BaseModel):
    condition: str = Field(min_length=1, max_length=300)


@app.get("/api/status")
def status():
    """화면 시작 시 안내(F2012)와 색인 현황(F2002)에 쓴다."""
    has_key = bool(os.environ.get("GMS_KEY"))
    return {
        "gms_key": has_key,
        "items_total": collection("items")._collection.count() if has_key else None,
        "versions": list(VERSIONS),
        "missing_docs": [v for v in VERSIONS if not any(docs_dir(v).rglob("*.adoc"))],
    }


@app.get("/api/items")
def items():
    return [{k: i[k] for k in ("id", "name", "group", "description", "doc_url")} for i in ITEMS.values()]


@app.get("/api/docs-count")
def docs_count(item_id: str, version: str):
    where = {"$and": [{"item_id": _item(item_id)["id"]}, {"boot_version": _version(version)}]}
    return {"count": len(collection("docs").get(where=where, include=[])["ids"])}


@app.post("/api/ask")
def ask(body: Ask):
    item, version, question = _item(body.item_id), _version(body.version), body.question.strip()

    def work(step):
        added = collect(item, version, question, on_step=step)["added_chunks"]
        step(f"새 문서 청크 {added}건 색인" if added else "이미 색인된 문서로 답합니다")
        step("답변을 만드는 중")
        result = answer(item, version, question)
        return {**result, "notice": no_docs_notice(item, version, result["sources"], retry_hint=True)}

    return _stream(work)


@app.post("/api/guide")
def guide_api(body: Target):
    item, version = _item(body.item_id), _version(body.version)

    def work(step):
        result = guide(item, version, on_step=step)
        return {**result, "notice": no_docs_notice(item, version, result["sources"], retry_hint=False)}

    return _stream(work)


@app.post("/api/explore")
def explore_api(body: Condition):
    try:
        return {"condition": body.condition, "results": explore(body.condition.strip())}
    except Exception:
        log.exception("조건 탐색 실패")
        raise HTTPException(502, "의존성을 찾지 못했습니다. 키와 네트워크를 확인한 뒤 다시 시도해 주세요.")


app.mount("/", StaticFiles(directory=ROOT / "web", html=True), name="web")  # API 경로보다 뒤에 둔다
