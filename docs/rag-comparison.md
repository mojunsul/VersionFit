# RAG 전후 비교 (F2015)

2026-10-22 측정. 재현: `python -m scripts.compare_rag`

## 1. 방법

- 같은 모델(`gpt-5.4-mini`)로 같은 질문에 두 번 답한다.
  - **LLM만**: 근거 없이 항목·버전·질문만 준다. 공정하게 비교하려고 "확실하지 않거나 모르면 모른다고 답한다"는 지시를 똑같이 넣었다.
  - **RAG**: 서비스와 같은 경로(`collect` → `answer`, 검색 MMR, 근거 8개).
- 질문 6개: 답이 문서에 있는 질문 4개(버전에 따라 답이 달라지는 질문 포함), 문서에 답이 없는 질문 2개.
- 기준 3개
  - **사실 정확성**: 맞는 값이 들어 있고, 틀린 값(다른 버전의 값, 없는 기능을 있다고 한 주장)이 없는가
  - **근거 제시**: 주장에 `[근거 N]`을 붙였는가
  - **모름 응답**: 답이 문서에 없을 때 지어내지 않고 모른다고 하는가
- 1차 판정은 스크립트의 단어 기준이고, 아래 표는 답변 전문(3절)을 읽고 확정했다.

## 2. 결과

| # | 항목·버전 | 질문 요지 | LLM만 | RAG |
|---|---|---|---|---|
| 1 | Kafka 4.0.x | 역직렬화 클래스, `KafkaProperties` 패키지 | ✗ 3.x 값(`JsonDeserializer`, `boot.autoconfigure.kafka`)으로 답함 | ✓ `JacksonJsonDeserializer`, `boot.kafka.autoconfigure` [근거] |
| 2 | Kafka 3.5.x | 같은 질문 | ✓ | ✓ [근거] |
| 3 | Web 4.0.x | Jackson 패키지 | ✗ `tools.jackson` 누락 (3.x의 `com.fasterxml`로 답함) | ✓ `tools.jackson` [근거] |
| 4 | SpringDoc 3.5.x | Swagger UI 경로 속성 | ✓ | ✓ [근거, springdoc 2.x 문서] |
| 5 | Pulsar 4.0.x | 리액티브 스타터 사용 가능 여부 (4.0 문서에서 사라짐) | ✗ "사용할 수 있습니다"라고 단정 | ✓ "문서에서 확인되지 않는다" + 문서에 있는 스타터만 안내 [근거] |
| 6 | Kafka 4.0.x | 브로커 권장 JVM 힙 (문서에 없음) | ✗ "6GB(-Xmx6g)"라는 근거 없는 수치 | ✓ "문서에서 확인되지 않는다" |

| 기준 | LLM만 | RAG |
|---|---|---|
| 사실 정확성 (1~5번, 5개) | 2 / 5 | **5 / 5** |
| 근거 제시 (답이 있는 1~5번) | 0 / 5 | **5 / 5** |
| 모름 응답 (5·6번) | 0 / 2 | **2 / 2** |

**해석**
- LLM만 쓰면 **최신 버전(4.0)의 변경을 모르고 3.x 지식으로 답한다** (1, 3번). 3.5.x처럼 학습된 지식과 맞는 버전은 맞힌다 (2, 4번). 이 서비스가 버전 인지형이어야 하는 이유가 여기서 드러난다.
- "모르면 모른다고 하라"고 지시해도 LLM만으로는 **없어진 기능을 있다고 하거나(5번) 그럴듯한 수치를 지어낸다(6번)**. RAG는 근거에 없으면 "확인되지 않는다"고 답했다.
- RAG의 6번 답에는 근거 번호가 없다. 인용할 근거가 없는 "모름" 답이라 맞는 동작이다.

**관찰: 항목과 무관한 질문**
처음에는 "Kafka 항목에서 GraphQL 스키마 위치를 묻는 질문"을 답이 없는 질문으로 넣었다. 그런데 RAG는 수집 단계에서 Spring Boot GraphQL 문서를 찾아와 `spring.graphql.schema.locations`를 근거와 함께 정확히 답했다. 지어낸 답이 아니라서 "모름" 질문에서 빼고, 실제로 문서에 없는 6번으로 바꿨다. 항목과 무관한 질문도 Spring Boot 문서 안에 답이 있으면 답한다는 뜻이다.

