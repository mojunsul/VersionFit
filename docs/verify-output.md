# 명세 4장 자동 확인 실행 결과

2026-10-22 `python -m scripts.verify` 실행 출력 그대로 (답변 모델 `gpt-6.1-sol`). 항목별 판정과 화면 증거는 [verification.md](verification.md).


## 4.1 데이터와 색인 (F2001~F2002)
로드한 항목 204건, 색인된 청크 204건
로드한 항목 204건, 색인된 청크 204건
- [통과] 로드한 항목 수와 색인된 청크 수가 같다 — 항목 204, 청크 204
- [통과] 두 번 색인해도 청크 수가 늘지 않는다 — 204 → 204
  kafka 색인 텍스트: 이름: Spring for Apache Kafka / id: kafka / 분류: Messaging / 설명: Publish, subscribe, store, and process streams of records.
- [통과] 색인 텍스트에 이름·id·분류·설명이 모두 있다

## 4.2 문서 수집과 색인 (F2003~F2005)
  · 이미 수집한 검색어라 수집을 건너뜀
  프롬프트1 검색어: ['spring for apache kafka', 'concurrency', 'concurrent message listener', 'container factory', 'kafka listener', 'spring.kafka.listener']
  후보: []
  선택(색인): [] | 버려진 후보: []
  새 청크 0개, 0.2초
- [통과] 프롬프트1이 검색어 목록을 만든다
- [통과] 항목 자체 문서가 빠지지 않는다 — reference/pages/messaging/kafka.adoc
- [통과] 같은 질문을 다시 해도 수집하지 않는다 — 새 검색어 [], 새 청크 0, 0.0초
- [통과] 청크 크기·중복을 바꾸면 청크 수가 달라진다 — 1000/200 → 11개, 500/100 → 27개

## 4.3 답변과 근거 (F2006~F2008)
  top_k=4: ['Spring for Apache Kafka', 'Apache Kafka Support > Receiving a Message', 'Apache Kafka Support', 'Apache Kafka Support > Kafka Streams']
  top_k=8: ['Spring for Apache Kafka', 'Apache Kafka Support > Receiving a Message', 'Apache Kafka Support', 'Apache Kafka Support > Kafka Streams', 'Message Listener Containers > Using `ConcurrentMessageListenerContainer`', 'Message Listener Containers > Using `ConcurrentMessageListenerContainer`', '`@KafkaListener` Annotation > Record Listeners', 'Message Listener Containers']
- [통과] Top-k를 바꾸면 근거 목록이 달라진다 — 4개 → 8개
  그래프 구조:
    ---
    config:
      flowchart:
        curve: linear
    ---
    graph TD;
    	__start__([<p>__start__</p>]):::first
    	retrieve(retrieve)
    	generate(generate)
    	__end__([<p>__end__</p>]):::last
    	__start__ --> retrieve;
    	retrieve --> generate;
    	generate --> __end__;
    	classDef default fill:#f2f0ff,line-height:1.2
    	classDef first fill-opacity:0
    	classDef last fill:#bfb6fc
- [통과] LangGraph가 retrieve·generate 두 노드다 — 노드 ['generate', 'retrieve']
  문서에 없는 질문 답: Spring Boot 4.0.x 기준, Kafka 브로커에 권장되는 JVM 힙 메모리 크기는 제공된 문서에서 확인되지 않는다.
- [통과] 문서에 없는 것을 물으면 확인되지 않는다고 답한다

## 4.4 서비스 기능과 화면 (F2009~F2012)
  '메시징 큐' 탐색: [('rabbitmq', 'Messaging'), ('artemis', 'Messaging'), ('activemq', 'Messaging'), ('pulsar', 'Messaging'), ('solace', 'Messaging'), ('cloud-gcp-pubsub', 'Google Cloud'), ('kafka', 'Messaging'), ('cloud-stream', 'Spring Cloud Messaging')]
