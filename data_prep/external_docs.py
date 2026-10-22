"""Spring Boot 문서 밖의 외부 문서 출처: springdoc-openapi, Spring Data JDBC·R2DBC. (F2016 일부)

항목 id가 SOURCES에 있으면, 그 항목의 질문 시점 수집에서 이 문서도 후보로 검색한다.
Boot 버전마다 호환되는 판(브랜치·폴더)의 문서를 쓴다 (progress.md 3절).
원문은 data/external_docs/{저장소}/{브랜치}/에 받는다. 같은 저장소를 쓰는 출처는 사본을 함께 쓴다.
"""
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


def _spring_data(title: str, repo: str, slug: str, store: str, releases: dict[str, str], pages: list[str]) -> dict:
    """releases: Boot 버전 → 모듈 릴리스 버전(BOM 값). 모듈 판(major.minor)이 브랜치 이름이다.
    docs.spring.io는 최신판(Boot 4.1.x 짝)을 버전 없는 주소로, 가장 오래된 판(3.4.x 짝)은 내려서(404) GitHub 원문을 링크한다."""
    editions = {}
    for boot, release in releases.items():
        short, commons = release.rsplit(".", 1)[0], DATA_COMMONS[boot]
        base = f"https://docs.spring.io/spring-data/{slug}/reference/"
        editions[boot] = {
            "branch": f"{short}.x", "commons_branch": f"{commons}.x", "pages": pages + _DATA_SHARED, "page_urls": True,
            "url": {"4.1.x": base, "3.4.x": None}.get(boot, f"{base}{short}/"), "label": f"{title} {short} 문서",
            "attributes": {"store": store, "version": release, "include-xml-namespaces": "false",
                           "spring-framework-docs": "https://docs.spring.io/spring-framework/reference",
                           "spring-data-commons-docs-url": f"https://docs.spring.io/spring-data/commons/reference/{commons}",
                           "spring-data-commons-javadoc-base": f"https://docs.spring.io/spring-data/commons/reference/{commons}/api/java",
                           "springdocsurl": "https://docs.spring.io/spring-framework/reference",
                           "springDocsUrl": "https://docs.spring.io/spring-framework/reference",
                           "springJavadocUrl": "https://docs.spring.io/spring-framework/docs/current/javadoc-api",
                           "spring-framework-javadoc": "https://docs.spring.io/spring-framework/docs/current/javadoc-api"},
        }
    return {"repo": f"spring-projects/{repo}", "root": DATA_ROOT, "license": "Apache-2.0", "editions": editions}


def _releases(*versions: str) -> dict[str, str]:
    return dict(zip(DATA_COMMONS, versions))


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
}

INCLUDE = re.compile(r"(?m)^include::([^\[\n]+)\[[^\]\n]*\]\s*$")


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
    if target.startswith("example$"):
        return "", ""  # 예제 코드는 빌드할 때 테스트 소스에서 복사돼 저장소 문서 폴더에 없다. 줄을 지운다
    if target.startswith("partial$"):
        return repo, f"{DATA_ROOT}/partials/{target.removeprefix('partial$')}"
    if repo != _SPRINGDOC["repo"] and "$" not in target and "{" not in target:
        return repo, f"{path.rsplit('/', 1)[0]}/{target}"
    return None  # 예: springdoc의 광고 조각 {docdir}/_ad-in-article.adoc. 줄은 그대로 둔다


def _expand(repo: str, branch: str, path: str, fetch: bool, commons_branch: str | None = None, depth: int = 0,
            defs: dict[str, str] | None = None) -> str:
    text = _read(repo, branch, path, fetch) or ""
    if depth > 5:
        return text
    # include 경로가 문서 속성일 수 있다 (예: :vector-search-intro-include: partial$...). 상위 문서의 정의도 물려받는다
    defs = {**(defs or {}), **dict(re.findall(r"(?m)^:([\w-]+):[ \t]*(\S.*)$", text))}

    def sub(m):
        target = re.sub(r"\{([\w-]+)\}", lambda a: defs.get(a[1], a[0]), m[1])
        found = _include_target(target, repo, branch, path)
        if not found:
            return m[0]
        if not found[0]:
            return ""
        # commons 페이지는 릴리스 묶음의 commons 판 브랜치에서 읽는다 (MongoDB 5.0 ↔ commons 4.0처럼 번호가 다르다)
        to_branch = (commons_branch or branch) if found[0] == COMMONS_REPO and repo != COMMONS_REPO else branch
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
    """원문 경로 중 이 판의 본문 페이지. 밑줄 조각, index, nav는 본문이 아니다."""
    root = s["root"] + "/"
    rels = [p.removeprefix(root) for p in paths if p.startswith(root) and p.endswith(".adoc")]
    return sorted(r for r in rels if any(fnmatch(r, pat) and "/" not in r.removeprefix(pat.split("*")[0])
                                         for pat in edition["pages"])
                  and not r.rsplit("/", 1)[-1].startswith("_") and r.rsplit("/", 1)[-1] not in ("index.adoc", "nav.adoc"))


def download(source: str) -> int:
    """모든 판의 본문과 include 대상, 속성 파일을 받는다. 이미 받은 파일은 건너뛴다. 새로 받은 파일 수를 돌려준다."""
    s = SOURCES[source]
    before = sum(1 for _ in (ROOT / CONFIG["paths"]["external_docs_dir"]).rglob("*") if _.is_file())
    for branch in sorted({e["branch"] for e in s["editions"].values()}):
        paths = github_tree(s["repo"], branch, _local(s["repo"], branch, ".tree.json"))
        for edition in (e for e in s["editions"].values() if e["branch"] == branch):
            for rel in _pages(s, edition, paths):
                _expand(s["repo"], branch, f"{s['root']}/{rel}", fetch=True, commons_branch=edition.get("commons_branch"))
        if s.get("attributes_from"):
            _read(s["repo"], branch, s["attributes_from"], fetch=True)
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
    paths = [f"{s['root']}/{p.relative_to(base).as_posix()}" for p in base.rglob("*.adoc")] if base.exists() else []
    docs = {}
    for rel in _pages(s, edition, paths):
        attrs = dict(_attributes(source, edition))  # 본문 속성 정의(:이름: 값)가 다른 문서로 새지 않게 문서마다 복사한다
        text = _conditionals(_expand(s["repo"], edition["branch"], f"{s['root']}/{rel}", fetch=False,
                                     commons_branch=edition.get("commons_branch")), attrs)
        text = re.sub(r"\{([\w-]+)\}", lambda m: attrs.get(m[1], m[0]), text)
        docs[f"{source}:{rel}"] = clean(text)
    return docs


def describe(doc_id: str, version: str) -> dict:
    """외부 문서 청크 메타데이터의 출처 값 (source_url, repo_url, source_type, license)."""
    source, rel = doc_id.split(":", 1)
    s = SOURCES[source]
    edition = s["editions"][version]
    repo_url = f"https://github.com/{s['repo']}/blob/{edition['branch']}/{s['root']}/{rel}"
    url = edition["url"]
    if url and edition["page_urls"]:
        url += rel.removeprefix("pages/").removesuffix(".adoc") + ".html"
    return {"source_url": url or repo_url, "repo_url": repo_url, "source_type": edition["label"], "license": s["license"]}
