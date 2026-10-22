"""Spring Boot 문서 밖의 외부 문서 출처: springdoc-openapi, Spring Data, Security, Kafka, AMQP, Batch, Session, Lombok. (F2016 일부)

항목 id가 SOURCES에 있으면, 그 항목의 질문 시점 수집에서 이 문서도 후보로 검색한다.
Boot 버전마다 호환되는 판(브랜치·폴더)의 문서를 쓴다 (progress.md 3절).
원문은 data/external_docs/{저장소}/{브랜치}/에 받는다. 같은 저장소를 쓰는 출처는 사본을 함께 쓴다.
"""
import html
import re
from fnmatch import fnmatch
from pathlib import Path

from config import CONFIG, ROOT
from data_prep.boot_docs import clean, github_tree, http_get

_SPRINGDOC = {"repo": "springdoc/springdoc.github.io", "branch": "master", "label": "springdoc-openapi {} 문서"}

# Spring Data 문서 (Antora). 본문 일부는 spring-data-commons 저장소의 페이지를 include로 가져온다
COMMONS_REPO = "spring-projects/spring-data-commons"
DATA_ROOT = "src/main/antora/modules/ROOT"
# Boot 버전 → Spring Data 릴리스 묶음의 commons 판. Boot spring-boot-dependencies의 Spring Data Bom
# (4.1.x 2026.0, 4.0.x 2025.1, 3.5.x 2025.0, 3.4.x 2024.1) → Maven Central spring-data-bom으로 확인 (2026-10-22)
DATA_COMMONS = {"4.1.x": "4.1", "4.0.x": "4.0", "3.5.x": "3.5", "3.4.x": "3.4"}
_DATA_SHARED = ["pages/repositories/*.adoc", "pages/commons/*.adoc", "pages/object-mapping.adoc",
                "pages/query-by-example.adoc", "pages/value-expressions.adoc"]


def _antora(title: str, repo: str, url_base: str, root: str, releases: dict[str, str], pages: list[str],
            attributes, gone: tuple[str, ...] = ("3.4.x",)) -> dict:
    """Spring 프로젝트의 Antora 문서. releases: Boot 버전 → 프로젝트 릴리스 버전(Boot가 관리하는 값).
    판(major.minor)이 브랜치 이름이다. docs.spring.io는 최신판(Boot 4.1.x 짝)을 버전 없는 주소로 보여 주고,
    gone에 든 Boot 버전의 판은 내려가서(404) GitHub 원문을 링크한다. attributes(boot, short, release)는 판의 문서 속성을 만든다."""
    current = releases["4.1.x"].rsplit(".", 1)[0]
    editions = {}
    for boot, release in releases.items():
        short = release.rsplit(".", 1)[0]
        url = url_base if short == current else None if boot in gone else f"{url_base}{short}/"
        editions[boot] = {"branch": f"{short}.x", "pages": pages, "page_urls": True, "url": url,
                          "label": f"{title} {short} 문서", "attributes": attributes(boot, short, release)}
    return {"repo": f"spring-projects/{repo}", "root": root, "license": "Apache-2.0", "editions": editions}


def _spring_data(title: str, repo: str, slug: str, store: str, releases: dict[str, str], pages: list[str]) -> dict:
    """Spring Data 모듈. commons 페이지는 Boot 버전의 릴리스 묶음이 정한 commons 판 브랜치에서 읽는다."""
    def attributes(boot, short, release):
        commons = DATA_COMMONS[boot]
        return {"store": store, "version": release, "include-xml-namespaces": "false",
                           "spring-framework-docs": "https://docs.spring.io/spring-framework/reference",
                           "spring-data-commons-docs-url": f"https://docs.spring.io/spring-data/commons/reference/{commons}",
                           "spring-data-commons-javadoc-base": f"https://docs.spring.io/spring-data/commons/reference/{commons}/api/java",
                           "springdocsurl": "https://docs.spring.io/spring-framework/reference",
                           "springDocsUrl": "https://docs.spring.io/spring-framework/reference",
                           "springJavadocUrl": "https://docs.spring.io/spring-framework/docs/current/javadoc-api",
                           "spring-framework-javadoc": "https://docs.spring.io/spring-framework/docs/current/javadoc-api"}
    s = _antora(title, repo, f"https://docs.spring.io/spring-data/{slug}/reference/", DATA_ROOT, releases,
                pages + _DATA_SHARED, attributes)
    for boot, edition in s["editions"].items():
        edition["commons_branch"] = f"{DATA_COMMONS[boot]}.x"
    return s


