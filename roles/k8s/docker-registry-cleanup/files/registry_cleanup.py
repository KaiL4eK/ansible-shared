#!/usr/bin/env python3
"""Чистка docker registry по политике retention (только stdlib).

Политика:
- Всегда защищены теги из KEEP_TAGS (точные имена) и теги, совпадающие хотя бы
  с одним регулярным выражением из KEEP_TAG_PATTERNS (например, релизные ``v*``).
- Из незащищённых в каждом репозитории храним не менее KEEP_MIN_PER_REPO
  свежайших и все, созданные за последние KEEP_DAYS дней.
- Дата тега берётся из поля ``created`` config blob его манифеста
  (для OCI-индексов берётся первый linux/amd64 дочерний манифест).
- Удаление выполняется по digest манифеста. Digest, на который ссылается любой
  сохраняемый тег, не удаляется (API реестра удаляет манифест целиком).
- Место освобождает garbage-collect самого реестра
  (CronJob docker-registry-garbage-collector из Helm-чарта), отдельно
  запускать его не нужно.

Переменные окружения:
- REGISTRY_URL        — базовый URL реестра (v2 API)
- KEEP_TAGS           — защищённые теги через запятую
- KEEP_TAG_PATTERNS   — регулярные выражения защищённых тегов через запятую
- KEEP_MIN_PER_REPO   — минимальное число хранимых тегов на репозиторий
- KEEP_DAYS           — хранить всё, созданное за последние N дней
- DRY_RUN             — "true" только показывает план удаления
- REQUEST_TIMEOUT     — таймаут одного HTTP-запроса, секунд
"""

import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

ACCEPT = ", ".join(
    [
        "application/vnd.docker.distribution.manifest.v2+json",
        "application/vnd.docker.distribution.manifest.list.v2+json",
        "application/vnd.oci.image.manifest.v1+json",
        "application/vnd.oci.image.index.v1+json",
    ]
)

INDEX_MEDIA_TYPES = {
    "application/vnd.docker.distribution.manifest.list.v2+json",
    "application/vnd.oci.image.index.v1+json",
}


def env(name, default):
    value = os.environ.get(name)
    return default if value is None or value == "" else value


REGISTRY_URL = env("REGISTRY_URL", "http://docker-registry:5000").rstrip("/")
KEEP_TAGS = {tag for tag in env("KEEP_TAGS", "latest,stable,latest-stable").split(",") if tag}
KEEP_TAG_PATTERNS = [
    re.compile(pattern)
    for pattern in env("KEEP_TAG_PATTERNS", r"^v\d+\.\d+\.\d+$,^sha256-").split(",")
    if pattern
]
KEEP_MIN_PER_REPO = int(env("KEEP_MIN_PER_REPO", "10"))
KEEP_DAYS = int(env("KEEP_DAYS", "14"))
DRY_RUN = env("DRY_RUN", "false").lower() == "true"
REQUEST_TIMEOUT = float(env("REQUEST_TIMEOUT", "30"))

manifest_cache = {}
created_cache = {}


def log(message):
    print(message, flush=True)


def request(method, path):
    req = urllib.request.Request(REGISTRY_URL + path, method=method, headers={"Accept": ACCEPT})
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as response:
            return response.status, response.read(), dict(response.headers)
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read(), dict(exc.headers)


def paginate_pages(path, key):
    """Обход постраничных ответов реестра, следующих по заголовку Link."""
    items = []
    url = path
    while url:
        status, data, headers = request("GET", url)
        if status != 200:
            raise RuntimeError("GET {}: HTTP {}".format(url, status))
        items.extend(json.loads(data).get(key) or [])
        link = headers.get("Link") or ""
        match = re.search(r'<([^>]+)>;\s*rel="next"', link)
        url = match.group(1) if match else None
    return items