**한계**
- 질문 6개, 각 1회 측정이다. 같은 질문도 답이 달라질 수 있다.
- 판정 단어는 질문마다 직접 정했다.

## 3. 답변 전문

### 1. Spring for Apache Kafka · 4.0.x

**질문**: JSON 값 역직렬화 설정에는 어떤 클래스를 쓰나? KafkaProperties의 패키지는?

**LLM만**

Spring Boot 4.0.x 기준으로 답하면, **JSON 값 역직렬화 설정**에는 보통 `org.springframework.kafka.support.serializer.JsonDeserializer` 클래스를 사용합니다.

또한 `KafkaProperties`의 패키지는 **`org.springframework.boot.autoconfigure.kafka.KafkaProperties`** 입니다.

참고로, JSON 직렬화/역직렬화 관련 설정은 보통 Spring Kafka의 serializer/deserializer를 함께 사용하며, 구체적인 설정 방식은 `spring.kafka.consumer.properties...` 또는 `DefaultKafkaConsumerFactory` 구성에서 다룹니다.

**RAG**

Spring Boot 4.0.x 기준으로 답하면, 질문은 두 가지입니다.

1. JSON 값 역직렬화 설정에 쓰는 클래스는 `org.springframework.kafka.support.serializer.JacksonJsonDeserializer`입니다. [근거 4]

2. `KafkaProperties`의 패키지는 `org.springframework.boot.kafka.autoconfigure`입니다. 따라서 전체 이름은 `org.springframework.boot.kafka.autoconfigure.KafkaProperties`입니다. [근거 3]

### 2. Spring for Apache Kafka · 3.5.x

**질문**: JSON 값 역직렬화 설정에는 어떤 클래스를 쓰나? KafkaProperties의 패키지는?

**LLM만**

Spring Boot 3.5.x 기준, **JSON 값 역직렬화 설정**에는 보통 **`org.springframework.kafka.support.serializer.JsonDeserializer`** 클래스를 사용합니다.

그리고 **`KafkaProperties`**의 패키지는 **`org.springframework.boot.autoconfigure.kafka.KafkaProperties`** 입니다.

원하시면 이어서 `spring.kafka.consumer.properties.spring.json.trusted.packages` 같은 실제 설정 예시도 같이 정리해드릴게요.

**RAG**

Spring Boot 3.5.x 기준입니다.

1. JSON 값 역직렬화 설정에 쓰는 클래스는 `org.springframework.kafka.support.serializer.JsonDeserializer`입니다. [근거 4]

2. `KafkaProperties`의 패키지는 `org.springframework.boot.autoconfigure.kafka`입니다. 즉, 전체 이름은 `org.springframework.boot.autoconfigure.kafka.KafkaProperties`입니다. [근거 3, 5]

### 3. Spring Web · 4.0.x

**질문**: JSON 직렬화(Jackson)를 설정할 때 쓰는 패키지는?

**LLM만**

Spring Boot 4.0.x 기준으로, JSON 직렬화(Jackson) 설정과 관련해 주로 사용하는 패키지는 **`org.springframework.http.converter.json`** 입니다.

대표적으로 다음 클래스들이 있습니다.

- `org.springframework.http.converter.json.Jackson2ObjectMapperBuilder`
- `org.springframework.http.converter.json.Jackson2ObjectMapperBuilderCustomizer`

참고로, 애플리케이션에서 Jackson 자체 설정을 직접 다룰 때는 보통 Jackson 라이브러리의 패키지인 **`com.fasterxml.jackson.databind`** 계열도 함께 사용합니다.

다만, **Spring Boot 4.0.x에서 새로 바뀐 내부 구조나 추가된 패키지**까지는 이 질문만으로 확실히 단정하기 어렵습니다. 필요한 경우 사용 목적(전역 설정, ObjectMapper 커스터마이징, Web MVC 메시지 컨버터 설정 등)을 알려주시면 더 정확히 답하겠습니다.

**RAG**

Spring Boot 4.0.x 기준, JSON 직렬화(Jackson) 설정과 관련해 근거에서 확인되는 패키지는 `org.springframework.boot.jackson`입니다. `@org.springframework.boot.jackson.JacksonComponent`를 사용해 Spring Bean을 직접 등록할 수 있다고 문서에 나와 있습니다. [근거 4]