def _security(title: str, pages: list[str]) -> dict:
    """Spring Security. Boot spring-boot-dependencies의 Spring Security 값 4.1.x 7.1, 4.0.x 7.0, 3.5.x 6.5.11,
    3.4.x 6.4.13 → Maven Central spring-security-bom 최신 릴리스 (2026-10-22 확인)."""
    def attributes(boot, short, release):
        return {"gh-tag": release, "spring-security-version": release, "icondir": "icons",
                "spring-framework-reference-url": "https://docs.spring.io/spring-framework/reference",
                "gh-url": f"https://github.com/spring-projects/spring-security/tree/{release}",
                "gh-samples-url": "https://github.com/spring-projects/spring-security-samples",
                "include-java": "example$docs-src", "include-kotlin": "example$docs-src", "include-xml": "example$docs-src",
                "security-api-url": f"https://docs.spring.io/spring-security/reference/{short}/api/java/"}
    return _antora(title, "spring-security", "https://docs.spring.io/spring-security/reference/", "docs/modules/ROOT",
                   _releases("7.1.1", "7.0.7", "6.5.11", "6.4.13"), pages, attributes)


def _releases(*versions: str) -> dict[str, str]:
    return dict(zip(DATA_COMMONS, versions))


def _project(title: str, repo: str, root: str, releases: tuple[str, ...]) -> dict:
    """문서 전체(pages 아래 모두)를 쓰는 Spring 프로젝트. 속성은 버전 값만 넣는다."""
    def attributes(boot, short, release):
        return {"project-version": release, "version": release, "revnumber": release, "spring-session-version": release,
                "spring-framework-reference-url": "https://docs.spring.io/spring-framework/reference"}
    return _antora(title, repo, f"https://docs.spring.io/{repo}/reference/", root, _releases(*releases),
                   ["pages/**"], attributes, gone=())


# 모듈 릴리스 버전은 spring-data-bom 2026.0.1 / 2025.1.7 / 2025.0.13 / 2024.1.13 값 (2026-10-22 확인)
_RELATIONAL = _releases("4.1.1", "4.0.7", "3.5.13", "3.4.13")


