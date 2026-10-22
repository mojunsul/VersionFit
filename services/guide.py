"""버전 맞춤 사용 가이드: 선택 항목·버전의 의존성 선언, 핵심 설정, import를 근거와 함께 만든다. (F2010)

4.x 문서에는 스타터 좌표(예: spring-boot-starter-kafka)가 없어서, Initializr가 지원하는 버전은
Initializr 좌표를 근거로 함께 넣는다. 지원하지 않는 버전(3.x)은 문서 근거만 쓴다.
"""
from data_prep.initializr import fetch_coordinates
from rag.collect import collect
from rag.graph import answer
from rag.prompts import GUIDE_QUESTION


def coordinate_sources(item: dict, version: str) -> list[dict]:
    coords = fetch_coordinates(version)
    if not coords:
        return []
    boot = coords["boot_version"]
    dep = coords["dependencies"].get(item["id"])
    if dep:
        text = (f"Spring Boot {boot}에서 Initializr가 추가하는 '{item['name']}' 의존성 좌표: "
                + ", ".join(f"{k}={v}" for k, v in dep.items()))
    else:
        text = f"Spring Boot {boot}용 Initializr 의존성 목록에 '{item['name']}'(id: {item['id']})이 없다."
    return [{"title": f"{item['name']} 의존성 좌표", "text": text,
             "url": f"https://start.spring.io/dependencies?bootVersion={boot}",
             "source_type": f"Initializr 의존성 좌표 ({boot})"}]


def guide(item: dict, version: str, on_step=lambda message: None) -> dict:
    """{"answer", "sources"}. 문서 수집(collect)까지 포함한다."""
    question = GUIDE_QUESTION.format(version=version)
    doc_ids = collect(item, version, question, on_step=on_step)["doc_ids"]
    on_step("의존성 좌표를 확인하는 중")
    extra = coordinate_sources(item, version)
    on_step("가이드를 만드는 중")
    return answer(item, version, question, extra_sources=extra, doc_ids=doc_ids)