또한 Jackson 3의 자동 구성과 관련된 클래스는 `tools.jackson.databind.json.JsonMapper`이며, 이 Bean이 자동으로 구성된다고 되어 있습니다. 다만 이 근거에는 `JsonMapper`의 패키지가 `tools.jackson.databind.json`로 직접 제시되어 있을 뿐, “설정할 때 쓰는 패키지”를 하나로 특정하는 설명은 문서에서 확인되지 않는다. [근거 3]

### 4. SpringDoc OpenAPI · 3.5.x

**질문**: Swagger UI 경로를 바꾸려면 어떤 속성을 쓰나?

**LLM만**

Spring Boot 3.5.x 기준으로, Swagger UI 경로를 바꾸려면 `springdoc.swagger-ui.path` 속성을 사용합니다.

예:
```properties
springdoc.swagger-ui.path=/docs
```

그러면 Swagger UI는 기본 `/swagger-ui.html` 또는 `/swagger-ui/index.html` 대신 `/docs` 경로로 접근하게 됩니다.

참고로 OpenAPI JSON 경로도 함께 바꾸고 싶다면 보통 아래 속성을 씁니다:
```properties
springdoc.api-docs.path=/api-docs
```

원하시면 `application.yml` 예시도 같이 드리겠습니다.

**RAG**

Spring Boot 3.5.x 기준, `Swagger UI` 경로를 바꾸려면 `springdoc.swagger-ui.path` 속성을 사용한다. 기본값은 `/swagger-ui.html`이며, Swagger UI HTML 문서의 커스텀 경로를 지정하는 용도다. [근거 4]

### 5. Spring for Apache Pulsar · 4.0.x

**질문**: 리액티브 Pulsar 스타터(spring-boot-starter-pulsar-reactive)를 쓸 수 있나?

**LLM만**

Spring Boot 4.0.x 기준, **네, `spring-boot-starter-pulsar-reactive`를 사용할 수 있습니다.**

다만 몇 가지를 같이 알아두면 좋습니다.

- 이 스타터는 **리액티브 API를 쓰는 Pulsar 연동용**입니다.
- 일반 `spring-boot-starter-pulsar`가 아닌, **리액티브 방식**으로 `ReactivePulsarTemplate` 같은 구성을 사용하게 됩니다.
- 실제 사용 가능 여부는 **Pulsar 클라이언트/브로커 버전 호환성**과 함께 확인하는 것이 좋습니다.

즉, **Spring Boot 4.0.x에서는 리액티브 Pulsar 스타터를 사용할 수 있다**고 보면 됩니다.  
원하시면 제가 이어서 **의존성 추가 예시**와 **간단한 리액티브 송수신 코드**도 한국어로 정리해드릴게요.

**RAG**

Spring Boot 4.0.x 기준, `spring-boot-starter-pulsar-reactive`를 사용할 수 있는지는 문서에서 확인되지 않는다.

문서에서 확인되는 것은 `spring-boot-starter-pulsar` 스타터가 있다는 점과, `org.springframework.pulsar:spring-pulsar`가 클래스패스에 있으면 Spring Boot가 Spring for Apache Pulsar 컴포넌트를 자동 구성한다는 점이다. [근거 2]

### 6. Spring for Apache Kafka · 4.0.x

**질문**: Kafka 브로커에 권장되는 JVM 힙 메모리 크기는?

**LLM만**

Spring Boot 4.0.x 기준, Kafka 브로커에 **권장되는 JVM 힙 메모리 크기**는 **일반적으로 6GB 정도(예: -Xmx6g)**로 안내됩니다.

다만 이 값은 **절대 고정값이 아니라 운영 환경과 메시지 처리량, 파티션 수, OS 캐시 활용, 네트워크/디스크 성능** 등에 따라 달라질 수 있습니다.  
즉, **작은 클러스터는 더 적게도 가능하고**, 고부하 환경에서는 더 크게 잡을 수도 있습니다.

정리하면:
- **권장 시작점:** `-Xmx6g`
- **주의:** Kafka는 힙만큼이나 **페이지 캐시(오프힙)** 도 중요하므로, 힙을 너무 크게 잡는 것은 오히려 비효율적일 수 있음

원하시면 제가 이어서 **Kafka 브로커 메모리 설정 전체 권장안(힙/오프힙/OS 캐시 포함)** 도 정리해드릴게요.

**RAG**

Spring Boot 4.0.x 기준, Kafka 브로커에 권장되는 JVM 힙 메모리 크기는 문서에서 확인되지 않는다.