SOURCES = {
    "springdoc-openapi": {
        "repo": _SPRINGDOC["repo"], "root": "src/docs/asciidoc", "license": "Apache-2.0",
        "attributes_from": "pom.xml",  # {springdoc-version} 같은 값은 빌드 설정(pom.xml)에서 넘긴다
        # Boot 4.x ↔ springdoc 3.x(루트), Boot 3.4~3.5 ↔ springdoc 2.7~2.8(v2/)
        "editions": {
            boot: {"branch": "master", "pages": [pattern], "url": url, "page_urls": False, "label": _SPRINGDOC["label"].format(ed)}
            for boot, pattern, url, ed in [("4.1.x", "*.adoc", "https://springdoc.org/", "3.x"),
                                           ("4.0.x", "*.adoc", "https://springdoc.org/", "3.x"),
                                           ("3.5.x", "v2/*.adoc", "https://springdoc.org/v2/", "2.x"),
                                           ("3.4.x", "v2/*.adoc", "https://springdoc.org/v2/", "2.x")]
        },
    },
    "data-jdbc": _spring_data("Spring Data JDBC", "spring-data-relational", "relational", "Jdbc", _RELATIONAL,
                              ["pages/jdbc.adoc", "pages/jdbc/*.adoc"]),
    "data-r2dbc": _spring_data("Spring Data R2DBC", "spring-data-relational", "relational", "R2dbc", _RELATIONAL,
                               ["pages/r2dbc.adoc", "pages/r2dbc/*.adoc"]),
    "data-jpa": _spring_data("Spring Data JPA", "spring-data-jpa", "jpa", "Jpa", _RELATIONAL,
                             ["pages/jpa.adoc", "pages/jpa/*.adoc", "pages/envers.adoc", "pages/envers/*.adoc", "pages/auditing.adoc"]),
    "data-redis": _spring_data("Spring Data Redis", "spring-data-redis", "redis", "Redis", _RELATIONAL,
                               ["pages/redis.adoc", "pages/redis/*.adoc", "pages/redis/redis-repositories/*.adoc",
                                "pages/repositories.adoc", "pages/observability.adoc", "pages/upgrading.adoc"]),
    "data-mongodb": _spring_data("Spring Data MongoDB", "spring-data-mongodb", "mongodb", "Mongo",
                                 _releases("5.1.1", "5.0.7", "4.5.13", "4.4.13"),
                                 ["pages/mongodb.adoc", "pages/mongodb/*.adoc", "pages/mongodb/mapping/*.adoc",
                                  "pages/mongodb/repositories/*.adoc", "pages/repositories.adoc"]),
    "data-elasticsearch": _spring_data("Spring Data Elasticsearch", "spring-data-elasticsearch", "elasticsearch", "Elasticsearch",
                                       _releases("6.1.1", "6.0.7", "5.5.13", "5.4.13"),
                                       ["pages/elasticsearch.adoc", "pages/elasticsearch/*.adoc",
                                        "pages/elasticsearch/repositories/*.adoc", "pages/repositories.adoc"]),
    "security": _security("Spring Security", ["pages/*.adoc", "pages/features/**", "pages/servlet/**", "pages/reactive/**",
                                              "pages/migration/**", "pages/migration-*/**", "pages/native-image/**"]),
    "oauth2-client": _security("Spring Security", ["pages/servlet/oauth2/**", "pages/reactive/oauth2/**"]),
    # 아래 판은 Boot 의존성 설정의 값 (4.1.x/4.0.x/3.5.x/3.4.x)과 Maven Central 최신 릴리스 (2026-10-22 확인). 네 판 모두 문서가 남아 있다
    "kafka": _project("Spring for Apache Kafka", "spring-kafka", "spring-kafka-docs/src/main/antora/modules/ROOT",
                      ("4.1.1", "4.0.7", "3.3.16", "3.3.16")),
    "rabbitmq": _project("Spring AMQP", "spring-amqp", "src/reference/antora/modules/ROOT", ("4.1.1", "4.0.5", "3.2.12", "3.2.12")),
    "batch": _project("Spring Batch", "spring-batch", "spring-batch-docs/modules/ROOT", ("6.0.5", "6.0.5", "5.2.6", "5.2.6")),
    "session-data-redis": _project("Spring Session", "spring-session", "spring-session-docs/modules/ROOT",
                                   ("4.1.1", "4.0.5", "3.5.7", "3.4.7")),
    # Lombok 웹사이트의 기능 문서 (FreeMarker HTML 템플릿, 예제 코드는 usageExamples/). 판은 Boot 의존성 설정의 Lombok 값
    # 4.1.x·4.0.x 1.18.48, 3.5.x 1.18.46, 3.4.x 1.18.42 = 릴리스 태그 (2026-10-22 확인). 사이트는 최신판(1.18.48)만 보여 준다
    "lombok": {
        "repo": "projectlombok/lombok", "root": "website/templates/features", "license": "MIT",
        "editions": {boot: {"branch": f"v{v}", "pages": ["*.html", "experimental/*.html"], "page_urls": True,
                            "url": "https://projectlombok.org/features/" if v == "1.18.48" else None,
                            "page_suffix": "",  # 사이트 주소는 확장자가 없다 (/features/Data)
                            "label": f"Lombok {v} 문서"}
                     for boot, v in [("4.1.x", "1.18.48"), ("4.0.x", "1.18.48"), ("3.5.x", "1.18.46"), ("3.4.x", "1.18.42")]},
    },
    # Hibernate Validator 레퍼런스 (AsciiDoc, 장마다 파일). 판은 Boot 의존성 설정의 값 4.1.x 9.1.5, 4.0.x 9.0.2,
    # 3.5.x·3.4.x 8.0.3 = 릴리스 태그 (2026-10-22 확인). 9.1부터 장 파일이 reference/_chNN.adoc로 바뀌었다.
    # 예제 코드는 {sourcedir}(= documentation/src/test/java)의 //tag::include[] 구간이다
    "validation": {
        "repo": "hibernate/hibernate-validator", "root": "documentation/src/main/asciidoc", "license": "Apache-2.0",
        "editions": {boot: {"branch": tag, "pages": [pages], "page_urls": False,
                            "url": f"https://docs.hibernate.org/validator/{short}/reference/en-US/html_single/",
                            "label": f"Hibernate Validator {short} 문서",
                            "attributes": {"hvVersion": tag, "hvVersionShort": short,
                                           "sourcedir": "/documentation/src/test/java", "engine-sourcedir": "/engine/src/main/java"}}
                     for boot, tag, short, pages in [("4.1.x", "9.1.5.Final", "9.1", "reference/_ch*.adoc"),
                                                     ("4.0.x", "9.0.2.Final", "9.0", "ch*.asciidoc"),
                                                     ("3.5.x", "8.0.3.Final", "8.0", "ch*.asciidoc"),
                                                     ("3.4.x", "8.0.3.Final", "8.0", "ch*.asciidoc")]},
    },
    # MyBatis 스타터 (Boot 관리 밖). 판은 스타터 호환표와 각 태그 pom.xml의 spring-boot.version으로 고른 태그:
    # 4.1.x 4.1.0(Boot 4.1.0), 4.0.x 4.0.1(Initializr 값과 같음), 3.5.x·3.4.x 3.0.5(Boot 3.2~3.5) (2026-10-22 확인).
    # SQL 매퍼·동적 SQL은 MyBatis 코어 문서에 있어 함께 쓴다 (세 태그 모두 mybatis.version 3.5.19)
    "mybatis": {
        "repo": "mybatis/spring-boot-starter", "root": "mybatis-spring-boot-autoconfigure/src/site/markdown",
        "license": "Apache-2.0", "also": ["mybatis-core"],
        "must": "index.md",  # 스타터 설정 속성(mybatis.*)은 이 한 페이지에 있는데 제목이 "Introduction"이라 선별에서 밀린다
        "editions": {boot: {"branch": f"mybatis-spring-boot-{v}", "pages": ["index.md"], "page_urls": False,
                            "url": "https://mybatis.org/spring-boot-starter/mybatis-spring-boot-autoconfigure/" if v == "4.1.0" else None,
                            "label": f"MyBatis Spring Boot Starter {v} 문서"}
                     for boot, v in [("4.1.x", "4.1.0"), ("4.0.x", "4.0.1"), ("3.5.x", "3.0.5"), ("3.4.x", "3.0.5")]},
    },
    "mybatis-core": {
        "repo": "mybatis/mybatis-3", "root": "src/site/markdown", "license": "Apache-2.0",
        "editions": {boot: {"branch": "mybatis-3.5.19", "pages": ["*.md"], "page_urls": True,
                            "url": "https://mybatis.org/mybatis-3/", "label": "MyBatis 3.5.19 문서"}
                     for boot in ("4.1.x", "4.0.x", "3.5.x", "3.4.x")},
    },
    "oauth2-resource-server": _security("Spring Security", ["pages/servlet/oauth2/resource-server/**",
                                                            "pages/reactive/oauth2/resource-server/**"]),
    "security-saml2": _security("Spring Security", ["pages/servlet/saml2/**"]),
    "spring-security-webauthn": _security("Spring Security", ["pages/servlet/authentication/passkeys.adoc"]),
}
# 같은 프로젝트의 다른 스타터는 그 프로젝트 문서를 함께 쓴다 (사본도 같다)
SOURCES |= {alias: SOURCES[base] for base, aliases in {
    "data-redis": ["data-redis-reactive"], "data-mongodb": ["data-mongodb-reactive"],
    "kafka": ["kafka-streams"], "rabbitmq": ["rabbitmq-streams"], "batch": ["batch-jdbc", "batch-data-mongodb"],
    "session-data-redis": ["session-jdbc", "session-hazelcast", "session-data-mongodb"],
}.items() for alias in aliases}