- [통과] 조건 탐색 결과 대부분이 메시징 분류이고, 메시징과 무관한 항목이 없다 — 메시징 분류 7/8
- [통과] 조건과 무관한 항목을 섞지 않는다 (무관한 조건 → 빈 결과) — []
- [통과] 특화 기능(가이드) 결과에 근거가 함께 있다 — ['Initializr 의존성 좌표 (4.0.8.RELEASE)', 'Initializr 항목 정보', 'Spring Boot 4.0.x 문서', 'Spring for Apache Kafka 4.0 문서']
- [통과] 수집·생성 중 진행 단계가 전달된다 (SSE step) — ['이미 수집한 검색어라 수집을 건너뜀', '이미 색인된 문서로 답합니다', '답변을 만드는 중']
  일반 지식 답변: 공식 문서 근거 없이 일반 지식으로 답한다.  Kafka 브로커의 JVM 힙은 **운영 환경에서 보통 6GB 정도를 시작점으로 잡고**, 실제 부하와 GC 지표를 보며 조정한다. 모든 환경에 적용되는 고정 권장값은 
- [통과] 문서에 없을 때 요청하면 근거 없는 일반 지식 답변을 따로 준다
- [통과] API 키가 없으면 상태에 표시된다 (화면 배너) — {'gms_key': False, 'items_total': None, 'versions': ['4.1.x', '4.0.x', '3.5.x', '3.4.x'], 'missing_docs': []}
- [통과] 항목 색인이 없으면 상태에 표시된다 (화면 배너) — {'gms_key': True, 'items_total': 0, 'versions': ['4.1.x', '4.0.x', '3.5.x', '3.4.x'], 'missing_docs': []}

## 4.7 비기능 (NF2001~NF2007)
- [통과] 대표 질문 처리 시간 (NF2001) — 이미 색인된 질문 7.2초, 4.2 수집 단계 0.2초 (처음 수집이면 수집 시간, 이후엔 캐시)
- [통과] 저장소와 git 이력에 API 키가 없다 (NF2003) — .env gitignore=True, 이력·추적 파일 검색 결과 0건
요청 처리 실패
Traceback (most recent call last):
  File "C:\SSAFY\rag\server.py", line 79, in run
    events.put(("result", work(lambda message: events.put(("step", message)))))
                          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\SSAFY\rag\server.py", line 141, in work
    result = answer(item, version, question, doc_ids=collected["doc_ids"], terms=collected["terms"])
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\SSAFY\AppData\Local\Programs\Python\Python312\Lib\unittest\mock.py", line 1139, in __call__
    return self._mock_call(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\SSAFY\AppData\Local\Programs\Python\Python312\Lib\unittest\mock.py", line 1143, in _mock_call
    return self._execute_mock_call(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\SSAFY\AppData\Local\Programs\Python\Python312\Lib\unittest\mock.py", line 1198, in _execute_mock_call
    raise effect
RuntimeError: secret internal detail
- [통과] 오류가 나도 화면 응답에 오류 추적이 없다 (NF2004) — ('error', '답변을 만들지 못했습니다. 키와 네트워크를 확인한 뒤 다시 시도해 주세요.')
조건 탐색 실패
Traceback (most recent call last):
  File "C:\SSAFY\rag\server.py", line 173, in explore_api
    return {"condition": body.condition, "results": explore(body.condition.strip())}
                                                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\SSAFY\AppData\Local\Programs\Python\Python312\Lib\unittest\mock.py", line 1139, in __call__
    return self._mock_call(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\SSAFY\AppData\Local\Programs\Python\Python312\Lib\unittest\mock.py", line 1143, in _mock_call
    return self._execute_mock_call(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\SSAFY\AppData\Local\Programs\Python\Python312\Lib\unittest\mock.py", line 1198, in _execute_mock_call
    raise effect
RuntimeError: secret internal detail
- [통과] 조건 탐색 오류도 짧은 안내만 보낸다 (NF2004) — {"detail":"의존성을 찾지 못했습니다. 키와 네트워크를 확인한 뒤 다시 시도해 주세요."}

자동 확인 21/21 통과
