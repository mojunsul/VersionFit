"""버전 인지형 Spring Boot 문서 Q&A 화면. (F2008, F2009, F2010, F2012)

실행:
    streamlit run app.py

놓치기 쉬운 두 가지
    1. 대화를 다시 그릴 때 근거 목록도 함께 그린다. 빠뜨리면 이전 답변의 근거가 사라진다.
    2. 검색된 문서를 전부 보여 주지 않는다. 답변이 실제로 인용한 [근거 N]만 보여 주고,
       인용이 하나도 없으면 그 사실을 안내한다. (요구사항 F2008)
"""

import os
import re

import streamlit as st
from dotenv import load_dotenv

from data_prep.boot_docs import VERSIONS, docs_dir
from data_prep.initializr import load_items
from rag.collect import collect
from rag.graph import answer
from services.guide import guide
from vector_store.store import get_collection

load_dotenv()

# 답변 본문의 [근거 3], [근거 3, 5] 표기를 찾는다.
CITE_PATTERN = re.compile(r"\[근거\s*([\d,\s]+)\]")


@st.cache_data
def items_by_id() -> dict[str, dict]:
    return {i["id"]: i for i in load_items()}


@st.cache_resource
def collection(name: str):
    return get_collection(name)


def docs_count(item_id: str, version: str) -> int:
    where = {"$and": [{"item_id": item_id}, {"boot_version": version}]}
    return len(collection("docs").get(where=where, include=[])["ids"])


def cited_sources(answer: str, sources: list[dict]) -> list[tuple[int, dict]]:
    """답변이 실제로 인용한 근거만 (번호, 문서)로 돌려준다. 인용이 없으면 빈 목록. (F2008)"""
    numbers = {
        int(n) for group in CITE_PATTERN.findall(answer)
        for n in group.split(",") if n.strip().isdigit()
    }
    return [(i, s) for i, s in enumerate(sources, start=1) if i in numbers]


def render_sources(answer: str, sources: list[dict]) -> None:
    """답변 아래 근거 목록. 인용한 것만 보여 주고, 인용이 없으면 안내한다."""
    used = cited_sources(answer, sources)
    if not used:
        st.caption("ⓘ 답변에 인용된 근거가 없습니다.")
        return
    with st.expander(f"답변에 사용한 근거 {len(used)}건"):
        for number, source in used:
            st.markdown(f"**[근거 {number}]** {source['title']} · {source['source_type']} · [원문]({source['url']})")


st.set_page_config(page_title="Spring Boot 버전별 문서 Q&A", page_icon="🍃")
st.title("🍃 Spring Boot 버전별 문서 Q&A")
st.caption("의존성과 Spring Boot 버전을 고르면, 그 버전의 공식 문서를 근거로 답하고 출처를 함께 보여 줍니다.")

if not os.environ.get("GMS_KEY"):
    st.error("GMS_KEY가 설정되지 않았습니다. `.env.example`을 복사해 `.env`에 키를 넣어 주세요.")
    st.stop()
items_total = collection("items")._collection.count()
if not items_total:
    st.warning("항목 색인이 비어 있습니다. 먼저 `python -m scripts.build_items`를 실행해 주세요.")
    st.stop()

by_id = items_by_id()
chats = st.session_state.setdefault("chats", {})  # (항목 id, 버전) → 대화. 항목·버전마다 대화를 분리한다

with st.sidebar:
    st.header("항목과 버전")
    item_id = st.selectbox(
        "의존성", list(by_id), index=None, key="item_id", placeholder="의존성을 고르세요 (입력해 검색)",
        format_func=lambda i: f"{by_id[i]['name']} ({by_id[i]['group']})",
    )
    version = st.selectbox("Spring Boot 버전", list(VERSIONS), key="version")
    st.caption(f"색인 현황 · 항목 {items_total}건"
               + (f" · 이 항목·버전 문서 청크 {docs_count(item_id, version)}건" if item_id else ""))
    guide_requested = st.button("📘 버전 맞춤 사용 가이드", width="stretch", disabled=not item_id)
    if st.button("이 대화 지우기", width="stretch", disabled=not item_id):
        chats[(item_id, version)] = []

if not item_id:
    st.info("왼쪽에서 질문할 의존성을 먼저 고르세요.")
    st.stop()
if not any(docs_dir(version).rglob("*.adoc")):
    st.warning(f"{version} 문서 원문이 없습니다. 먼저 `python -m scripts.fetch_docs`를 실행해 주세요.")
    st.stop()

item = by_id[item_id]
messages = chats.setdefault((item_id, version), [])
st.subheader(f"{item['name']} · Spring Boot {version}")

for message in messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["role"] == "assistant":
            render_sources(message["content"], message.get("sources", []))

question = st.chat_input(f"{item['name']} ({version})에 대해 궁금한 점을 물어보세요")
if guide_requested:
    question = "📘 버전 맞춤 사용 가이드 (의존성 선언 · 핵심 설정 · import)"

if question:
    messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        result = None
        try:
            with st.status("관련 문서를 찾고 있습니다...", expanded=False) as status:
                def step(message: str) -> None:
                    status.update(label=message)
                    status.write(message)

                if guide_requested:
                    result = guide(item, version, on_step=step)  # 수집·좌표·생성까지 한 번에
                    status.update(label="가이드 준비 완료", state="complete")
                else:
                    added = collect(item, version, question, on_step=step)["added_chunks"]
                    status.update(label=f"새 문서 청크 {added}건 색인" if added else "이미 색인된 문서로 답합니다",
                                  state="complete")
            if not guide_requested:
                with st.spinner("답변을 만드는 중..."):
                    result = answer(item, version, question)
        except Exception:
            # NF2004: 오류 추적·키·프롬프트는 화면에 내보내지 않는다
            st.error("답변을 만들지 못했습니다. 키와 네트워크를 확인한 뒤 다시 시도해 주세요.")

        if result:
            st.markdown(result["answer"])
            if not any(s["source_type"].startswith("Spring Boot") for s in result["sources"]):
                st.info(f"{version} 문서에서 이 질문과 관련된 내용을 찾지 못했습니다. 질문을 바꿔 보세요.")
            render_sources(result["answer"], result["sources"])
            messages.append({"role": "assistant", "content": result["answer"], "sources": result["sources"]})