INCLUDE = re.compile(r"(?m)^include::([^\[\n]+)\[[^\]\n]*\]\s*$")
DOC_EXT = (".adoc", ".asciidoc", ".html", ".md")


def _local(repo: str, branch: str, path: str) -> Path:
    return ROOT / CONFIG["paths"]["external_docs_dir"] / repo.split("/")[1] / branch / path


def _read(repo: str, branch: str, path: str, fetch: bool) -> str | None:
    """받아 둔 사본을 읽는다. fetch면 없을 때 받는다. 원문에 없는 파일이면 None."""
    local = _local(repo, branch, path)
    if not local.exists():
        if not fetch:
            return None
        try:
            text = http_get(f"https://raw.githubusercontent.com/{repo}/{branch}/{path}").text
        except Exception:  # include가 가리키는 파일이 그 판에 없을 수 있다
            return None
        local.parent.mkdir(parents=True, exist_ok=True)
        local.write_text(text, encoding="utf-8")
    return local.read_text(encoding="utf-8")


def _include_target(target: str, repo: str, branch: str, path: str) -> tuple[str, str] | None:
    """include 대상 → (저장소, 경로). Antora의 partial$, commons 페이지, 같은 폴더 상대 경로만 푼다."""
    if m := re.fullmatch(r"\{commons\}@data-commons::(?:(page|partial)\$)?(.+)", target):  # 생략하면 page
        return COMMONS_REPO, f"{DATA_ROOT}/{m[1] or 'page'}s/{m[2]}"
    if target.startswith("/"):  # 출처 속성이 저장소 루트 기준 경로로 가리킨 파일 (예: Hibernate Validator 예제 코드)
        return repo, target[1:]
    if target.startswith("example$"):
        return "", ""  # 예제 코드는 빌드할 때 테스트 소스에서 복사돼 저장소 문서 폴더에 없다. 줄을 지운다
    if repo != _SPRINGDOC["repo"] and ("{" in target or not target.split("[")[0].endswith(DOC_EXT)):
        return "", ""  # 빌드 속성으로 가리키는 소스·샘플 코드(.java, .kt, .xml 등)도 문서 사본 밖이다
    if target.startswith("partial$"):  # 포함하는 문서가 속한 Antora 모듈의 partials (저장소마다 위치가 다르다)
        module = path[:path.index("/modules/ROOT/") + len("/modules/ROOT")] if "/modules/ROOT/" in path else DATA_ROOT
        return repo, f"{module}/partials/{target.removeprefix('partial$')}"
    if repo != _SPRINGDOC["repo"] and "$" not in target and "{" not in target:
        return repo, f"{path.rsplit('/', 1)[0]}/{target}"
    return None  # 예: springdoc의 광고 조각 {docdir}/_ad-in-article.adoc. 줄은 그대로 둔다


