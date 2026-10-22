"""외부 문서 추가 효과: 같은 질문을 Boot 문서만 근거로 / 외부 문서까지 근거로 답하고 정답 키워드가 들어 있는지 본다.

실행: python -m scripts.compare_sources > 결과.md
"Boot 문서만"은 외부 출처를 넣기 전 상태를 흉내 낸다 (수집 단계가 고른 문서 중 Spring Boot 문서만 근거로 쓴다).
자동 판정은 단어 기준의 1차 판정이고, 답변 전문을 함께 출력해 사람이 다시 확인한다.
"""
from data_prep.initializr import load_items
from rag.collect import collect
from rag.graph import answer

# (항목, 버전, 질문, 답에 들어 있어야 할 값). 값은 외부 문서 원문에서 확인한 클래스·설정 이름
CASES = [
    # `@Query`는 패키지 전체 이름(`@org...query.Query`)으로도 나와 끝의 "Query`"로 본다
    ("data-jdbc", "4.1.x", "메서드 이름으로 만든 쿼리로 join을 할 수 있나? 안 되면 어떻게 해?", ["Query`"]),
    ("data-r2dbc", "4.0.x", "R2dbcEntityTemplate으로 조건을 걸어 조회하는 방법은?", ["R2dbcEntityTemplate", "Criteria"]),
    ("data-jpa", "4.0.x", "연관 엔티티를 함께 조회하려고 @EntityGraph를 쓰는 방법은?", ["attributePaths"]),
    ("data-redis", "3.5.x", "RedisTemplate의 키와 값 직렬화 방식을 바꾸려면?", ["Jackson2JsonRedisSerializer"]),
    ("data-mongodb", "4.0.x", "MongoTemplate으로 집계(aggregation) 쿼리를 작성하는 방법은?", ["newAggregation"]),
    ("data-elasticsearch", "4.1.x", "ElasticsearchOperations로 검색 쿼리를 작성하는 방법은?", ["CriteriaQuery"]),
    ("security", "4.0.x", "SecurityFilterChain에서 특정 경로만 인증 없이 허용하려면?", ["permitAll"]),
    ("oauth2-client", "3.5.x", "구글 로그인을 붙이려면 어떤 설정이 필요해?", ["client-id"]),
    ("kafka", "4.0.x", "리스너에서 예외가 나면 재시도하고 DLT로 보내려면?", ["DeadLetterPublishingRecoverer"]),
    ("rabbitmq", "3.5.x", "@RabbitListener에서 재시도를 다 쓰면 메시지는 어떻게 처리되나?", ["RejectAndDontRequeueRecoverer"]),
    ("batch", "4.0.x", "청크 기반 Step을 만드는 방법은?", ["StepBuilder", "chunk"]),
    ("session-data-redis", "3.4.x", "사용자 이름으로 그 사용자의 세션들을 찾으려면?", ["FindByIndexNameSessionRepository"]),
    ("springdoc-openapi", "3.5.x", "Swagger UI 경로를 바꾸려면 어떤 속성을 쓰나?", ["springdoc.swagger-ui.path"]),
]


def main():
    items = {i["id"]: i for i in load_items()}
    rows, full = [], []
    for item_id, v, q, words in CASES:
        c = collect(items[item_id], v, q)
        boot_ids = [d for d in c["doc_ids"] if ":" not in d]  # 외부 문서 doc_id는 "출처:경로"
        r = {}
        for name, ids in (("Boot 문서만", boot_ids), ("외부 문서 포함", c["doc_ids"])):
            r[name] = answer(items[item_id], v, q, doc_ids=ids, terms=c["terms"])
        mark = lambda a: "O" if all(w in a["answer"] for w in words) else "X"
        ext = sum(1 for s in r["외부 문서 포함"]["sources"] if not s["source_type"].startswith(("Initializr", "Spring Boot")))
        rows.append(f"| {item_id} {v} | {q} | `{'`, `'.join(words)}` | {mark(r['Boot 문서만'])} | {mark(r['외부 문서 포함'])} | {ext} |")
        full.append(f"### {item_id} {v}\n\n**질문**: {q}\n\n" + "\n\n".join(f"**{n}**\n\n{a['answer']}" for n, a in r.items()))
    print("| 항목·버전 | 질문 | 정답 키워드 | Boot 문서만 | 외부 문서 포함 | 외부 근거 수 |\n|---|---|---|---|---|---|")
    print("\n".join(rows))
    print("\n## 답변 전문\n\n" + "\n\n".join(full))


if __name__ == "__main__":
    main()
