"""Spring Boot 문서 밖의 외부 문서 출처. 지금은 springdoc-openapi 하나다. (F2016 일부)

항목 id가 SOURCES에 있으면, 그 항목의 질문 시점 수집에서 이 문서도 후보로 검색한다.
Boot 버전마다 호환되는 판의 문서를 쓴다 (progress.md 3절 호환표).
"""
import re
from pathlib import Path

from config import CONFIG, ROOT
from data_prep.boot_docs import clean, http_get

SOURCES = {
    "springdoc-openapi": {
        "repo": "springdoc/springdoc.github.io",
        "branch": "master",
        "license": "Apache-2.0",
        # Boot 버전 → (원본 폴더, 원문 링크, 표시 이름). Boot 4.x ↔ springdoc 3.x, Boot 3.4~3.5 ↔ springdoc 2.7~2.8
        "editions": {
            "4.1.x": ("src/docs/asciidoc", "https://springdoc.org/", "springdoc-openapi 3.x 문서"),
            "4.0.x": ("src/docs/asciidoc", "https://springdoc.org/", "springdoc-openapi 3.x 문서"),
            "3.5.x": ("src/docs/asciidoc/v2", "https://springdoc.org/v2/", "springdoc-openapi 2.x 문서"),
            "3.4.x": ("src/docs/asciidoc/v2", "https://springdoc.org/v2/", "springdoc-openapi 2.x 문서"),
        },
        "attributes_from": "pom.xml",  # {springdoc-version} 같은 값은 빌드 설정(pom.xml)에서 넘긴다
    },
}


def _dir(source: str) -> Path:
    return ROOT / CONFIG["paths"]["external_docs_dir"] / source


def download(source: str) -> int:
    """모든 판의 .adoc과 속성 파일을 받는다. 이미 받은 파일은 건너뛴다. 받은 파일 수를 돌려준다."""
    s = SOURCES[source]
    folders = {folder for folder, _, _ in s["editions"].values()}
    tree = http_get(f"https://api.github.com/repos/{s['repo']}/git/trees/{s['branch']}?recursive=1",
                    Accept="application/vnd.github+json").json()
    paths = [t["path"] for t in tree["tree"]
             if t["path"].endswith(".adoc") and t["path"].rsplit("/", 1)[0] in folders]
    fetched = 0
    for path in paths + [s["attributes_from"]]:
        local = _dir(source) / path
        if local.exists():
            continue
        text = http_get(f"https://raw.githubusercontent.com/{s['repo']}/{s['branch']}/{path}").text
        local.parent.mkdir(parents=True, exist_ok=True)
        local.write_text(text, encoding="utf-8")
        fetched += 1
    return fetched


def _attributes(source: str) -> dict[str, str]:
    """pom.xml의 asciidoctor 속성(<springdoc-version>${springdoc.version}</...>)을 실제 값으로 푼다."""
    pom = (_dir(source) / SOURCES[source]["attributes_from"]).read_text(encoding="utf-8")
    props = dict(re.findall(r"<([\w.-]+)>([^<$]+)</\1>", pom))
    # 문서 속성만 쓴다. pom의 version·name 같은 일반 값까지 쓰면 본문의 {version} 같은 글자가 잘못 바뀐다
    return {name: props.get(prop, "") for name, prop in re.findall(r"<([\w-]+)>\$\{([\w.-]+)\}</\1>", pom)
            if name.startswith(source.split("-")[0])}


def load(source: str, version: str) -> dict[str, str]:
    """해당 Boot 버전에 맞는 판의 문서를 {doc_id: 정리된 본문}으로. doc_id 예: springdoc-openapi:v2/features.adoc
    출처가 없거나 아직 받지 않았으면 빈 dict."""
    edition = SOURCES.get(source, {}).get("editions", {}).get(version)
    folder = _dir(source) / edition[0] if edition else None
    if not folder or not folder.exists():
        return {}
    attrs = _attributes(source)
    docs = {}
    for p in sorted(folder.glob("*.adoc")):
        if p.name.startswith("_") or p.name == "index.adoc":  # 속성·광고 조각과 묶음 파일은 본문이 아니다
            continue
        text = re.sub(r"\{([\w-]+)\}", lambda m: attrs.get(m[1], m[0]), p.read_text(encoding="utf-8"))
        docs[f"{source}:{p.relative_to(_dir(source) / 'src/docs/asciidoc').as_posix()}"] = clean(text)
    return docs


def describe(doc_id: str, version: str) -> dict:
    """외부 문서 청크 메타데이터의 출처 값 (source_url, repo_url, source_type, license)."""
    source, rel = doc_id.split(":", 1)
    s = SOURCES[source]
    _, url, label = s["editions"][version]
    return {"source_url": url, "repo_url": f"https://github.com/{s['repo']}/blob/{s['branch']}/src/docs/asciidoc/{rel}",
            "source_type": label, "license": s["license"]}