def _freemarker(repo: str, branch: str, text: str, fetch: bool) -> str:
    """Lombok 기능 문서 템플릿을 AsciiDoc 모양의 글로 바꾼다. 매크로는 헤더로, 예제 매크로는 코드 블록으로 바꾸고 HTML 태그는 걷어낸다."""
    def snippets(m):
        pre, post = (_read(repo, branch, f"website/usageExamples/{m[1]}Example_{k}.jpage", fetch) or "" for k in ("pre", "post"))
        return f"\n== With Lombok\n\n----\n{pre.strip()}\n----\n\n== Vanilla Java\n\n----\n{post.strip()}\n----\n"
    headings = {"overview": "Overview", "experimental": "Experimental", "confKeys": "Supported configuration keys",
                "smallPrint": "Small print", "history": "History"}
    text = re.sub(r'<@f\.scaffold title="([^"]*)"\s+logline="([^"]*)"[^>]*>', "= \\1\n\n\\2\n", text)
    text = re.sub(r"<@f\.(\w+)>", lambda m: f"\n== {headings[m[1]]}\n" if m[1] in headings else "", text)
    text = re.sub(r'<@main\.h(\d) title="([^"]*)"\s*/>', lambda m: f"\n{'=' * int(m[1])} {m[2]}\n", text)
    text = re.sub(r"</?[#@](?!f\.snippets)[^>]*>", "", text)  # 남은 FreeMarker 지시문
    text = re.sub(r"(?i)</?pre[^>]*>", "\n----\n", text)
    text = re.sub(r"(?i)</?(p|br|div|dl|ol|ul)\b[^>]*>", "\n\n", text)
    text = re.sub(r"(?i)<li[^>]*>", "\n* ", text)
    text = re.sub(r"(?i)<dd[^>]*>", "\n", text)
    text = re.sub(r"(?i)</?code>", "`", text)
    text = html.unescape(re.sub(r"<(?!@f\.snippets)[^>]+>", "", text))
    text = "\n".join(line.strip() for line in text.split("\n"))  # 템플릿 들여쓰기 제거 (예제 코드는 아래에서 넣는다)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return re.sub(r'<@f\.snippets name="([^"]+)"\s*/>', snippets, text).strip() + "\n"


