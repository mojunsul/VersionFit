"""RAG 전후 비교 (F2015): 같은 모델로 근거 없이(LLM만) 답한 것과 RAG로 답한 것을 3개 기준으로 비교한다.

실행: python -m scripts.compare_rag > 결과.md
기준: 사실 정확성(맞는 값 포함·틀린 값 없음), 근거 제시([근거 N]), 모름 응답(답이 문서에 없을 때 인정).
자동 판정은 단어 기준의 1차 판정이고, 답변 전문을 함께 출력해 사람이 다시 확인한다.
"""
import re

from config import CONFIG
from data_prep.initializr import load_items
from rag.collect import chat_model, collect
from rag.graph import answer

NO_RAG = """너는 Spring Boot 기술 문서 전문가다. 한국어로 답한다.

[항목] {name}
[Spring Boot 버전] {version}
[질문] {question}

규칙: 첫 문장에서 "Spring Boot {version} 기준"임을 밝힌다. 확실하지 않거나 모르면 모른다고 답한다."""

# "없습니다"는 '단정할 수 없습니다' 같은 단서에도 걸려 넣지 않는다
UNKNOWN = re.compile(r"확인되지 않|확인할 수 없|모릅니다|모른다|알 수 없")
# (항목, 버전, 질문, 들어 있어야 할 값, 들어 있으면 틀린 값, 답이 문서에 없어 '모름'이 맞는 질문인지)
CASES = [
    ("kafka", "4.0.x", "JSON 값 역직렬화 설정에는 어떤 클래스를 쓰나? KafkaProperties의 패키지는?",
     ["JacksonJsonDeserializer", "org.springframework.boot.kafka.autoconfigure"],
     ["org.springframework.boot.autoconfigure.kafka"], False),
    ("kafka", "3.5.x", "JSON 값 역직렬화 설정에는 어떤 클래스를 쓰나? KafkaProperties의 패키지는?",
     ["JsonDeserializer", "org.springframework.boot.autoconfigure.kafka"],
     ["JacksonJsonDeserializer", "org.springframework.boot.kafka.autoconfigure"], False),
    ("web", "4.0.x", "JSON 직렬화(Jackson)를 설정할 때 쓰는 패키지는?", ["tools.jackson"], [], False),
    ("springdoc-openapi", "3.5.x", "Swagger UI 경로를 바꾸려면 어떤 속성을 쓰나?", ["springdoc.swagger-ui.path"], [], False),
    # 4.0에서 리액티브 스타터 설명이 사라졌다. '쓸 수 있다'고 단정하면 틀린 답
    ("pulsar", "4.0.x", "리액티브 Pulsar 스타터(spring-boot-starter-pulsar-reactive)를 쓸 수 있나?", [],
     ["사용할 수 있습니다", "쓸 수 있습니다", "사용 가능합니다"], True),
    ("kafka", "4.0.x", "Kafka 브로커에 권장되는 JVM 힙 메모리 크기는?", [], [], True),
]


def judge(text: str, must: list[str], wrong: list[str], unknown_expected: bool) -> dict:
    cites = re.findall(r"\[근거\s*[\d,\s]+\]", text)
    missing, bad = [w for w in must if w not in text], [w for w in wrong if w in text]
    fact = "O" if not missing and not bad else f"X (누락 {missing}, 오답 {bad})"
    unknown = ("O" if UNKNOWN.search(text) and not bad else "X") if unknown_expected else "해당 없음"
    return {"fact": fact, "cite": f"O ({len(cites)}개)" if cites else "X", "unknown": unknown}


def main():
    items = {i["id"]: i for i in load_items()}
    llm = chat_model()
    print(f"모델: {CONFIG['models']['chat']}, 검색: {CONFIG['search']['mode']}\n")
    rows, details = [], []
    for n, (item_id, version, q, must, wrong, unknown_expected) in enumerate(CASES, 1):
        item = items[item_id]
        plain = llm.invoke(NO_RAG.format(name=item["name"], version=version, question=q)).content
        collected = collect(item, version, q)
        rag = answer(item, version, q, doc_ids=collected["doc_ids"], terms=collected["terms"])["answer"]
        for label, text in (("LLM만", plain), ("RAG", rag)):
            j = judge(text, must, wrong, unknown_expected)
            rows.append(f"| {n} | {item_id} {version} | {label} | {j['fact']} | {j['cite']} | {j['unknown']} |")
        details.append(f"### {n}. {item['name']} · {version}\n\n**질문**: {q}\n\n"
                       f"**LLM만**\n\n{plain}\n\n**RAG**\n\n{rag}\n")
    print("| # | 항목·버전 | 방식 | 사실 정확성 | 근거 제시 | 모름 응답 |\n|---|---|---|---|---|---|")
    print("\n".join(rows))
    print("\n## 답변 전문\n")
    print("\n".join(details))


if __name__ == "__main__":
    main()