def parse_created(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def resolve_manifest(repo, reference, depth=0):
    """Возвращает (digest, config_digest) манифеста, разворачивая индексы."""
    cache_key = (repo, reference)
    if cache_key in manifest_cache:
        return manifest_cache[cache_key]
    if depth > 2:
        raise RuntimeError("слишком глубокая вложенность OCI-индекса")
    path = "/v2/{}/manifests/{}".format(quote(repo, safe="/"), quote(reference, safe=":._-+"))
    status, data, headers = request("GET", path)
    if status != 200:
        raise RuntimeError("GET {}: HTTP {}".format(path, status))
    digest = headers.get("Docker-Content-Digest")
    if not digest:
        raise RuntimeError("реестр не вернул Docker-Content-Digest")
    manifest = json.loads(data)
    config_digest = None
    if manifest.get("mediaType") in INDEX_MEDIA_TYPES:
        children = manifest.get("manifests") or []
        child = next(
            (
                item["digest"]
                for item in children
                if (item.get("platform") or {}).get("architecture") == "amd64"
            ),
            children[0]["digest"] if children else None,
        )
        if child:
            _, config_digest = resolve_manifest(repo, child, depth + 1)
    else:
        config_digest = (manifest.get("config") or {}).get("digest")
    manifest_cache[cache_key] = (digest, config_digest)
    return digest, config_digest


def fetch_created(repo, config_digest):
    """Дата создания образа из config blob; None, если недоступна."""
    if config_digest is None:
        return None
    cache_key = (repo, config_digest)
    if cache_key in created_cache:
        return created_cache[cache_key]
    path = "/v2/{}/blobs/{}".format(quote(repo, safe="/"), quote(config_digest, safe=":._-+"))
    created = None
    status, data, _ = request("GET", path)
    if status == 200:
        try:
            created = parse_created(json.loads(data).get("created"))
        except (ValueError, json.JSONDecodeError):
            created = None
    created_cache[cache_key] = created
    return created


def is_protected(tag):
    if tag in KEEP_TAGS:
        return True
    return any(pattern.search(tag) for pattern in KEEP_TAG_PATTERNS)


def main():
    if KEEP_MIN_PER_REPO < 1 or KEEP_DAYS < 0:
        log("[ОШИБКА] KEEP_MIN_PER_REPO должен быть >= 1, KEEP_DAYS >= 0")
        return 2
    mode = "dry-run, удаления не выполняются" if DRY_RUN else "удаление включено"
    log("Чистка реестра {}: {} (тэги: {}, шаблоны: {}, минимум на репо: {}, дней: {})".format(
        REGISTRY_URL, mode, ",".join(sorted(KEEP_TAGS)),
        ",".join(pattern.pattern for pattern in KEEP_TAG_PATTERNS),
        KEEP_MIN_PER_REPO, KEEP_DAYS,
    ))
    repos = paginate_pages("/v2/_catalog?n=1000", "repositories")
    if not repos:
        log("Каталог пуст, удалять нечего")
        return 0
    cutoff = datetime.now(timezone.utc) - timedelta(days=KEEP_DAYS)
    min_time = datetime.min.replace(tzinfo=timezone.utc)
    stats = {
        "repos": 0, "tags": 0, "protected": 0, "kept": 0,
        "deleted": 0, "skipped": 0, "errors": 0,
    }
    for repo in repos:
        try:
            tags = paginate_pages("/v2/{}/tags/list?n=1000".format(quote(repo, safe="/")), "tags")
        except RuntimeError as exc:
            stats["errors"] += 1
            log("[ОШИБКА] {}: {}".format(repo, exc))
            continue
        if not tags:
            log("{}: тегов нет, пропуск".format(repo))
            continue
        entries = []
        for tag in tags:
            stats["tags"] += 1
            try:
                digest, config_digest = resolve_manifest(repo, tag)
            except RuntimeError as exc:
                stats["errors"] += 1
                log("[ОШИБКА] {}: {}: {}".format(repo, tag, exc))
                continue
            entries.append({
                "tag": tag,
                "digest": digest,
                "created": fetch_created(repo, config_digest),
            })
        protected = [entry for entry in entries if is_protected(entry["tag"])]
        candidates = [entry for entry in entries if not is_protected(entry["tag"])]
        candidates.sort(key=lambda entry: entry["created"] or min_time, reverse=True)
        kept_tags = {entry["tag"] for entry in protected}
        for index, entry in enumerate(candidates):
            if index < KEEP_MIN_PER_REPO or (entry["created"] and entry["created"] >= cutoff):
                kept_tags.add(entry["tag"])
        kept_digests = {entry["digest"] for entry in entries if entry["tag"] in kept_tags}
        deletable = {}
        for entry in candidates:
            if entry["tag"] not in kept_tags:
                deletable.setdefault(entry["digest"], []).append(entry["tag"])
        stats["repos"] += 1
        stats["protected"] += len(protected)
        stats["kept"] += len(kept_tags - {entry["tag"] for entry in protected})
        if not deletable:
            log("{}: тегов к удалению нет ({} защищено/сохранено)".format(repo, len(kept_tags)))
            continue
        for digest, tag_list in sorted(deletable.items()):
            if digest in kept_digests:
                stats["skipped"] += 1
                log("{}: digest {} пропущен, на него ссылается сохраняемый тег: {}".format(
                    repo, digest[:19], ", ".join(tag_list)))
                continue
            if DRY_RUN:
                stats["deleted"] += 1
                log("{}: [dry-run] удалён бы digest {} (теги: {})".format(
                    repo, digest[:19], ", ".join(tag_list)))
                continue
            path = "/v2/{}/manifests/{}".format(quote(repo, safe="/"), quote(digest, safe=":._-+"))
            status, _, _ = request("DELETE", path)
            if status in (202, 404):
                stats["deleted"] += 1
                log("{}: удалён digest {} HTTP {} (теги: {})".format(
                    repo, digest[:19], status, ", ".join(tag_list)))
            else:
                stats["errors"] += 1
                log("[ОШИБКА] {}: DELETE {} HTTP {}".format(repo, digest[:19], status))
    log(
        "Итог: репозиториев: {repos}, тегов просмотрено: {tags}, защищено: {protected}, "
        "сохранено по политике: {kept}, удалено манифестов: {deleted}, "
        "пропущено digest: {skipped}, ошибок: {errors}".format(**stats)
    )
    if not DRY_RUN and stats["deleted"]:
        log("Место освободит garbage-collect реестра (docker-registry-garbage-collector)")
    return 1 if stats["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