def _markdown(text: str) -> str:
    """MyBatis 사이트 Markdown을 AsciiDoc 모양으로: # 제목 → = 제목, ``` → ----. 코드 블록 밖의 HTML 태그와
    앞머리(title:, author:)는 지운다. 코드 블록 안(XML 매퍼 예제)은 그대로 둔다."""
    text = re.sub(r"\A(?:\s*<!--.*?-->)?(?:\s*\w+: [^\n]*\n)*", "", text, flags=re.S)  # 라이선스 주석, 앞머리
    out, fence = [], False
    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            out.append("----")
            fence = not fence
        elif fence:
            out.append(line)
        elif m := re.match(r"(#{1,6}) (.+)", line):
            out.append(f"{'=' * len(m[1])} {m[2]}")
        else:
            out.append(re.sub(r"<[^>]+>", "", re.sub(r"<h1[^>]*>.*?</h1>", "", line)))
    return "\n".join(out)


def _expand(repo: str, branch: str, path: str, fetch: bool, commons_branch: str | None = None, depth: int = 0,
            defs: dict[str, str] | None = None) -> str:
    text = _read(repo, branch, path, fetch) or ""
    if path.endswith(".html"):
        return _freemarker(repo, branch, text, fetch)
    if path.endswith(".md"):
        return _markdown(text)
    if depth > 5:
        return text
    # include 경로가 문서 속성일 수 있다 (예: :vector-search-intro-include: partial$...). 상위 문서의 정의도 물려받는다
    defs = {**(defs or {}), **dict(re.findall(r"(?m)^:([\w-]+):[ \t]*(\S.*)$", text))}
    text = re.sub(r"(?m)^include-code::.*$", "", text)  # 빌드 때 테스트 소스에서 가져오는 예제 코드 매크로. 사본에 없다

    def sub(m):
        target = re.sub(r"\{([\w-]+)\}", lambda a: defs.get(a[1], a[0]), m[1])
        found = _include_target(target, repo, branch, path)
        if not found:
            return m[0]
        if not found[0]:
            return ""
        # commons 페이지는 릴리스 묶음의 commons 판 브랜치에서 읽는다 (MongoDB 5.0 ↔ commons 4.0처럼 번호가 다르다)
        to_branch = (commons_branch or branch) if found[0] == COMMONS_REPO and repo != COMMONS_REPO else branch
        if not found[1].endswith(DOC_EXT):  # 코드 파일은 tags=이름 구간만 (// tag::이름[] ~ // end::이름[])
            code = _read(found[0], to_branch, found[1], fetch) or ""
            if tag := re.search(r"\btags?=([\w-]+)", m[0]):
                code = "".join(re.findall(rf"//\s*tag::{tag[1]}\[\]\n(.*?)//\s*end::{tag[1]}\[\]", code, re.S))
            return code.strip("\n")
        return _expand(found[0], to_branch, found[1], fetch, commons_branch, depth + 1, defs)
    return INCLUDE.sub(sub, text)


def _conditionals(text: str, attrs: dict[str, str]) -> str:
    """ifdef/ifndef/ifeval 블록을 속성 값으로 고른다. ifeval은 `값 ==/!= 값` 비교만 푼다.
    본문 안의 속성 정의(`:이름: 값`)는 attrs에 더하고 줄은 지운다."""
    out, keep = [], [True]
    for line in text.split("\n"):
        if m := re.fullmatch(r":([\w-]+):\s*(.*)", line.strip()):
            if keep[-1]:
                attrs[m[1]] = m[2]
        elif m := re.fullmatch(r"(ifdef|ifndef)::([\w-]+)\[\]", line.strip()):
            keep.append(keep[-1] and ((m[2] in attrs) == (m[1] == "ifdef")))
        elif m := re.fullmatch(r"ifeval::\[(.+?)\s*(==|!=)\s*(.+)\]", line.strip()):
            left, right = (re.sub(r"\{([\w-]+)\}", lambda a: attrs.get(a[1], ""), s).strip("\"' ") for s in (m[1], m[3]))
            keep.append(keep[-1] and ((left == right) == (m[2] == "==")))
        elif line.strip().startswith("endif::") and len(keep) > 1:
            keep.pop()
        elif keep[-1]:
            out.append(line)
    return "\n".join(out)


def _pages(s: dict, edition: dict, paths: list[str]) -> list[str]:
    """원문 경로 중 이 판의 본문 페이지. 패턴의 *는 한 폴더 안, **는 하위 폴더까지.
    밑줄 조각, nav, 최상위 index(목차 묶음)는 본문이 아니다. 하위 폴더의 index는 본문이다 (예: servlet/oauth2/index.adoc)."""
    root = s["root"] + "/"
    rels = [p.removeprefix(root) for p in paths if p.startswith(root) and p.endswith(DOC_EXT)]
    name = lambda r: r.rsplit("/", 1)[-1]
    # 밑줄 조각은 패턴이 밑줄로 시작할 때만 본문이다 (Hibernate Validator 9.1의 reference/_ch02.adoc)
    return sorted(r for r in rels if any(fnmatch(r, pat) and ("**" in pat or "/" not in r.removeprefix(pat.split("*")[0]))
                                         and (not name(r).startswith("_") or name(pat).startswith("_"))
                                         for pat in edition["pages"])
                  and name(r) != "nav.adoc"
                  and not (name(r).startswith("index.") and r.count("/") <= 1 and r not in edition["pages"]))


def download(source: str) -> int:
    """모든 판의 본문과 include 대상, 속성 파일을 받는다. 이미 받은 파일은 건너뛴다. 새로 받은 파일 수를 돌려준다."""
    s = SOURCES[source]
    before = sum(1 for _ in (ROOT / CONFIG["paths"]["external_docs_dir"]).rglob("*") if _.is_file())
    for branch in sorted({e["branch"] for e in s["editions"].values()}):
        paths = github_tree(s["repo"], branch, _local(s["repo"], branch, ".tree.json"))
        for edition in (e for e in s["editions"].values() if e["branch"] == branch):
            for rel in _pages(s, edition, paths):
                _expand(s["repo"], branch, f"{s['root']}/{rel}", fetch=True, commons_branch=edition.get("commons_branch"),
                        defs=edition.get("attributes"))
        if s.get("attributes_from"):
            _read(s["repo"], branch, s["attributes_from"], fetch=True)
    for extra in s.get("also", []):
        download(extra)
    return sum(1 for _ in (ROOT / CONFIG["paths"]["external_docs_dir"]).rglob("*") if _.is_file()) - before


def _attributes(source: str, edition: dict) -> dict[str, str]:
    """판의 문서 속성. springdoc은 pom.xml의 asciidoctor 속성(<springdoc-version>${springdoc.version}</...>)을 푼다."""
    s = SOURCES[source]
    if not s.get("attributes_from"):
        return edition.get("attributes", {})
    pom = _read(s["repo"], edition["branch"], s["attributes_from"], fetch=False) or ""
    props = dict(re.findall(r"<([\w.-]+)>([^<$]+)</\1>", pom))
    # 문서 속성만 쓴다. pom의 version·name 같은 일반 값까지 쓰면 본문의 {version} 같은 글자가 잘못 바뀐다
    return {name: props.get(prop, "") for name, prop in re.findall(r"<([\w-]+)>\$\{([\w.-]+)\}</\1>", pom)
            if name.startswith(source.split("-")[0])}


def load(source: str, version: str) -> dict[str, str]:
    """해당 Boot 버전에 맞는 판의 문서를 {doc_id: 정리된 본문}으로. doc_id 예: springdoc-openapi:v2/features.adoc,
    data-jdbc:pages/jdbc/query-methods.adoc. 출처가 없거나 아직 받지 않았으면 빈 dict."""
    s = SOURCES.get(source)
    edition = s and s["editions"].get(version)
    if not edition:
        return {}
    base = _local(s["repo"], edition["branch"], s["root"])
    paths = [f"{s['root']}/{p.relative_to(base).as_posix()}" for p in base.rglob("*")] if base.exists() else []
    docs = {}
    for rel in _pages(s, edition, paths):
        attrs = dict(_attributes(source, edition))  # 본문 속성 정의(:이름: 값)가 다른 문서로 새지 않게 문서마다 복사한다
        text = _conditionals(_expand(s["repo"], edition["branch"], f"{s['root']}/{rel}", fetch=False,
                                     commons_branch=edition.get("commons_branch"), defs=edition.get("attributes")), attrs)
        text = re.sub(r"\{([\w-]+)\}", lambda m: attrs.get(m[1], m[0]), text)
        if not re.search(r"(?m)^= ", text) and (h := re.search(r"(?m)^==+ (.+)$", text)):
            text = f"= {h[1]}\n\n{text}"  # 장 파일(== 로 시작)도 문서 제목이 있어야 후보 선별에 제목이 보인다
        docs[f"{source}:{rel}"] = clean(text)
    for extra in s.get("also", []):  # 한 항목이 여러 저장소의 문서를 쓰는 경우 (MyBatis 스타터 + MyBatis 코어)
        docs |= load(extra, version)
    return docs


def must_doc(item_id: str) -> str | None:
    """항목의 외부 문서 중 선별과 무관하게 늘 넣는 문서의 doc_id (Initializr 문서 링크가 Boot 문서가 아닌 항목용)."""
    s = SOURCES.get(item_id)
    return f"{item_id}:{s['must']}" if s and s.get("must") else None


def describe(doc_id: str, version: str) -> dict:
    """외부 문서 청크 메타데이터의 출처 값 (source_url, repo_url, source_type, license)."""
    source, rel = doc_id.split(":", 1)
    s = SOURCES[source]
    edition = s["editions"][version]
    repo_url = f"https://github.com/{s['repo']}/blob/{edition['branch']}/{s['root']}/{rel}"
    url = edition["url"]
    if url and edition["page_urls"]:
        url += re.sub(r"\.\w+$", "", rel.removeprefix("pages/")) + edition.get("page_suffix", ".html")
    return {"source_url": url or repo_url, "repo_url": repo_url, "source_type": edition["label"], "license": s["license"]}
