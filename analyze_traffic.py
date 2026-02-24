#!/usr/bin/env python3
import argparse
import json
import os
import re
import subprocess
import sys
from collections import Counter, deque
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

LOG_FILES = ["/var/log/nginx/web-ceo.access.log", "/var/log/nginx/web-ceo.access.log.1"]
LOG_PATTERN = re.compile(
    r'^(?P<ip>\S+) \S+ \S+ \[(?P<ts>[^\]]+)\] "(?P<req>[^"]*)" (?P<status>\d{3}) \S+ "(?P<ref>[^"]*)" "(?P<ua>[^"]*)"'
)
ASSET_PATTERN = re.compile(
    r"\.(css|js|mjs|ico|png|jpg|jpeg|gif|svg|webp|avif|woff|woff2|ttf|eot|map|txt|xml)$",
    re.IGNORECASE,
)
EXACT_ASSET_PATHS = {
    "/favicon.ico",
    "/robots.txt",
    "/sitemap.xml",
    "/feed.xml",
    "/sw.js",
    "/manifest.json",
    "/site.webmanifest",
}
CONTENT_SECTION_NAMES = (
    "homepage",
    "blog",
    "tools",
    "cheatsheets",
    "datekit",
    "budgetkit",
    "healthkit",
    "sleepkit",
    "focuskit",
    "opskit",
    "studykit",
    "careerkit",
    "housingkit",
    "taxkit",
    "other",
)
KIT_SECTION_NAMES = ("datekit", "budgetkit", "healthkit", "sleepkit", "focuskit", "opskit", "studykit", "careerkit", "housingkit", "taxkit")
INTERNAL_CROSSPROPERTY_TARGETS = (
    "datekit",
    "budgetkit",
    "healthkit",
    "sleepkit",
    "focuskit",
    "opskit",
    "studykit",
    "careerkit",
    "housingkit",
    "taxkit",
)
CROSSPROMO_CAMPAIGN_NAME = "crosspromo-top-organic"
CROSSPROMO_REDIRECT_TARGETS = {
    "datekit",
    "budgetkit",
    "healthkit",
    "sleepkit",
    "focuskit",
    "opskit",
    "studykit",
    "careerkit",
    "housingkit",
    "kits",
}
INFERRED_SOURCE_LOOKBACK = timedelta(minutes=30)
INFERRED_SOURCE_MAX_RECENT_PATHS = 200
INFERRED_SOURCE_SECTION_PATHS = {
    "homepage": "/",
    "blog": "/blog",
    "tools": "/tools",
    "cheatsheets": "/cheatsheets",
    "datekit": "/datekit",
    "budgetkit": "/budgetkit",
    "healthkit": "/healthkit",
    "sleepkit": "/sleepkit",
    "focuskit": "/focuskit",
    "opskit": "/opskit",
    "studykit": "/studykit",
    "careerkit": "/careerkit",
    "housingkit": "/housingkit",
    "taxkit": "/taxkit",
}
BLOG_SLUG_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")
ENGINE_PATTERNS = [
    (re.compile(r"google\.", re.IGNORECASE), "google"),
    (re.compile(r"bing\.", re.IGNORECASE), "bing"),
    (re.compile(r"duckduckgo\.", re.IGNORECASE), "duckduckgo"),
    (re.compile(r"yahoo\.", re.IGNORECASE), "yahoo"),
    (re.compile(r"ecosia\.", re.IGNORECASE), "ecosia"),
    (re.compile(r"qwant\.", re.IGNORECASE), "qwant"),
    (re.compile(r"aol\.", re.IGNORECASE), "aol"),
    (re.compile(r"search\.brave\.com", re.IGNORECASE), "brave"),
    (re.compile(r"yandex\.", re.IGNORECASE), "yandex"),
]
BOT_UA_PATTERNS = [
    re.compile(r"(?:^|[^a-z])(bot|crawler|spider|slurp)(?:[^a-z]|$)", re.IGNORECASE),
    re.compile(r"(?:^|[^a-z])(headless|lighthouse|pagespeed)(?:[^a-z]|$)", re.IGNORECASE),
    re.compile(r"(?:^|[^a-z])(curl|wget|python-requests|scrapy|httpclient|go-http-client)(?:[^a-z]|$)", re.IGNORECASE),
]
SUSPECTED_CROSSPROMO_DATACENTER_IP_PREFIXES = (
    "43.130.",
    "43.131.",
    "43.132.",
    "43.133.",
    "43.135.",
    "43.152.",
    "43.153.",
    "43.155.",
    "43.156.",
    "43.157.",
    "43.158.",
    "43.166.",
    "43.167.",
    "49.51.",
    "101.33.",
    "124.156.",
    "170.106.",
)
SUSPECTED_CROSSPROMO_SPOOFED_MOBILE_UA = re.compile(
    r"^Mozilla/5\.0 \(iPhone; CPU iPhone OS 13_2_3 like Mac OS X\) AppleWebKit/605\.1\.15 "
    r"\(KHTML, like Gecko\) Version/13\.0\.3 Mobile/15E148 Safari/604\.1$"
)
SUSPICIOUS_PATH_PATTERNS = [
    re.compile(r"^/(?:wp-admin(?:/|$)|wp-login\.php$|xmlrpc\.php$)", re.IGNORECASE),
    re.compile(r"/vendor/phpunit/", re.IGNORECASE),
    re.compile(r"^/(?:phpunit|lib/phpunit)/", re.IGNORECASE),
    re.compile(r"\.(?:php(?:\d+)?|phtml|phar)$", re.IGNORECASE),
    re.compile(r"/\.env(?:[._-][^/]*)?$", re.IGNORECASE),
    re.compile(r"^/wp-config", re.IGNORECASE),
    re.compile(
        r"(?:^|/)(?:phpinfo|phpsysinfo|php-info|php[_-]?details?|phpinformation|infophp|testphp(?:info)?|pinfo|php\.ini)(?:$|[/.])",
        re.IGNORECASE,
    ),
    re.compile(r"^/\.(?!well-known/)", re.IGNORECASE),
    re.compile(r"^/(?:wp-config\.php|web\.config|configuration\.php|config\.json|secrets\.json|credentials\.json)$", re.IGNORECASE),
    re.compile(r"^/(?:public/hot|public/storage|containers/json|storage/\*\.key)$", re.IGNORECASE),
    re.compile(r"^/(?:bin/sh|hello\.world|manager/html|shell|version|v1)$", re.IGNORECASE),
    re.compile(r"^/(?:boaform/|actuator/|geoserver/web/|developmentserver/metadatauploader)", re.IGNORECASE),
    re.compile(r"^/(?:\.emacs\.desktop(?:\.lock)?|eshell/(?:lastdir|history)|elpa/|auto/)$", re.IGNORECASE),
    re.compile(r"^/(?:webui/|admin(?:/config\.php)?$|login$|aaa9$|aab9$)", re.IGNORECASE),
    re.compile(r"^/(?:backup|dump|database)\.sql$", re.IGNORECASE),
    re.compile(r"^/(?:phpinfo\.php|composer\.json|docker-compose\.yml|bitbucket-pipelines\.yml)$", re.IGNORECASE),
    re.compile(r"^/wp-config\.php(?:\.(?:bak|old|save|orig))?$", re.IGNORECASE),
    re.compile(r"^/(?:var/log/|usr/bin/|path/to/|bins/)", re.IGNORECASE),
    re.compile(r"%7c_", re.IGNORECASE),
    re.compile(r"\|_", re.IGNORECASE),
    re.compile(r"/\.git/config$", re.IGNORECASE),
    re.compile(r"^/gponform/diag_form$", re.IGNORECASE),
    re.compile(r"^/.+\.(?:php|ini|cfg|conf|ya?ml|json|sql|log|key|env)(?:\.(?:bak|old|orig|save)|~)$", re.IGNORECASE),
    re.compile(
        r"^/(?:config(?:uration)?|settings|credentials|secrets?|database|db|appsettings|application|serverless)\.(?:php|ini|cfg|conf|ya?ml|json|properties|sql)$",
        re.IGNORECASE,
    ),
    re.compile(r"^/docker-compose(?:\.override)?\.(?:yml|yaml)$", re.IGNORECASE),
    re.compile(r"^/(?:app/)?config(?:/|$)", re.IGNORECASE),
    re.compile(r"^/(?:server-status|server-info)$", re.IGNORECASE),
    re.compile(r"^/(?:debug|error)\.log$", re.IGNORECASE),
    re.compile(r"^/(?:local_)?settings\.py$", re.IGNORECASE),
    re.compile(r"^/(?:instance/)?config\.py$", re.IGNORECASE),
    re.compile(r"^/appsettings(?:\.[^/]+)?\.json$", re.IGNORECASE),
    re.compile(r"^/terraform\.tfvars$", re.IGNORECASE),
    re.compile(r"^/(?:package\.json|package-lock\.json|composer\.lock|yarn\.lock|pnpm-lock\.yaml)$", re.IGNORECASE),
    re.compile(r"^/_next(?:/|$)", re.IGNORECASE),
]


def read_log_lines(path: str):
    if not os.path.exists(path):
        return []
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.readlines()
    except PermissionError:
        output = subprocess.check_output(["sudo", "-n", "cat", path], text=True, stderr=subprocess.DEVNULL)
        return output.splitlines(keepends=True)


def parse_request_path_query(request: str):
    parts = request.split()
    if len(parts) < 2:
        return "", ""
    target = parts[1].strip()
    path, _, query = target.partition("?")
    normalized = normalize_path(path or "/")
    return (normalized or "/"), query


def normalize_path(path: str) -> str:
    if not path:
        return ""
    raw_path = path.strip()
    if not raw_path:
        return ""
    if "://" in raw_path:
        try:
            parsed = urlparse(raw_path)
        except ValueError:
            return ""
        raw_path = parsed.path or "/"
    if not raw_path.startswith("/"):
        raw_path = f"/{raw_path}"
    normalized = re.sub(r"/{2,}", "/", raw_path)
    if len(normalized) > 1:
        normalized = normalized.rstrip("/")
    return normalized or "/"


def is_asset_path(path: str) -> bool:
    if not path:
        return True
    if path in EXACT_ASSET_PATHS:
        return True
    if path.startswith("/assets/") or path.startswith("/static/"):
        return True
    return bool(ASSET_PATTERN.search(path))


def classify_content_section(path: str) -> str:
    path = normalize_path(path) or "/"
    if path == "/":
        return "homepage"
    if path == "/blog" or path.startswith("/blog/"):
        return "blog"
    if path == "/tools" or path.startswith("/tools/"):
        return "tools"
    if path == "/cheatsheets" or path.startswith("/cheatsheets/"):
        return "cheatsheets"
    if path == "/datekit" or path.startswith("/datekit/"):
        return "datekit"
    if path == "/budgetkit" or path.startswith("/budgetkit/"):
        return "budgetkit"
    if path == "/healthkit" or path.startswith("/healthkit/"):
        return "healthkit"
    if path == "/sleepkit" or path.startswith("/sleepkit/"):
        return "sleepkit"
    if path == "/focuskit" or path.startswith("/focuskit/"):
        return "focuskit"
    if path == "/opskit" or path.startswith("/opskit/"):
        return "opskit"
    if path == "/studykit" or path.startswith("/studykit/"):
        return "studykit"
    if path == "/careerkit" or path.startswith("/careerkit/"):
        return "careerkit"
    if path == "/housingkit" or path.startswith("/housingkit/"):
        return "housingkit"
    if path == "/taxkit" or path.startswith("/taxkit/"):
        return "taxkit"
    return "other"


def detect_engine(referrer: str) -> str:
    for pattern, name in ENGINE_PATTERNS:
        if pattern.search(referrer):
            return name
    return ""


def normalize_user_agent(user_agent: str) -> str:
    value = (user_agent or "").strip()
    if value == "-":
        return ""
    return value


def is_known_bot_user_agent(user_agent: str) -> bool:
    normalized = normalize_user_agent(user_agent)
    if not normalized:
        return False
    for pattern in BOT_UA_PATTERNS:
        if pattern.search(normalized):
            return True
    return False


def is_suspected_crosspromo_automation(ip: str, normalized_user_agent: str, referrer: str, query: str) -> bool:
    if f"utm_campaign={CROSSPROMO_CAMPAIGN_NAME}" not in query:
        return False
    if referrer and referrer != "-":
        return False
    if not normalized_user_agent:
        return False
    if not SUSPECTED_CROSSPROMO_SPOOFED_MOBILE_UA.fullmatch(normalized_user_agent):
        return False
    return ip.startswith(SUSPECTED_CROSSPROMO_DATACENTER_IP_PREFIXES)


def is_crosspromo_redirect_hop(path: str) -> bool:
    normalized = normalize_path(path)
    if not normalized.startswith("/go/"):
        return False
    target = normalized.removeprefix("/go/").strip("/")
    return target in CROSSPROMO_REDIRECT_TARGETS


def parse_internal_referrer_path(referrer: str) -> str:
    if not referrer or referrer == "-":
        return ""
    try:
        parsed = urlparse(referrer)
    except ValueError:
        return ""
    host = (parsed.netloc or "").lower()
    if host.startswith("www."):
        host = host[4:]
    if host != "devtoolbox.dedyn.io":
        return ""
    return normalize_path(parsed.path or "/")


def infer_internal_source_path(source: str) -> str:
    candidate = (source or "").strip()
    if not candidate:
        return ""
    if candidate.startswith(("http://", "https://")):
        try:
            parsed = urlparse(candidate)
        except ValueError:
            return ""
        host = (parsed.netloc or "").lower()
        if host.startswith("www."):
            host = host[4:]
        if host != "devtoolbox.dedyn.io":
            return ""
        return normalize_path(parsed.path or "/")
    if candidate.startswith("/"):
        return normalize_path(candidate)
    section_path = INFERRED_SOURCE_SECTION_PATHS.get(candidate.lower())
    if section_path:
        return section_path
    slug_candidate = candidate.lower()
    if BLOG_SLUG_PATTERN.fullmatch(slug_candidate):
        return f"/blog/{slug_candidate}"
    return ""


def is_suspicious_path(path: str) -> bool:
    if not path:
        return False
    for pattern in SUSPICIOUS_PATH_PATTERNS:
        if pattern.search(path):
            return True
    return False


def counter_to_sorted_list(counter: Counter, key_name: str, max_items: int | None = None):
    if max_items is None or max_items < 0:
        items = counter.most_common()
    else:
        items = counter.most_common(max_items)
    return [{key_name: key, "count": count} for key, count in items]


def safe_ratio(part: int, whole: int) -> float:
    if whole <= 0:
        return 0.0
    return round((part / whole) * 100, 2)


def safe_pct_change(current: int, previous: int):
    if previous <= 0:
        return None
    return round(((current - previous) / previous) * 100, 2)


class WindowStats:
    def __init__(self):
        self.total_requests = 0
        self.clean_requests = 0
        self.content_requests = 0
        self.suspicious_requests = 0
        self.unique_ips = set()
        self.clean_unique_ips = set()
        self.content_unique_ips = set()
        self.suspicious_unique_ips = set()
        self.status_counts = Counter()
        self.page_counts = Counter()
        self.content_section_counts = Counter()
        self.organic_engine_counts = Counter()
        self.organic_page_counts = Counter()
        self.organic_section_counts = Counter()
        self.organic_non_bot_engine_counts = Counter()
        self.organic_non_bot_page_counts = Counter()
        self.organic_non_bot_section_counts = Counter()
        self.external_referrers = Counter()
        self.not_found_pages = Counter()
        self.clean_not_found_pages = Counter()
        self.suspicious_paths = Counter()
        self.suspicious_not_found_pages = Counter()
        self.crosspromo_campaign_hits = 0
        self.crosspromo_campaign_pages = Counter()
        self.crosspromo_campaign_sources = Counter()
        self.crosspromo_campaign_source_pages = Counter()
        self.crosspromo_campaign_source_sections = Counter()
        self.crosspromo_campaign_target_sections = Counter()
        self.crosspromo_campaign_source_target_sections = Counter()
        self.crosspromo_campaign_page_path_pairs = Counter()
        self.crosspromo_hits_with_internal_referrer = 0
        self.crosspromo_hits_with_inferred_source = 0
        self.crosspromo_hits_unattributed = 0
        self.crosspromo_non_bot_campaign_sources = Counter()
        self.crosspromo_non_bot_campaign_source_pages = Counter()
        self.crosspromo_non_bot_campaign_source_sections = Counter()
        self.crosspromo_non_bot_campaign_target_sections = Counter()
        self.crosspromo_non_bot_campaign_source_target_sections = Counter()
        self.crosspromo_non_bot_campaign_page_path_pairs = Counter()
        self.crosspromo_non_bot_hits_with_internal_referrer = 0
        self.crosspromo_non_bot_hits_with_inferred_source = 0
        self.crosspromo_non_bot_hits_unattributed = 0
        self.crosspromo_inferred_verified_hits = 0
        self.crosspromo_inferred_unverified_hits = 0
        self.crosspromo_non_bot_inferred_verified_hits = 0
        self.crosspromo_non_bot_inferred_unverified_hits = 0
        self.crosspromo_hits_with_param_source = 0
        self.crosspromo_non_bot_hits_with_param_source = 0
        self.crosspromo_hits_with_param_source_without_referrer = 0
        self.crosspromo_non_bot_hits_with_param_source_without_referrer = 0
        self.crosspromo_campaign_param_source_pages = Counter()
        self.crosspromo_campaign_param_source_sections = Counter()
        self.crosspromo_non_bot_campaign_param_source_pages = Counter()
        self.crosspromo_non_bot_campaign_param_source_sections = Counter()
        self.crosspromo_source_mismatch_hits = 0
        self.internal_crossproperty_referrals = 0
        self.internal_crossproperty_target_sections = Counter()
        self.internal_crossproperty_source_sections = Counter()
        self.internal_crossproperty_target_pages = Counter()
        self.internal_crossproperty_source_pages = Counter()
        self.internal_crossproperty_non_bot_referrals = 0
        self.internal_crossproperty_non_bot_target_sections = Counter()
        self.internal_crossproperty_non_bot_source_sections = Counter()
        self.internal_crossproperty_non_bot_target_pages = Counter()
        self.internal_crossproperty_non_bot_source_pages = Counter()
        self.internal_crossproperty_inferred_referrals = 0
        self.internal_crossproperty_inferred_target_sections = Counter()
        self.internal_crossproperty_inferred_non_bot_referrals = 0
        self.internal_crossproperty_inferred_non_bot_target_sections = Counter()
        self.internal_crossproperty_inferred_verified_referrals = 0
        self.internal_crossproperty_inferred_verified_target_sections = Counter()
        self.internal_crossproperty_inferred_non_bot_verified_referrals = 0
        self.internal_crossproperty_inferred_non_bot_verified_target_sections = Counter()
        self.internal_crossproperty_inferred_unverified_referrals = 0
        self.internal_crossproperty_inferred_unverified_target_sections = Counter()
        self.internal_crossproperty_inferred_non_bot_unverified_referrals = 0
        self.internal_crossproperty_inferred_non_bot_unverified_target_sections = Counter()
        self.known_bot_requests = 0
        self.known_bot_unique_ips = set()
        self.crosspromo_known_bot_hits = 0
        self.crosspromo_known_bot_user_agents = Counter()
        self.crosspromo_hits_with_any_referrer = 0
        self.crosspromo_hits_without_referrer = 0
        self.crosspromo_non_bot_hits_with_any_referrer = 0
        self.crosspromo_non_bot_hits_without_referrer = 0
        self.crosspromo_hits_without_referrer_known_bot = 0
        self.crosspromo_suspected_automation_hits = 0
        self.crosspromo_suspected_automation_unique_ips = set()
        self.crosspromo_suspected_automation_user_agents = Counter()
        self.recent_content_paths_by_client: dict[tuple[str, str], deque[tuple[datetime, str]]] = {}

    @staticmethod
    def _client_key(ip: str, normalized_user_agent: str) -> tuple[str, str]:
        if normalized_user_agent:
            return (ip, normalized_user_agent)
        return (ip, "")

    @staticmethod
    def _trim_recent_paths(paths: deque[tuple[datetime, str]], cutoff: datetime):
        while paths and paths[0][0] < cutoff:
            paths.popleft()

    def _has_recent_inferred_source_match(self, client_key: tuple[str, str], inferred_paths: set[str], ts: datetime) -> bool:
        if not inferred_paths:
            return False
        recent_paths = self.recent_content_paths_by_client.get(client_key)
        if not recent_paths:
            return False
        cutoff = ts - INFERRED_SOURCE_LOOKBACK
        self._trim_recent_paths(recent_paths, cutoff)
        if not recent_paths:
            return False
        for _, candidate_path in recent_paths:
            if candidate_path in inferred_paths:
                return True
        return False

    def _remember_recent_content_path(self, client_key: tuple[str, str], ts: datetime, path: str):
        recent_paths = self.recent_content_paths_by_client.get(client_key)
        if recent_paths is None:
            recent_paths = deque()
            self.recent_content_paths_by_client[client_key] = recent_paths
        cutoff = ts - INFERRED_SOURCE_LOOKBACK
        self._trim_recent_paths(recent_paths, cutoff)
        recent_paths.append((ts, path))
        while len(recent_paths) > INFERRED_SOURCE_MAX_RECENT_PATHS:
            recent_paths.popleft()

    def record(self, ip: str, status: str, referrer: str, path: str, query: str, user_agent: str, ts: datetime):
        asset = is_asset_path(path)
        suspicious_path = is_suspicious_path(path)
        internal_referrer_path = parse_internal_referrer_path(referrer)
        normalized_user_agent = normalize_user_agent(user_agent)
        known_bot_ua = is_known_bot_user_agent(normalized_user_agent)
        client_key = self._client_key(ip, normalized_user_agent)

        self.total_requests += 1
        self.unique_ips.add(ip)
        self.status_counts[status] += 1
        if known_bot_ua:
            self.known_bot_requests += 1
            self.known_bot_unique_ips.add(ip)

        if suspicious_path:
            self.suspicious_requests += 1
            self.suspicious_unique_ips.add(ip)
            if path:
                self.suspicious_paths[path] += 1
        else:
            self.clean_requests += 1
            self.clean_unique_ips.add(ip)
            if not asset and path:
                self.content_requests += 1
                self.content_unique_ips.add(ip)
                section = classify_content_section(path)
                self.content_section_counts[section] += 1

        if not asset and path:
            self.page_counts[path] += 1
            if status == "404":
                self.not_found_pages[path] += 1
                if suspicious_path:
                    self.suspicious_not_found_pages[path] += 1
                else:
                    self.clean_not_found_pages[path] += 1
            if f"utm_campaign={CROSSPROMO_CAMPAIGN_NAME}" in query and not is_crosspromo_redirect_hop(path):
                self.crosspromo_campaign_hits += 1
                self.crosspromo_campaign_pages[path] += 1
                target_section = classify_content_section(path)
                suspected_crosspromo_automation = is_suspected_crosspromo_automation(
                    ip,
                    normalized_user_agent,
                    referrer,
                    query,
                )
                crosspromo_known_bot = known_bot_ua or suspected_crosspromo_automation
                if suspected_crosspromo_automation:
                    self.crosspromo_suspected_automation_hits += 1
                    self.crosspromo_suspected_automation_unique_ips.add(ip)
                    if normalized_user_agent:
                        self.crosspromo_suspected_automation_user_agents[normalized_user_agent] += 1
                self.crosspromo_campaign_target_sections[target_section] += 1
                if not crosspromo_known_bot:
                    self.crosspromo_non_bot_campaign_target_sections[target_section] += 1
                if referrer and referrer != "-":
                    self.crosspromo_hits_with_any_referrer += 1
                    if not crosspromo_known_bot:
                        self.crosspromo_non_bot_hits_with_any_referrer += 1
                else:
                    self.crosspromo_hits_without_referrer += 1
                    if not crosspromo_known_bot:
                        self.crosspromo_non_bot_hits_without_referrer += 1
                if crosspromo_known_bot:
                    self.crosspromo_known_bot_hits += 1
                    if normalized_user_agent:
                        self.crosspromo_known_bot_user_agents[normalized_user_agent] += 1
                    if not referrer or referrer == "-":
                        self.crosspromo_hits_without_referrer_known_bot += 1
                params = parse_qs(query, keep_blank_values=False)
                inferred_source_paths: list[str] = []
                for source in params.get("utm_content", []):
                    source = source.strip()
                    if not source:
                        continue
                    self.crosspromo_campaign_sources[source] += 1
                    self.crosspromo_campaign_source_target_sections[f"{source}->{target_section}"] += 1
                    if not crosspromo_known_bot:
                        self.crosspromo_non_bot_campaign_sources[source] += 1
                        self.crosspromo_non_bot_campaign_source_target_sections[f"{source}->{target_section}"] += 1
                    inferred_source_path = infer_internal_source_path(source)
                    if inferred_source_path:
                        inferred_source_paths.append(inferred_source_path)
                normalized_inferred_paths = set()
                for inferred_source_path in inferred_source_paths:
                    normalized_inferred_path = normalize_path(inferred_source_path)
                    if normalized_inferred_path:
                        normalized_inferred_paths.add(normalized_inferred_path)
                if normalized_inferred_paths:
                    self.crosspromo_hits_with_param_source += 1
                    if not crosspromo_known_bot:
                        self.crosspromo_non_bot_hits_with_param_source += 1
                    if not referrer or referrer == "-":
                        self.crosspromo_hits_with_param_source_without_referrer += 1
                        if not crosspromo_known_bot:
                            self.crosspromo_non_bot_hits_with_param_source_without_referrer += 1
                    for normalized_source_path in normalized_inferred_paths:
                        source_section = classify_content_section(normalized_source_path)
                        self.crosspromo_campaign_param_source_pages[normalized_source_path] += 1
                        self.crosspromo_campaign_param_source_sections[source_section] += 1
                        if not crosspromo_known_bot:
                            self.crosspromo_non_bot_campaign_param_source_pages[normalized_source_path] += 1
                            self.crosspromo_non_bot_campaign_param_source_sections[source_section] += 1
                if internal_referrer_path:
                    self.crosspromo_hits_with_internal_referrer += 1
                    source_section = classify_content_section(internal_referrer_path)
                    self.crosspromo_campaign_source_pages[internal_referrer_path] += 1
                    self.crosspromo_campaign_source_sections[source_section] += 1
                    self.crosspromo_campaign_page_path_pairs[f"{internal_referrer_path}->{path}"] += 1
                    if not crosspromo_known_bot:
                        self.crosspromo_non_bot_hits_with_internal_referrer += 1
                        self.crosspromo_non_bot_campaign_source_pages[internal_referrer_path] += 1
                        self.crosspromo_non_bot_campaign_source_sections[source_section] += 1
                        self.crosspromo_non_bot_campaign_page_path_pairs[f"{internal_referrer_path}->{path}"] += 1
                    if normalized_inferred_paths and internal_referrer_path not in normalized_inferred_paths:
                        self.crosspromo_source_mismatch_hits += 1
                elif inferred_source_paths:
                    self.crosspromo_hits_with_inferred_source += 1
                    if not crosspromo_known_bot:
                        self.crosspromo_non_bot_hits_with_inferred_source += 1
                    inferred_source_verified = self._has_recent_inferred_source_match(client_key, normalized_inferred_paths, ts)
                    if inferred_source_verified:
                        self.crosspromo_inferred_verified_hits += 1
                        if not crosspromo_known_bot:
                            self.crosspromo_non_bot_inferred_verified_hits += 1
                    else:
                        self.crosspromo_inferred_unverified_hits += 1
                        if not crosspromo_known_bot:
                            self.crosspromo_non_bot_inferred_unverified_hits += 1
                    recorded_paths = set()
                    inferred_internal_crossproperty_recorded = False
                    for inferred_source_path in inferred_source_paths:
                        normalized_source_path = normalize_path(inferred_source_path)
                        if not normalized_source_path or normalized_source_path in recorded_paths:
                            continue
                        recorded_paths.add(normalized_source_path)
                        source_section = classify_content_section(normalized_source_path)
                        if (
                            not inferred_internal_crossproperty_recorded
                            and target_section in INTERNAL_CROSSPROPERTY_TARGETS
                            and source_section != target_section
                        ):
                            self.internal_crossproperty_inferred_referrals += 1
                            self.internal_crossproperty_inferred_target_sections[target_section] += 1
                            if inferred_source_verified:
                                self.internal_crossproperty_inferred_verified_referrals += 1
                                self.internal_crossproperty_inferred_verified_target_sections[target_section] += 1
                            else:
                                self.internal_crossproperty_inferred_unverified_referrals += 1
                                self.internal_crossproperty_inferred_unverified_target_sections[target_section] += 1
                            if not crosspromo_known_bot:
                                self.internal_crossproperty_inferred_non_bot_referrals += 1
                                self.internal_crossproperty_inferred_non_bot_target_sections[target_section] += 1
                                if inferred_source_verified:
                                    self.internal_crossproperty_inferred_non_bot_verified_referrals += 1
                                    self.internal_crossproperty_inferred_non_bot_verified_target_sections[target_section] += 1
                                else:
                                    self.internal_crossproperty_inferred_non_bot_unverified_referrals += 1
                                    self.internal_crossproperty_inferred_non_bot_unverified_target_sections[target_section] += 1
                            inferred_internal_crossproperty_recorded = True
                        self.crosspromo_campaign_source_pages[normalized_source_path] += 1
                        self.crosspromo_campaign_source_sections[source_section] += 1
                        self.crosspromo_campaign_page_path_pairs[f"{normalized_source_path}->{path}"] += 1
                        if not crosspromo_known_bot:
                            self.crosspromo_non_bot_campaign_source_pages[normalized_source_path] += 1
                            self.crosspromo_non_bot_campaign_source_sections[source_section] += 1
                            self.crosspromo_non_bot_campaign_page_path_pairs[f"{normalized_source_path}->{path}"] += 1
                else:
                    self.crosspromo_hits_unattributed += 1
                    if not crosspromo_known_bot:
                        self.crosspromo_non_bot_hits_unattributed += 1

        if referrer and referrer != "-":
            if not internal_referrer_path:
                self.external_referrers[referrer] += 1
            engine = detect_engine(referrer)
            if engine and not asset and path and not suspicious_path:
                self.organic_engine_counts[engine] += 1
                self.organic_page_counts[path] += 1
                section = classify_content_section(path)
                self.organic_section_counts[section] += 1
                if not known_bot_ua:
                    self.organic_non_bot_engine_counts[engine] += 1
                    self.organic_non_bot_page_counts[path] += 1
                    self.organic_non_bot_section_counts[section] += 1

        if internal_referrer_path and not asset and path and not suspicious_path:
            source_section = classify_content_section(internal_referrer_path)
            target_section = classify_content_section(path)
            if target_section in INTERNAL_CROSSPROPERTY_TARGETS and source_section != target_section:
                self.internal_crossproperty_referrals += 1
                self.internal_crossproperty_target_sections[target_section] += 1
                self.internal_crossproperty_source_sections[source_section] += 1
                self.internal_crossproperty_target_pages[path] += 1
                self.internal_crossproperty_source_pages[internal_referrer_path] += 1
                if not known_bot_ua:
                    self.internal_crossproperty_non_bot_referrals += 1
                    self.internal_crossproperty_non_bot_target_sections[target_section] += 1
                    self.internal_crossproperty_non_bot_source_sections[source_section] += 1
                    self.internal_crossproperty_non_bot_target_pages[path] += 1
                    self.internal_crossproperty_non_bot_source_pages[internal_referrer_path] += 1

        if not asset and path and not suspicious_path:
            self._remember_recent_content_path(client_key, ts, path)

    def summary(self, generated_at: str, window_hours: int):
        organic_total = sum(self.organic_engine_counts.values())
        organic_non_bot_total = sum(self.organic_non_bot_engine_counts.values())
        not_found_total = sum(self.not_found_pages.values())
        clean_404 = sum(self.clean_not_found_pages.values())
        suspicious_404 = sum(self.suspicious_not_found_pages.values())
        content_sections = {name: int(self.content_section_counts.get(name, 0)) for name in CONTENT_SECTION_NAMES}
        organic_sections = {name: int(self.organic_section_counts.get(name, 0)) for name in CONTENT_SECTION_NAMES}
        organic_non_bot_sections = {name: int(self.organic_non_bot_section_counts.get(name, 0)) for name in CONTENT_SECTION_NAMES}
        content_section_share = {name: safe_ratio(content_sections[name], self.content_requests) for name in CONTENT_SECTION_NAMES}
        organic_section_share = {name: safe_ratio(organic_sections[name], organic_total) for name in CONTENT_SECTION_NAMES}
        organic_non_bot_section_share = {
            name: safe_ratio(organic_non_bot_sections[name], organic_non_bot_total) for name in CONTENT_SECTION_NAMES
        }
        organic_kit_referrals = sum(organic_sections[name] for name in KIT_SECTION_NAMES)
        organic_non_bot_kit_referrals = sum(organic_non_bot_sections[name] for name in KIT_SECTION_NAMES)
        organic_non_bot_kit_page_counts = Counter()
        for page_path, count in self.organic_non_bot_page_counts.items():
            if classify_content_section(page_path) in KIT_SECTION_NAMES:
                organic_non_bot_kit_page_counts[page_path] = count

        top_content_section = "other"
        top_content_section_requests = 0
        top_organic_section = "other"
        top_organic_section_referrals = 0
        top_organic_non_bot_section = "other"
        top_organic_non_bot_section_referrals = 0
        top_organic_non_bot_page = ""
        top_organic_non_bot_page_hits = 0
        top_organic_non_bot_kit_section = "other"
        top_organic_non_bot_kit_section_referrals = 0
        top_organic_non_bot_kit_page = ""
        top_organic_non_bot_kit_page_hits = 0
        internal_to_datekit = int(self.internal_crossproperty_target_sections.get("datekit", 0))
        internal_to_budgetkit = int(self.internal_crossproperty_target_sections.get("budgetkit", 0))
        internal_to_healthkit = int(self.internal_crossproperty_target_sections.get("healthkit", 0))
        internal_to_sleepkit = int(self.internal_crossproperty_target_sections.get("sleepkit", 0))
        internal_to_focuskit = int(self.internal_crossproperty_target_sections.get("focuskit", 0))
        internal_to_opskit = int(self.internal_crossproperty_target_sections.get("opskit", 0))
        internal_to_studykit = int(self.internal_crossproperty_target_sections.get("studykit", 0))
        internal_to_careerkit = int(self.internal_crossproperty_target_sections.get("careerkit", 0))
        internal_to_housingkit = int(self.internal_crossproperty_target_sections.get("housingkit", 0))
        internal_to_taxkit = int(self.internal_crossproperty_target_sections.get("taxkit", 0))
        internal_non_bot_to_datekit = int(self.internal_crossproperty_non_bot_target_sections.get("datekit", 0))
        internal_non_bot_to_budgetkit = int(self.internal_crossproperty_non_bot_target_sections.get("budgetkit", 0))
        internal_non_bot_to_healthkit = int(self.internal_crossproperty_non_bot_target_sections.get("healthkit", 0))
        internal_non_bot_to_sleepkit = int(self.internal_crossproperty_non_bot_target_sections.get("sleepkit", 0))
        internal_non_bot_to_focuskit = int(self.internal_crossproperty_non_bot_target_sections.get("focuskit", 0))
        internal_non_bot_to_opskit = int(self.internal_crossproperty_non_bot_target_sections.get("opskit", 0))
        internal_non_bot_to_studykit = int(self.internal_crossproperty_non_bot_target_sections.get("studykit", 0))
        internal_non_bot_to_careerkit = int(self.internal_crossproperty_non_bot_target_sections.get("careerkit", 0))
        internal_non_bot_to_housingkit = int(self.internal_crossproperty_non_bot_target_sections.get("housingkit", 0))
        internal_non_bot_to_taxkit = int(self.internal_crossproperty_non_bot_target_sections.get("taxkit", 0))
        internal_inferred_to_datekit = int(self.internal_crossproperty_inferred_target_sections.get("datekit", 0))
        internal_inferred_to_budgetkit = int(self.internal_crossproperty_inferred_target_sections.get("budgetkit", 0))
        internal_inferred_to_healthkit = int(self.internal_crossproperty_inferred_target_sections.get("healthkit", 0))
        internal_inferred_to_sleepkit = int(self.internal_crossproperty_inferred_target_sections.get("sleepkit", 0))
        internal_inferred_to_focuskit = int(self.internal_crossproperty_inferred_target_sections.get("focuskit", 0))
        internal_inferred_to_opskit = int(self.internal_crossproperty_inferred_target_sections.get("opskit", 0))
        internal_inferred_to_studykit = int(self.internal_crossproperty_inferred_target_sections.get("studykit", 0))
        internal_inferred_to_careerkit = int(self.internal_crossproperty_inferred_target_sections.get("careerkit", 0))
        internal_inferred_to_housingkit = int(self.internal_crossproperty_inferred_target_sections.get("housingkit", 0))
        internal_inferred_to_taxkit = int(self.internal_crossproperty_inferred_target_sections.get("taxkit", 0))
        internal_inferred_non_bot_to_datekit = int(
            self.internal_crossproperty_inferred_non_bot_target_sections.get("datekit", 0)
        )
        internal_inferred_non_bot_to_budgetkit = int(
            self.internal_crossproperty_inferred_non_bot_target_sections.get("budgetkit", 0)
        )
        internal_inferred_non_bot_to_healthkit = int(
            self.internal_crossproperty_inferred_non_bot_target_sections.get("healthkit", 0)
        )
        internal_inferred_non_bot_to_sleepkit = int(
            self.internal_crossproperty_inferred_non_bot_target_sections.get("sleepkit", 0)
        )
        internal_inferred_non_bot_to_focuskit = int(
            self.internal_crossproperty_inferred_non_bot_target_sections.get("focuskit", 0)
        )
        internal_inferred_non_bot_to_opskit = int(
            self.internal_crossproperty_inferred_non_bot_target_sections.get("opskit", 0)
        )
        internal_inferred_non_bot_to_studykit = int(
            self.internal_crossproperty_inferred_non_bot_target_sections.get("studykit", 0)
        )
        internal_inferred_non_bot_to_careerkit = int(
            self.internal_crossproperty_inferred_non_bot_target_sections.get("careerkit", 0)
        )
        internal_inferred_non_bot_to_housingkit = int(
            self.internal_crossproperty_inferred_non_bot_target_sections.get("housingkit", 0)
        )
        internal_inferred_non_bot_to_taxkit = int(
            self.internal_crossproperty_inferred_non_bot_target_sections.get("taxkit", 0)
        )
        internal_inferred_non_bot_verified_to_datekit = int(
            self.internal_crossproperty_inferred_non_bot_verified_target_sections.get("datekit", 0)
        )
        internal_inferred_non_bot_verified_to_budgetkit = int(
            self.internal_crossproperty_inferred_non_bot_verified_target_sections.get("budgetkit", 0)
        )
        internal_inferred_non_bot_verified_to_healthkit = int(
            self.internal_crossproperty_inferred_non_bot_verified_target_sections.get("healthkit", 0)
        )
        internal_inferred_non_bot_verified_to_sleepkit = int(
            self.internal_crossproperty_inferred_non_bot_verified_target_sections.get("sleepkit", 0)
        )
        internal_inferred_non_bot_verified_to_focuskit = int(
            self.internal_crossproperty_inferred_non_bot_verified_target_sections.get("focuskit", 0)
        )
        internal_inferred_non_bot_verified_to_opskit = int(
            self.internal_crossproperty_inferred_non_bot_verified_target_sections.get("opskit", 0)
        )
        internal_inferred_non_bot_verified_to_studykit = int(
            self.internal_crossproperty_inferred_non_bot_verified_target_sections.get("studykit", 0)
        )
        internal_inferred_non_bot_verified_to_careerkit = int(
            self.internal_crossproperty_inferred_non_bot_verified_target_sections.get("careerkit", 0)
        )
        internal_inferred_non_bot_verified_to_housingkit = int(
            self.internal_crossproperty_inferred_non_bot_verified_target_sections.get("housingkit", 0)
        )
        internal_inferred_non_bot_verified_to_taxkit = int(
            self.internal_crossproperty_inferred_non_bot_verified_target_sections.get("taxkit", 0)
        )
        internal_high_confidence_non_bot_to_datekit = (
            internal_non_bot_to_datekit + internal_inferred_non_bot_verified_to_datekit
        )
        internal_high_confidence_non_bot_to_budgetkit = (
            internal_non_bot_to_budgetkit + internal_inferred_non_bot_verified_to_budgetkit
        )
        internal_high_confidence_non_bot_to_healthkit = (
            internal_non_bot_to_healthkit + internal_inferred_non_bot_verified_to_healthkit
        )
        internal_high_confidence_non_bot_to_sleepkit = (
            internal_non_bot_to_sleepkit + internal_inferred_non_bot_verified_to_sleepkit
        )
        internal_high_confidence_non_bot_to_focuskit = (
            internal_non_bot_to_focuskit + internal_inferred_non_bot_verified_to_focuskit
        )
        internal_high_confidence_non_bot_to_opskit = (
            internal_non_bot_to_opskit + internal_inferred_non_bot_verified_to_opskit
        )
        internal_high_confidence_non_bot_to_studykit = (
            internal_non_bot_to_studykit + internal_inferred_non_bot_verified_to_studykit
        )
        internal_high_confidence_non_bot_to_careerkit = (
            internal_non_bot_to_careerkit + internal_inferred_non_bot_verified_to_careerkit
        )
        internal_high_confidence_non_bot_to_housingkit = (
            internal_non_bot_to_housingkit + internal_inferred_non_bot_verified_to_housingkit
        )
        internal_high_confidence_non_bot_to_taxkit = (
            internal_non_bot_to_taxkit + internal_inferred_non_bot_verified_to_taxkit
        )
        internal_effective_to_datekit = internal_to_datekit + internal_inferred_to_datekit
        internal_effective_to_budgetkit = internal_to_budgetkit + internal_inferred_to_budgetkit
        internal_effective_to_healthkit = internal_to_healthkit + internal_inferred_to_healthkit
        internal_effective_to_sleepkit = internal_to_sleepkit + internal_inferred_to_sleepkit
        internal_effective_to_focuskit = internal_to_focuskit + internal_inferred_to_focuskit
        internal_effective_to_opskit = internal_to_opskit + internal_inferred_to_opskit
        internal_effective_to_studykit = internal_to_studykit + internal_inferred_to_studykit
        internal_effective_to_careerkit = internal_to_careerkit + internal_inferred_to_careerkit
        internal_effective_to_housingkit = internal_to_housingkit + internal_inferred_to_housingkit
        internal_effective_to_taxkit = internal_to_taxkit + internal_inferred_to_taxkit
        internal_effective_non_bot_to_datekit = internal_non_bot_to_datekit + internal_inferred_non_bot_to_datekit
        internal_effective_non_bot_to_budgetkit = internal_non_bot_to_budgetkit + internal_inferred_non_bot_to_budgetkit
        internal_effective_non_bot_to_healthkit = internal_non_bot_to_healthkit + internal_inferred_non_bot_to_healthkit
        internal_effective_non_bot_to_sleepkit = internal_non_bot_to_sleepkit + internal_inferred_non_bot_to_sleepkit
        internal_effective_non_bot_to_focuskit = internal_non_bot_to_focuskit + internal_inferred_non_bot_to_focuskit
        internal_effective_non_bot_to_opskit = internal_non_bot_to_opskit + internal_inferred_non_bot_to_opskit
        internal_effective_non_bot_to_studykit = internal_non_bot_to_studykit + internal_inferred_non_bot_to_studykit
        internal_effective_non_bot_to_careerkit = internal_non_bot_to_careerkit + internal_inferred_non_bot_to_careerkit
        internal_effective_non_bot_to_housingkit = (
            internal_non_bot_to_housingkit + internal_inferred_non_bot_to_housingkit
        )
        internal_effective_non_bot_to_taxkit = internal_non_bot_to_taxkit + internal_inferred_non_bot_to_taxkit
        internal_crossproperty_effective_referrals = (
            self.internal_crossproperty_referrals + self.internal_crossproperty_inferred_referrals
        )
        internal_crossproperty_effective_non_bot_referrals = (
            self.internal_crossproperty_non_bot_referrals + self.internal_crossproperty_inferred_non_bot_referrals
        )
        crosspromo_to_datekit = int(self.crosspromo_campaign_target_sections.get("datekit", 0))
        crosspromo_to_budgetkit = int(self.crosspromo_campaign_target_sections.get("budgetkit", 0))
        crosspromo_to_healthkit = int(self.crosspromo_campaign_target_sections.get("healthkit", 0))
        crosspromo_to_sleepkit = int(self.crosspromo_campaign_target_sections.get("sleepkit", 0))
        crosspromo_to_focuskit = int(self.crosspromo_campaign_target_sections.get("focuskit", 0))
        crosspromo_to_opskit = int(self.crosspromo_campaign_target_sections.get("opskit", 0))
        crosspromo_to_studykit = int(self.crosspromo_campaign_target_sections.get("studykit", 0))
        crosspromo_to_careerkit = int(self.crosspromo_campaign_target_sections.get("careerkit", 0))
        crosspromo_to_housingkit = int(self.crosspromo_campaign_target_sections.get("housingkit", 0))
        crosspromo_to_taxkit = int(self.crosspromo_campaign_target_sections.get("taxkit", 0))
        crosspromo_non_bot_to_datekit = int(self.crosspromo_non_bot_campaign_target_sections.get("datekit", 0))
        crosspromo_non_bot_to_budgetkit = int(self.crosspromo_non_bot_campaign_target_sections.get("budgetkit", 0))
        crosspromo_non_bot_to_healthkit = int(self.crosspromo_non_bot_campaign_target_sections.get("healthkit", 0))
        crosspromo_non_bot_to_sleepkit = int(self.crosspromo_non_bot_campaign_target_sections.get("sleepkit", 0))
        crosspromo_non_bot_to_focuskit = int(self.crosspromo_non_bot_campaign_target_sections.get("focuskit", 0))
        crosspromo_non_bot_to_opskit = int(self.crosspromo_non_bot_campaign_target_sections.get("opskit", 0))
        crosspromo_non_bot_to_studykit = int(self.crosspromo_non_bot_campaign_target_sections.get("studykit", 0))
        crosspromo_non_bot_to_careerkit = int(self.crosspromo_non_bot_campaign_target_sections.get("careerkit", 0))
        crosspromo_non_bot_to_housingkit = int(self.crosspromo_non_bot_campaign_target_sections.get("housingkit", 0))
        crosspromo_non_bot_to_taxkit = int(self.crosspromo_non_bot_campaign_target_sections.get("taxkit", 0))
        crosspromo_param_source_hits = self.crosspromo_hits_with_param_source
        crosspromo_non_bot_param_source_hits = self.crosspromo_non_bot_hits_with_param_source
        crosspromo_param_source_without_referrer_hits = self.crosspromo_hits_with_param_source_without_referrer
        crosspromo_non_bot_param_source_without_referrer_hits = (
            self.crosspromo_non_bot_hits_with_param_source_without_referrer
        )
        crosspromo_source_attributed_hits = self.crosspromo_hits_with_internal_referrer + self.crosspromo_hits_with_inferred_source
        crosspromo_non_bot_hits = max(0, self.crosspromo_campaign_hits - self.crosspromo_known_bot_hits)
        crosspromo_non_bot_source_attributed_hits = (
            self.crosspromo_non_bot_hits_with_internal_referrer + self.crosspromo_non_bot_hits_with_inferred_source
        )
        crosspromo_suspected_automation_hits = self.crosspromo_suspected_automation_hits
        crosspromo_suspected_automation_unique_ips = len(self.crosspromo_suspected_automation_unique_ips)
        crosspromo_inferred_verified_hits = self.crosspromo_inferred_verified_hits
        crosspromo_inferred_unverified_hits = self.crosspromo_inferred_unverified_hits
        crosspromo_non_bot_inferred_verified_hits = self.crosspromo_non_bot_inferred_verified_hits
        crosspromo_non_bot_inferred_unverified_hits = self.crosspromo_non_bot_inferred_unverified_hits
        internal_inferred_verified_referrals = self.internal_crossproperty_inferred_verified_referrals
        internal_inferred_non_bot_verified_referrals = self.internal_crossproperty_inferred_non_bot_verified_referrals
        internal_inferred_unverified_referrals = self.internal_crossproperty_inferred_unverified_referrals
        internal_inferred_non_bot_unverified_referrals = self.internal_crossproperty_inferred_non_bot_unverified_referrals
        crosspromo_non_bot_high_confidence_hits = (
            self.crosspromo_non_bot_hits_with_internal_referrer + crosspromo_non_bot_inferred_verified_hits
        )
        crosspromo_non_bot_low_confidence_hits = max(
            0,
            crosspromo_non_bot_hits - crosspromo_non_bot_high_confidence_hits,
        )
        internal_crossproperty_high_confidence_non_bot_referrals = (
            self.internal_crossproperty_non_bot_referrals + internal_inferred_non_bot_verified_referrals
        )
        internal_crossproperty_low_confidence_non_bot_referrals = internal_inferred_non_bot_unverified_referrals
        top_internal_source_section = "other"
        top_internal_source_referrals = 0
        top_internal_non_bot_source_section = "other"
        top_internal_non_bot_source_referrals = 0
        top_crosspromo_source = ""
        top_crosspromo_source_hits = 0
        top_crosspromo_source_page = ""
        top_crosspromo_source_page_hits = 0
        top_crosspromo_target_section = "other"
        top_crosspromo_target_hits = 0
        top_crosspromo_source_target = ""
        top_crosspromo_source_target_hits = 0
        top_crosspromo_page_pair = ""
        top_crosspromo_page_pair_hits = 0
        top_crosspromo_known_bot_user_agent = ""
        top_crosspromo_known_bot_user_agent_hits = 0
        top_crosspromo_suspected_automation_user_agent = ""
        top_crosspromo_suspected_automation_user_agent_hits = 0
        top_crosspromo_non_bot_source = ""
        top_crosspromo_non_bot_source_hits = 0
        top_crosspromo_non_bot_source_page = ""
        top_crosspromo_non_bot_source_page_hits = 0
        top_crosspromo_non_bot_target_section = "other"
        top_crosspromo_non_bot_target_hits = 0
        top_crosspromo_non_bot_source_target = ""
        top_crosspromo_non_bot_source_target_hits = 0
        top_crosspromo_non_bot_page_pair = ""
        top_crosspromo_non_bot_page_pair_hits = 0
        if content_sections:
            top_content_section, top_content_section_requests = max(content_sections.items(), key=lambda item: item[1])
        if organic_sections:
            top_organic_section, top_organic_section_referrals = max(organic_sections.items(), key=lambda item: item[1])
        if organic_non_bot_sections:
            top_organic_non_bot_section, top_organic_non_bot_section_referrals = max(
                organic_non_bot_sections.items(),
                key=lambda item: item[1],
            )
        if self.organic_non_bot_page_counts:
            top_organic_non_bot_page, top_organic_non_bot_page_hits = max(
                self.organic_non_bot_page_counts.items(),
                key=lambda item: item[1],
            )
        if organic_non_bot_kit_referrals > 0:
            top_organic_non_bot_kit_section, top_organic_non_bot_kit_section_referrals = max(
                ((name, organic_non_bot_sections[name]) for name in KIT_SECTION_NAMES),
                key=lambda item: item[1],
            )
        if organic_non_bot_kit_page_counts:
            top_organic_non_bot_kit_page, top_organic_non_bot_kit_page_hits = max(
                organic_non_bot_kit_page_counts.items(),
                key=lambda item: item[1],
            )
        if self.internal_crossproperty_source_sections:
            top_internal_source_section, top_internal_source_referrals = max(
                self.internal_crossproperty_source_sections.items(),
                key=lambda item: item[1],
            )
        if self.internal_crossproperty_non_bot_source_sections:
            top_internal_non_bot_source_section, top_internal_non_bot_source_referrals = max(
                self.internal_crossproperty_non_bot_source_sections.items(),
                key=lambda item: item[1],
            )
        if self.crosspromo_campaign_sources:
            top_crosspromo_source, top_crosspromo_source_hits = max(
                self.crosspromo_campaign_sources.items(),
                key=lambda item: item[1],
            )
        if self.crosspromo_campaign_source_pages:
            top_crosspromo_source_page, top_crosspromo_source_page_hits = max(
                self.crosspromo_campaign_source_pages.items(),
                key=lambda item: item[1],
            )
        if self.crosspromo_campaign_target_sections:
            top_crosspromo_target_section, top_crosspromo_target_hits = max(
                self.crosspromo_campaign_target_sections.items(),
                key=lambda item: item[1],
            )
        if self.crosspromo_campaign_source_target_sections:
            top_crosspromo_source_target, top_crosspromo_source_target_hits = max(
                self.crosspromo_campaign_source_target_sections.items(),
                key=lambda item: item[1],
            )
        if self.crosspromo_campaign_page_path_pairs:
            top_crosspromo_page_pair, top_crosspromo_page_pair_hits = max(
                self.crosspromo_campaign_page_path_pairs.items(),
                key=lambda item: item[1],
            )
        if self.crosspromo_known_bot_user_agents:
            top_crosspromo_known_bot_user_agent, top_crosspromo_known_bot_user_agent_hits = max(
                self.crosspromo_known_bot_user_agents.items(),
                key=lambda item: item[1],
            )
        if self.crosspromo_suspected_automation_user_agents:
            (
                top_crosspromo_suspected_automation_user_agent,
                top_crosspromo_suspected_automation_user_agent_hits,
            ) = max(
                self.crosspromo_suspected_automation_user_agents.items(),
                key=lambda item: item[1],
            )
        if self.crosspromo_non_bot_campaign_sources:
            top_crosspromo_non_bot_source, top_crosspromo_non_bot_source_hits = max(
                self.crosspromo_non_bot_campaign_sources.items(),
                key=lambda item: item[1],
            )
        if self.crosspromo_non_bot_campaign_source_pages:
            top_crosspromo_non_bot_source_page, top_crosspromo_non_bot_source_page_hits = max(
                self.crosspromo_non_bot_campaign_source_pages.items(),
                key=lambda item: item[1],
            )
        if self.crosspromo_non_bot_campaign_target_sections:
            top_crosspromo_non_bot_target_section, top_crosspromo_non_bot_target_hits = max(
                self.crosspromo_non_bot_campaign_target_sections.items(),
                key=lambda item: item[1],
            )
        if self.crosspromo_non_bot_campaign_source_target_sections:
            top_crosspromo_non_bot_source_target, top_crosspromo_non_bot_source_target_hits = max(
                self.crosspromo_non_bot_campaign_source_target_sections.items(),
                key=lambda item: item[1],
            )
        if self.crosspromo_non_bot_campaign_page_path_pairs:
            top_crosspromo_non_bot_page_pair, top_crosspromo_non_bot_page_pair_hits = max(
                self.crosspromo_non_bot_campaign_page_path_pairs.items(),
                key=lambda item: item[1],
            )

        summary = {
            "generated_at": generated_at,
            "window_hours": window_hours,
            "total_requests": self.total_requests,
            "unique_ips": len(self.unique_ips),
            "clean_requests": self.clean_requests,
            "clean_unique_ips": len(self.clean_unique_ips),
            "content_requests": self.content_requests,
            "content_unique_ips": len(self.content_unique_ips),
            "suspicious_requests": self.suspicious_requests,
            "suspicious_unique_ips": len(self.suspicious_unique_ips),
            "not_found_requests": not_found_total,
            "suspicious_404": suspicious_404,
            "clean_404": clean_404,
            "organic_referrals": organic_total,
            "organic_non_bot_referrals": organic_non_bot_total,
            "organic_kit_referrals": organic_kit_referrals,
            "organic_non_bot_kit_referrals": organic_non_bot_kit_referrals,
            "crosspromo_campaign_hits": self.crosspromo_campaign_hits,
            "crosspromo_campaign_hits_to_datekit": crosspromo_to_datekit,
            "crosspromo_campaign_hits_to_budgetkit": crosspromo_to_budgetkit,
            "crosspromo_campaign_hits_to_healthkit": crosspromo_to_healthkit,
            "crosspromo_campaign_hits_to_sleepkit": crosspromo_to_sleepkit,
            "crosspromo_campaign_hits_to_focuskit": crosspromo_to_focuskit,
            "crosspromo_campaign_hits_to_opskit": crosspromo_to_opskit,
            "crosspromo_campaign_hits_to_studykit": crosspromo_to_studykit,
            "crosspromo_campaign_hits_to_careerkit": crosspromo_to_careerkit,
            "crosspromo_campaign_hits_to_housingkit": crosspromo_to_housingkit,
            "crosspromo_campaign_hits_to_taxkit": crosspromo_to_taxkit,
            "crosspromo_non_bot_hits_to_datekit": crosspromo_non_bot_to_datekit,
            "crosspromo_non_bot_hits_to_budgetkit": crosspromo_non_bot_to_budgetkit,
            "crosspromo_non_bot_hits_to_healthkit": crosspromo_non_bot_to_healthkit,
            "crosspromo_non_bot_hits_to_sleepkit": crosspromo_non_bot_to_sleepkit,
            "crosspromo_non_bot_hits_to_focuskit": crosspromo_non_bot_to_focuskit,
            "crosspromo_non_bot_hits_to_opskit": crosspromo_non_bot_to_opskit,
            "crosspromo_non_bot_hits_to_studykit": crosspromo_non_bot_to_studykit,
            "crosspromo_non_bot_hits_to_careerkit": crosspromo_non_bot_to_careerkit,
            "crosspromo_non_bot_hits_to_housingkit": crosspromo_non_bot_to_housingkit,
            "crosspromo_non_bot_hits_to_taxkit": crosspromo_non_bot_to_taxkit,
            "crosspromo_source_attributed_hits": crosspromo_source_attributed_hits,
            "crosspromo_hits_with_param_source": crosspromo_param_source_hits,
            "crosspromo_non_bot_hits_with_param_source": crosspromo_non_bot_param_source_hits,
            "crosspromo_hits_with_param_source_without_referrer": crosspromo_param_source_without_referrer_hits,
            "crosspromo_non_bot_hits_with_param_source_without_referrer": (
                crosspromo_non_bot_param_source_without_referrer_hits
            ),
            "crosspromo_hits_with_internal_referrer": self.crosspromo_hits_with_internal_referrer,
            "crosspromo_hits_with_inferred_source": self.crosspromo_hits_with_inferred_source,
            "crosspromo_inferred_verified_hits": crosspromo_inferred_verified_hits,
            "crosspromo_inferred_unverified_hits": crosspromo_inferred_unverified_hits,
            "crosspromo_hits_unattributed": self.crosspromo_hits_unattributed,
            "crosspromo_non_bot_source_attributed_hits": crosspromo_non_bot_source_attributed_hits,
            "crosspromo_non_bot_hits_with_internal_referrer": self.crosspromo_non_bot_hits_with_internal_referrer,
            "crosspromo_non_bot_hits_with_inferred_source": self.crosspromo_non_bot_hits_with_inferred_source,
            "crosspromo_non_bot_inferred_verified_hits": crosspromo_non_bot_inferred_verified_hits,
            "crosspromo_non_bot_inferred_unverified_hits": crosspromo_non_bot_inferred_unverified_hits,
            "crosspromo_non_bot_hits_unattributed": self.crosspromo_non_bot_hits_unattributed,
            "crosspromo_hits_with_any_referrer": self.crosspromo_hits_with_any_referrer,
            "crosspromo_hits_without_referrer": self.crosspromo_hits_without_referrer,
            "crosspromo_non_bot_hits_with_any_referrer": self.crosspromo_non_bot_hits_with_any_referrer,
            "crosspromo_non_bot_hits_without_referrer": self.crosspromo_non_bot_hits_without_referrer,
            "crosspromo_hits_without_referrer_known_bot": self.crosspromo_hits_without_referrer_known_bot,
            "crosspromo_hits_without_referrer_non_bot": max(
                0,
                self.crosspromo_hits_without_referrer - self.crosspromo_hits_without_referrer_known_bot,
            ),
            "crosspromo_known_bot_hits": self.crosspromo_known_bot_hits,
            "crosspromo_non_bot_hits": crosspromo_non_bot_hits,
            "crosspromo_non_bot_high_confidence_hits": crosspromo_non_bot_high_confidence_hits,
            "crosspromo_non_bot_low_confidence_hits": crosspromo_non_bot_low_confidence_hits,
            "crosspromo_suspected_automation_hits": crosspromo_suspected_automation_hits,
            "crosspromo_suspected_automation_unique_ips": crosspromo_suspected_automation_unique_ips,
            "crosspromo_source_mismatch_hits": self.crosspromo_source_mismatch_hits,
            "internal_crossproperty_referrals": self.internal_crossproperty_referrals,
            "internal_crossproperty_referrals_to_datekit": internal_to_datekit,
            "internal_crossproperty_referrals_to_budgetkit": internal_to_budgetkit,
            "internal_crossproperty_referrals_to_healthkit": internal_to_healthkit,
            "internal_crossproperty_referrals_to_sleepkit": internal_to_sleepkit,
            "internal_crossproperty_referrals_to_focuskit": internal_to_focuskit,
            "internal_crossproperty_referrals_to_opskit": internal_to_opskit,
            "internal_crossproperty_referrals_to_studykit": internal_to_studykit,
            "internal_crossproperty_referrals_to_careerkit": internal_to_careerkit,
            "internal_crossproperty_referrals_to_housingkit": internal_to_housingkit,
            "internal_crossproperty_referrals_to_taxkit": internal_to_taxkit,
            "internal_crossproperty_non_bot_referrals": self.internal_crossproperty_non_bot_referrals,
            "internal_crossproperty_non_bot_referrals_to_datekit": internal_non_bot_to_datekit,
            "internal_crossproperty_non_bot_referrals_to_budgetkit": internal_non_bot_to_budgetkit,
            "internal_crossproperty_non_bot_referrals_to_healthkit": internal_non_bot_to_healthkit,
            "internal_crossproperty_non_bot_referrals_to_sleepkit": internal_non_bot_to_sleepkit,
            "internal_crossproperty_non_bot_referrals_to_focuskit": internal_non_bot_to_focuskit,
            "internal_crossproperty_non_bot_referrals_to_opskit": internal_non_bot_to_opskit,
            "internal_crossproperty_non_bot_referrals_to_studykit": internal_non_bot_to_studykit,
            "internal_crossproperty_non_bot_referrals_to_careerkit": internal_non_bot_to_careerkit,
            "internal_crossproperty_non_bot_referrals_to_housingkit": internal_non_bot_to_housingkit,
            "internal_crossproperty_non_bot_referrals_to_taxkit": internal_non_bot_to_taxkit,
            "internal_crossproperty_inferred_referrals": self.internal_crossproperty_inferred_referrals,
            "internal_crossproperty_inferred_referrals_to_datekit": internal_inferred_to_datekit,
            "internal_crossproperty_inferred_referrals_to_budgetkit": internal_inferred_to_budgetkit,
            "internal_crossproperty_inferred_referrals_to_healthkit": internal_inferred_to_healthkit,
            "internal_crossproperty_inferred_referrals_to_sleepkit": internal_inferred_to_sleepkit,
            "internal_crossproperty_inferred_referrals_to_focuskit": internal_inferred_to_focuskit,
            "internal_crossproperty_inferred_referrals_to_opskit": internal_inferred_to_opskit,
            "internal_crossproperty_inferred_referrals_to_studykit": internal_inferred_to_studykit,
            "internal_crossproperty_inferred_referrals_to_careerkit": internal_inferred_to_careerkit,
            "internal_crossproperty_inferred_referrals_to_housingkit": internal_inferred_to_housingkit,
            "internal_crossproperty_inferred_referrals_to_taxkit": internal_inferred_to_taxkit,
            "internal_crossproperty_inferred_non_bot_referrals": self.internal_crossproperty_inferred_non_bot_referrals,
            "internal_crossproperty_inferred_non_bot_referrals_to_datekit": internal_inferred_non_bot_to_datekit,
            "internal_crossproperty_inferred_non_bot_referrals_to_budgetkit": internal_inferred_non_bot_to_budgetkit,
            "internal_crossproperty_inferred_non_bot_referrals_to_healthkit": internal_inferred_non_bot_to_healthkit,
            "internal_crossproperty_inferred_non_bot_referrals_to_sleepkit": internal_inferred_non_bot_to_sleepkit,
            "internal_crossproperty_inferred_non_bot_referrals_to_focuskit": internal_inferred_non_bot_to_focuskit,
            "internal_crossproperty_inferred_non_bot_referrals_to_opskit": internal_inferred_non_bot_to_opskit,
            "internal_crossproperty_inferred_non_bot_referrals_to_studykit": internal_inferred_non_bot_to_studykit,
            "internal_crossproperty_inferred_non_bot_referrals_to_careerkit": internal_inferred_non_bot_to_careerkit,
            "internal_crossproperty_inferred_non_bot_referrals_to_housingkit": internal_inferred_non_bot_to_housingkit,
            "internal_crossproperty_inferred_non_bot_referrals_to_taxkit": internal_inferred_non_bot_to_taxkit,
            "internal_crossproperty_inferred_verified_referrals": internal_inferred_verified_referrals,
            "internal_crossproperty_inferred_non_bot_verified_referrals": internal_inferred_non_bot_verified_referrals,
            "internal_crossproperty_inferred_unverified_referrals": internal_inferred_unverified_referrals,
            "internal_crossproperty_inferred_non_bot_unverified_referrals": internal_inferred_non_bot_unverified_referrals,
            "internal_crossproperty_effective_referrals": internal_crossproperty_effective_referrals,
            "internal_crossproperty_effective_referrals_to_datekit": internal_effective_to_datekit,
            "internal_crossproperty_effective_referrals_to_budgetkit": internal_effective_to_budgetkit,
            "internal_crossproperty_effective_referrals_to_healthkit": internal_effective_to_healthkit,
            "internal_crossproperty_effective_referrals_to_sleepkit": internal_effective_to_sleepkit,
            "internal_crossproperty_effective_referrals_to_focuskit": internal_effective_to_focuskit,
            "internal_crossproperty_effective_referrals_to_opskit": internal_effective_to_opskit,
            "internal_crossproperty_effective_referrals_to_studykit": internal_effective_to_studykit,
            "internal_crossproperty_effective_referrals_to_careerkit": internal_effective_to_careerkit,
            "internal_crossproperty_effective_referrals_to_housingkit": internal_effective_to_housingkit,
            "internal_crossproperty_effective_referrals_to_taxkit": internal_effective_to_taxkit,
            "internal_crossproperty_effective_non_bot_referrals": internal_crossproperty_effective_non_bot_referrals,
            "internal_crossproperty_effective_non_bot_referrals_to_datekit": internal_effective_non_bot_to_datekit,
            "internal_crossproperty_effective_non_bot_referrals_to_budgetkit": internal_effective_non_bot_to_budgetkit,
            "internal_crossproperty_effective_non_bot_referrals_to_healthkit": internal_effective_non_bot_to_healthkit,
            "internal_crossproperty_effective_non_bot_referrals_to_sleepkit": internal_effective_non_bot_to_sleepkit,
            "internal_crossproperty_effective_non_bot_referrals_to_focuskit": internal_effective_non_bot_to_focuskit,
            "internal_crossproperty_effective_non_bot_referrals_to_opskit": internal_effective_non_bot_to_opskit,
            "internal_crossproperty_effective_non_bot_referrals_to_studykit": internal_effective_non_bot_to_studykit,
            "internal_crossproperty_effective_non_bot_referrals_to_careerkit": internal_effective_non_bot_to_careerkit,
            "internal_crossproperty_effective_non_bot_referrals_to_housingkit": internal_effective_non_bot_to_housingkit,
            "internal_crossproperty_effective_non_bot_referrals_to_taxkit": internal_effective_non_bot_to_taxkit,
            "internal_crossproperty_high_confidence_non_bot_referrals": (
                internal_crossproperty_high_confidence_non_bot_referrals
            ),
            "internal_crossproperty_high_confidence_non_bot_referrals_to_datekit": (
                internal_high_confidence_non_bot_to_datekit
            ),
            "internal_crossproperty_high_confidence_non_bot_referrals_to_budgetkit": (
                internal_high_confidence_non_bot_to_budgetkit
            ),
            "internal_crossproperty_high_confidence_non_bot_referrals_to_healthkit": (
                internal_high_confidence_non_bot_to_healthkit
            ),
            "internal_crossproperty_high_confidence_non_bot_referrals_to_sleepkit": (
                internal_high_confidence_non_bot_to_sleepkit
            ),
            "internal_crossproperty_high_confidence_non_bot_referrals_to_focuskit": (
                internal_high_confidence_non_bot_to_focuskit
            ),
            "internal_crossproperty_high_confidence_non_bot_referrals_to_opskit": (
                internal_high_confidence_non_bot_to_opskit
            ),
            "internal_crossproperty_high_confidence_non_bot_referrals_to_studykit": (
                internal_high_confidence_non_bot_to_studykit
            ),
            "internal_crossproperty_high_confidence_non_bot_referrals_to_careerkit": (
                internal_high_confidence_non_bot_to_careerkit
            ),
            "internal_crossproperty_high_confidence_non_bot_referrals_to_housingkit": (
                internal_high_confidence_non_bot_to_housingkit
            ),
            "internal_crossproperty_high_confidence_non_bot_referrals_to_taxkit": (
                internal_high_confidence_non_bot_to_taxkit
            ),
            "internal_crossproperty_low_confidence_non_bot_referrals": (
                internal_crossproperty_low_confidence_non_bot_referrals
            ),
            "known_bot_requests": self.known_bot_requests,
            "known_bot_unique_ips": len(self.known_bot_unique_ips),
            "clean_request_ratio": safe_ratio(self.clean_requests, self.total_requests),
            "content_request_ratio": safe_ratio(self.content_requests, self.total_requests),
            "suspicious_request_ratio": safe_ratio(self.suspicious_requests, self.total_requests),
            "organic_referral_ratio": safe_ratio(organic_total, self.total_requests),
            "organic_non_bot_referral_ratio": safe_ratio(organic_non_bot_total, self.total_requests),
            "organic_non_bot_kit_referral_ratio": safe_ratio(organic_non_bot_kit_referrals, organic_non_bot_total),
            "internal_crossproperty_referral_ratio": safe_ratio(self.internal_crossproperty_referrals, self.total_requests),
            "internal_crossproperty_non_bot_referral_ratio": safe_ratio(
                self.internal_crossproperty_non_bot_referrals,
                self.total_requests,
            ),
            "internal_crossproperty_inferred_referral_ratio": safe_ratio(
                self.internal_crossproperty_inferred_referrals,
                self.total_requests,
            ),
            "internal_crossproperty_inferred_non_bot_referral_ratio": safe_ratio(
                self.internal_crossproperty_inferred_non_bot_referrals,
                self.total_requests,
            ),
            "internal_crossproperty_effective_referral_ratio": safe_ratio(
                internal_crossproperty_effective_referrals,
                self.total_requests,
            ),
            "internal_crossproperty_effective_non_bot_referral_ratio": safe_ratio(
                internal_crossproperty_effective_non_bot_referrals,
                self.total_requests,
            ),
            "internal_crossproperty_high_confidence_non_bot_referral_ratio": safe_ratio(
                internal_crossproperty_high_confidence_non_bot_referrals,
                self.total_requests,
            ),
            "internal_crossproperty_low_confidence_non_bot_referral_ratio": safe_ratio(
                internal_crossproperty_low_confidence_non_bot_referrals,
                self.total_requests,
            ),
            "internal_crossproperty_high_confidence_non_bot_of_effective_ratio": safe_ratio(
                internal_crossproperty_high_confidence_non_bot_referrals,
                internal_crossproperty_effective_non_bot_referrals,
            ),
            "crosspromo_source_attribution_ratio": safe_ratio(crosspromo_source_attributed_hits, self.crosspromo_campaign_hits),
            "known_bot_request_ratio": safe_ratio(self.known_bot_requests, self.total_requests),
            "crosspromo_known_bot_ratio": safe_ratio(self.crosspromo_known_bot_hits, self.crosspromo_campaign_hits),
            "crosspromo_suspected_automation_ratio": safe_ratio(
                crosspromo_suspected_automation_hits,
                self.crosspromo_campaign_hits,
            ),
            "crosspromo_non_bot_source_attribution_ratio": safe_ratio(
                crosspromo_non_bot_source_attributed_hits,
                crosspromo_non_bot_hits,
            ),
            "crosspromo_non_bot_high_confidence_ratio": safe_ratio(
                crosspromo_non_bot_high_confidence_hits,
                crosspromo_non_bot_hits,
            ),
            "crosspromo_non_bot_low_confidence_ratio": safe_ratio(
                crosspromo_non_bot_low_confidence_hits,
                crosspromo_non_bot_hits,
            ),
            "crosspromo_without_referrer_ratio": safe_ratio(
                self.crosspromo_hits_without_referrer,
                self.crosspromo_campaign_hits,
            ),
            "crosspromo_non_bot_without_referrer_ratio": safe_ratio(
                self.crosspromo_non_bot_hits_without_referrer,
                crosspromo_non_bot_hits,
            ),
            "crosspromo_param_source_ratio": safe_ratio(
                crosspromo_param_source_hits,
                self.crosspromo_campaign_hits,
            ),
            "crosspromo_non_bot_param_source_ratio": safe_ratio(
                crosspromo_non_bot_param_source_hits,
                crosspromo_non_bot_hits,
            ),
            "crosspromo_param_source_without_referrer_ratio": safe_ratio(
                crosspromo_param_source_without_referrer_hits,
                self.crosspromo_hits_without_referrer,
            ),
            "crosspromo_non_bot_param_source_without_referrer_ratio": safe_ratio(
                crosspromo_non_bot_param_source_without_referrer_hits,
                self.crosspromo_non_bot_hits_without_referrer,
            ),
            "crosspromo_inferred_verification_ratio": safe_ratio(
                crosspromo_inferred_verified_hits,
                self.crosspromo_hits_with_inferred_source,
            ),
            "crosspromo_non_bot_inferred_verification_ratio": safe_ratio(
                crosspromo_non_bot_inferred_verified_hits,
                self.crosspromo_non_bot_hits_with_inferred_source,
            ),
            "internal_crossproperty_inferred_verified_referral_ratio": safe_ratio(
                internal_inferred_verified_referrals,
                self.total_requests,
            ),
            "internal_crossproperty_inferred_non_bot_verified_referral_ratio": safe_ratio(
                internal_inferred_non_bot_verified_referrals,
                self.total_requests,
            ),
            "internal_crossproperty_inferred_unverified_referral_ratio": safe_ratio(
                internal_inferred_unverified_referrals,
                self.total_requests,
            ),
            "internal_crossproperty_inferred_non_bot_unverified_referral_ratio": safe_ratio(
                internal_inferred_non_bot_unverified_referrals,
                self.total_requests,
            ),
            "not_found_ratio": safe_ratio(not_found_total, self.total_requests),
            "clean_404_ratio": safe_ratio(clean_404, not_found_total),
            "suspicious_404_ratio": safe_ratio(suspicious_404, not_found_total),
            "content_sections": content_sections,
            "organic_sections": organic_sections,
            "organic_non_bot_sections": organic_non_bot_sections,
            "content_section_share_pct": content_section_share,
            "organic_section_share_pct": organic_section_share,
            "organic_non_bot_section_share_pct": organic_non_bot_section_share,
            "top_content_section": top_content_section,
            "top_content_section_requests": top_content_section_requests,
            "top_organic_section": top_organic_section,
            "top_organic_section_referrals": top_organic_section_referrals,
            "top_organic_non_bot_section": top_organic_non_bot_section,
            "top_organic_non_bot_section_referrals": top_organic_non_bot_section_referrals,
            "top_organic_non_bot_page": top_organic_non_bot_page,
            "top_organic_non_bot_page_hits": top_organic_non_bot_page_hits,
            "top_organic_non_bot_kit_section": top_organic_non_bot_kit_section,
            "top_organic_non_bot_kit_section_referrals": top_organic_non_bot_kit_section_referrals,
            "top_organic_non_bot_kit_page": top_organic_non_bot_kit_page,
            "top_organic_non_bot_kit_page_hits": top_organic_non_bot_kit_page_hits,
            "top_internal_crossproperty_source_section": top_internal_source_section,
            "top_internal_crossproperty_source_referrals": top_internal_source_referrals,
            "top_internal_crossproperty_non_bot_source_section": top_internal_non_bot_source_section,
            "top_internal_crossproperty_non_bot_source_referrals": top_internal_non_bot_source_referrals,
            "top_crosspromo_campaign_source": top_crosspromo_source,
            "top_crosspromo_campaign_source_hits": top_crosspromo_source_hits,
            "top_crosspromo_campaign_source_page": top_crosspromo_source_page,
            "top_crosspromo_campaign_source_page_hits": top_crosspromo_source_page_hits,
            "top_crosspromo_campaign_target_section": top_crosspromo_target_section,
            "top_crosspromo_campaign_target_hits": top_crosspromo_target_hits,
            "top_crosspromo_campaign_source_target_section": top_crosspromo_source_target,
            "top_crosspromo_campaign_source_target_hits": top_crosspromo_source_target_hits,
            "top_crosspromo_campaign_page_pair": top_crosspromo_page_pair,
            "top_crosspromo_campaign_page_pair_hits": top_crosspromo_page_pair_hits,
            "top_crosspromo_known_bot_user_agent": top_crosspromo_known_bot_user_agent,
            "top_crosspromo_known_bot_user_agent_hits": top_crosspromo_known_bot_user_agent_hits,
            "top_crosspromo_suspected_automation_user_agent": top_crosspromo_suspected_automation_user_agent,
            "top_crosspromo_suspected_automation_user_agent_hits": top_crosspromo_suspected_automation_user_agent_hits,
            "top_crosspromo_non_bot_source": top_crosspromo_non_bot_source,
            "top_crosspromo_non_bot_source_hits": top_crosspromo_non_bot_source_hits,
            "top_crosspromo_non_bot_source_page": top_crosspromo_non_bot_source_page,
            "top_crosspromo_non_bot_source_page_hits": top_crosspromo_non_bot_source_page_hits,
            "top_crosspromo_non_bot_target_section": top_crosspromo_non_bot_target_section,
            "top_crosspromo_non_bot_target_hits": top_crosspromo_non_bot_target_hits,
            "top_crosspromo_non_bot_source_target_section": top_crosspromo_non_bot_source_target,
            "top_crosspromo_non_bot_source_target_hits": top_crosspromo_non_bot_source_target_hits,
            "top_crosspromo_non_bot_page_pair": top_crosspromo_non_bot_page_pair,
            "top_crosspromo_non_bot_page_pair_hits": top_crosspromo_non_bot_page_pair_hits,
        }
        for section_name in CONTENT_SECTION_NAMES:
            summary[f"content_{section_name}_requests"] = content_sections[section_name]
            summary[f"organic_{section_name}_referrals"] = organic_sections[section_name]
            summary[f"organic_non_bot_{section_name}_referrals"] = organic_non_bot_sections[section_name]
        return summary


def build_window_comparison(
    current_summary: dict,
    previous_summary: dict,
    current_start: datetime,
    current_end: datetime,
    previous_start: datetime,
):
    metrics = [
        "total_requests",
        "unique_ips",
        "clean_requests",
        "content_requests",
        "suspicious_requests",
        "not_found_requests",
        "clean_404",
        "suspicious_404",
        "organic_referrals",
        "organic_non_bot_referrals",
        "organic_kit_referrals",
        "organic_non_bot_kit_referrals",
        "crosspromo_campaign_hits",
        "crosspromo_campaign_hits_to_datekit",
        "crosspromo_campaign_hits_to_budgetkit",
        "crosspromo_campaign_hits_to_healthkit",
        "crosspromo_campaign_hits_to_sleepkit",
        "crosspromo_campaign_hits_to_focuskit",
        "crosspromo_campaign_hits_to_opskit",
        "crosspromo_campaign_hits_to_studykit",
        "crosspromo_campaign_hits_to_careerkit",
        "crosspromo_campaign_hits_to_housingkit",
        "crosspromo_campaign_hits_to_taxkit",
        "crosspromo_non_bot_hits_to_datekit",
        "crosspromo_non_bot_hits_to_budgetkit",
        "crosspromo_non_bot_hits_to_healthkit",
        "crosspromo_non_bot_hits_to_sleepkit",
        "crosspromo_non_bot_hits_to_focuskit",
        "crosspromo_non_bot_hits_to_opskit",
        "crosspromo_non_bot_hits_to_studykit",
        "crosspromo_non_bot_hits_to_careerkit",
        "crosspromo_non_bot_hits_to_housingkit",
        "crosspromo_non_bot_hits_to_taxkit",
        "crosspromo_source_attributed_hits",
        "crosspromo_non_bot_source_attributed_hits",
        "crosspromo_hits_with_param_source",
        "crosspromo_non_bot_hits_with_param_source",
        "crosspromo_hits_with_param_source_without_referrer",
        "crosspromo_non_bot_hits_with_param_source_without_referrer",
        "crosspromo_hits_with_internal_referrer",
        "crosspromo_hits_with_inferred_source",
        "crosspromo_inferred_verified_hits",
        "crosspromo_inferred_unverified_hits",
        "crosspromo_hits_unattributed",
        "crosspromo_non_bot_hits_with_internal_referrer",
        "crosspromo_non_bot_hits_with_inferred_source",
        "crosspromo_non_bot_inferred_verified_hits",
        "crosspromo_non_bot_inferred_unverified_hits",
        "crosspromo_non_bot_hits_unattributed",
        "crosspromo_hits_with_any_referrer",
        "crosspromo_hits_without_referrer",
        "crosspromo_non_bot_hits_with_any_referrer",
        "crosspromo_non_bot_hits_without_referrer",
        "crosspromo_hits_without_referrer_known_bot",
        "crosspromo_hits_without_referrer_non_bot",
        "crosspromo_known_bot_hits",
        "crosspromo_non_bot_hits",
        "crosspromo_non_bot_high_confidence_hits",
        "crosspromo_non_bot_low_confidence_hits",
        "crosspromo_source_mismatch_hits",
        "internal_crossproperty_referrals",
        "internal_crossproperty_referrals_to_datekit",
        "internal_crossproperty_referrals_to_budgetkit",
        "internal_crossproperty_referrals_to_healthkit",
        "internal_crossproperty_referrals_to_sleepkit",
        "internal_crossproperty_referrals_to_focuskit",
        "internal_crossproperty_referrals_to_opskit",
        "internal_crossproperty_referrals_to_studykit",
        "internal_crossproperty_referrals_to_careerkit",
        "internal_crossproperty_referrals_to_housingkit",
        "internal_crossproperty_referrals_to_taxkit",
        "internal_crossproperty_non_bot_referrals",
        "internal_crossproperty_non_bot_referrals_to_datekit",
        "internal_crossproperty_non_bot_referrals_to_budgetkit",
        "internal_crossproperty_non_bot_referrals_to_healthkit",
        "internal_crossproperty_non_bot_referrals_to_sleepkit",
        "internal_crossproperty_non_bot_referrals_to_focuskit",
        "internal_crossproperty_non_bot_referrals_to_opskit",
        "internal_crossproperty_non_bot_referrals_to_studykit",
        "internal_crossproperty_non_bot_referrals_to_careerkit",
        "internal_crossproperty_non_bot_referrals_to_housingkit",
        "internal_crossproperty_non_bot_referrals_to_taxkit",
        "internal_crossproperty_inferred_referrals",
        "internal_crossproperty_inferred_referrals_to_datekit",
        "internal_crossproperty_inferred_referrals_to_budgetkit",
        "internal_crossproperty_inferred_referrals_to_healthkit",
        "internal_crossproperty_inferred_referrals_to_sleepkit",
        "internal_crossproperty_inferred_referrals_to_focuskit",
        "internal_crossproperty_inferred_referrals_to_opskit",
        "internal_crossproperty_inferred_referrals_to_studykit",
        "internal_crossproperty_inferred_referrals_to_careerkit",
        "internal_crossproperty_inferred_referrals_to_housingkit",
        "internal_crossproperty_inferred_referrals_to_taxkit",
        "internal_crossproperty_inferred_non_bot_referrals",
        "internal_crossproperty_inferred_non_bot_referrals_to_datekit",
        "internal_crossproperty_inferred_non_bot_referrals_to_budgetkit",
        "internal_crossproperty_inferred_non_bot_referrals_to_healthkit",
        "internal_crossproperty_inferred_non_bot_referrals_to_sleepkit",
        "internal_crossproperty_inferred_non_bot_referrals_to_focuskit",
        "internal_crossproperty_inferred_non_bot_referrals_to_opskit",
        "internal_crossproperty_inferred_non_bot_referrals_to_studykit",
        "internal_crossproperty_inferred_non_bot_referrals_to_careerkit",
        "internal_crossproperty_inferred_non_bot_referrals_to_housingkit",
        "internal_crossproperty_inferred_non_bot_referrals_to_taxkit",
        "internal_crossproperty_inferred_verified_referrals",
        "internal_crossproperty_inferred_non_bot_verified_referrals",
        "internal_crossproperty_inferred_unverified_referrals",
        "internal_crossproperty_inferred_non_bot_unverified_referrals",
        "internal_crossproperty_effective_referrals",
        "internal_crossproperty_effective_referrals_to_datekit",
        "internal_crossproperty_effective_referrals_to_budgetkit",
        "internal_crossproperty_effective_referrals_to_healthkit",
        "internal_crossproperty_effective_referrals_to_sleepkit",
        "internal_crossproperty_effective_referrals_to_focuskit",
        "internal_crossproperty_effective_referrals_to_opskit",
        "internal_crossproperty_effective_referrals_to_studykit",
        "internal_crossproperty_effective_referrals_to_careerkit",
        "internal_crossproperty_effective_referrals_to_housingkit",
        "internal_crossproperty_effective_referrals_to_taxkit",
        "internal_crossproperty_effective_non_bot_referrals",
        "internal_crossproperty_effective_non_bot_referrals_to_datekit",
        "internal_crossproperty_effective_non_bot_referrals_to_budgetkit",
        "internal_crossproperty_effective_non_bot_referrals_to_healthkit",
        "internal_crossproperty_effective_non_bot_referrals_to_sleepkit",
        "internal_crossproperty_effective_non_bot_referrals_to_focuskit",
        "internal_crossproperty_effective_non_bot_referrals_to_opskit",
        "internal_crossproperty_effective_non_bot_referrals_to_studykit",
        "internal_crossproperty_effective_non_bot_referrals_to_careerkit",
        "internal_crossproperty_effective_non_bot_referrals_to_housingkit",
        "internal_crossproperty_effective_non_bot_referrals_to_taxkit",
        "internal_crossproperty_high_confidence_non_bot_referrals",
        "internal_crossproperty_high_confidence_non_bot_referrals_to_datekit",
        "internal_crossproperty_high_confidence_non_bot_referrals_to_budgetkit",
        "internal_crossproperty_high_confidence_non_bot_referrals_to_healthkit",
        "internal_crossproperty_high_confidence_non_bot_referrals_to_sleepkit",
        "internal_crossproperty_high_confidence_non_bot_referrals_to_focuskit",
        "internal_crossproperty_high_confidence_non_bot_referrals_to_opskit",
        "internal_crossproperty_high_confidence_non_bot_referrals_to_studykit",
        "internal_crossproperty_high_confidence_non_bot_referrals_to_careerkit",
        "internal_crossproperty_high_confidence_non_bot_referrals_to_housingkit",
        "internal_crossproperty_high_confidence_non_bot_referrals_to_taxkit",
        "internal_crossproperty_low_confidence_non_bot_referrals",
        "known_bot_requests",
        "known_bot_unique_ips",
        "content_homepage_requests",
        "content_blog_requests",
        "content_tools_requests",
        "content_cheatsheets_requests",
        "content_datekit_requests",
        "content_budgetkit_requests",
        "content_healthkit_requests",
        "content_sleepkit_requests",
        "content_focuskit_requests",
        "content_opskit_requests",
        "content_studykit_requests",
        "content_careerkit_requests",
        "content_housingkit_requests",
        "content_taxkit_requests",
        "content_other_requests",
        "organic_homepage_referrals",
        "organic_blog_referrals",
        "organic_tools_referrals",
        "organic_cheatsheets_referrals",
        "organic_datekit_referrals",
        "organic_budgetkit_referrals",
        "organic_healthkit_referrals",
        "organic_sleepkit_referrals",
        "organic_focuskit_referrals",
        "organic_opskit_referrals",
        "organic_studykit_referrals",
        "organic_careerkit_referrals",
        "organic_housingkit_referrals",
        "organic_taxkit_referrals",
        "organic_other_referrals",
        "organic_non_bot_homepage_referrals",
        "organic_non_bot_blog_referrals",
        "organic_non_bot_tools_referrals",
        "organic_non_bot_cheatsheets_referrals",
        "organic_non_bot_datekit_referrals",
        "organic_non_bot_budgetkit_referrals",
        "organic_non_bot_healthkit_referrals",
        "organic_non_bot_sleepkit_referrals",
        "organic_non_bot_focuskit_referrals",
        "organic_non_bot_opskit_referrals",
        "organic_non_bot_studykit_referrals",
        "organic_non_bot_careerkit_referrals",
        "organic_non_bot_housingkit_referrals",
        "organic_non_bot_taxkit_referrals",
        "organic_non_bot_other_referrals",
    ]
    deltas = {}
    for metric in metrics:
        current_value = int(current_summary.get(metric, 0))
        previous_value = int(previous_summary.get(metric, 0))
        deltas[metric] = current_value - previous_value
        deltas[f"{metric}_pct"] = safe_pct_change(current_value, previous_value)

    return {
        "current_window": {
            "start": current_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "end": current_end.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "hours": int(current_summary.get("window_hours", 0)),
        },
        "previous_window": {
            "start": previous_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "end": current_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "hours": int(previous_summary.get("window_hours", 0)),
            "summary": previous_summary,
        },
        "deltas": deltas,
    }


def parse_args():
    parser = argparse.ArgumentParser(description="Analyze web-ceo nginx access logs.")
    parser.add_argument("--hours", type=int, default=24, help="Rolling time window in hours (default: 24)")
    parser.add_argument("--max-items", type=int, default=20, help="Max rows per printed section (default: 20)")
    parser.add_argument(
        "--compare-previous",
        action="store_true",
        help="Compare current window with the previous window of the same duration",
    )
    parser.add_argument("--json", type=str, default="", help="Write JSON output to this file")
    return parser.parse_args()


def main():
    args = parse_args()
    now = datetime.now(timezone.utc)
    window_hours = max(1, args.hours)
    current_start = now - timedelta(hours=window_hours)
    previous_start = current_start - timedelta(hours=window_hours)

    current_window = WindowStats()
    previous_window = WindowStats() if args.compare_previous else None
    events: list[tuple[datetime, str, str, str, str, str, str]] = []

    for logfile in LOG_FILES:
        try:
            lines = read_log_lines(logfile)
        except Exception as exc:
            print(f"Error reading {logfile}: {exc}", file=sys.stderr)
            continue

        for line in lines:
            match = LOG_PATTERN.match(line)
            if not match:
                continue

            try:
                ts = datetime.strptime(match.group("ts"), "%d/%b/%Y:%H:%M:%S %z").astimezone(timezone.utc)
            except ValueError:
                continue

            if args.compare_previous:
                if ts < previous_start:
                    continue
            else:
                if ts < current_start:
                    continue

            ip = match.group("ip")
            status = match.group("status")
            referrer = match.group("ref").strip()
            user_agent = match.group("ua").strip()
            path, query = parse_request_path_query(match.group("req"))
            events.append((ts, ip, status, referrer, path, query, user_agent))

    events.sort(key=lambda item: item[0])

    for ts, ip, status, referrer, path, query, user_agent in events:
        if args.compare_previous:
            target_window = current_window if ts >= current_start else previous_window
        else:
            target_window = current_window
        if target_window is None:
            continue
        target_window.record(ip, status, referrer, path, query, user_agent, ts)

    generated_at = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    summary = current_window.summary(generated_at, window_hours)
    comparison = None
    if args.compare_previous and previous_window is not None:
        previous_summary = previous_window.summary(current_start.strftime("%Y-%m-%dT%H:%M:%SZ"), window_hours)
        comparison = build_window_comparison(summary, previous_summary, current_start, now, previous_start)

    print(f"=== TRAFFIC SUMMARY (last {summary['window_hours']}h) ===")
    print(f"  total_requests: {summary['total_requests']}")
    print(f"  unique_ips: {summary['unique_ips']}")
    print(f"  clean_requests: {summary['clean_requests']}")
    print(f"  clean_unique_ips: {summary['clean_unique_ips']}")
    print(f"  content_requests: {summary['content_requests']}")
    print(f"  content_unique_ips: {summary['content_unique_ips']}")
    print(f"  suspicious_requests: {summary['suspicious_requests']}")
    print(f"  not_found_requests: {summary['not_found_requests']}")
    print(f"  suspicious_404: {summary['suspicious_404']}")
    print(f"  organic_referrals: {summary['organic_referrals']}")
    print(f"  organic_non_bot_referrals: {summary['organic_non_bot_referrals']}")
    print(f"  organic_kit_referrals: {summary['organic_kit_referrals']}")
    print(f"  organic_non_bot_kit_referrals: {summary['organic_non_bot_kit_referrals']}")
    print(f"  crosspromo_campaign_hits: {summary['crosspromo_campaign_hits']}")
    print(f"  crosspromo_campaign_hits_to_datekit: {summary['crosspromo_campaign_hits_to_datekit']}")
    print(f"  crosspromo_campaign_hits_to_budgetkit: {summary['crosspromo_campaign_hits_to_budgetkit']}")
    print(f"  crosspromo_campaign_hits_to_healthkit: {summary['crosspromo_campaign_hits_to_healthkit']}")
    print(f"  crosspromo_campaign_hits_to_sleepkit: {summary['crosspromo_campaign_hits_to_sleepkit']}")
    print(f"  crosspromo_campaign_hits_to_focuskit: {summary['crosspromo_campaign_hits_to_focuskit']}")
    print(f"  crosspromo_campaign_hits_to_opskit: {summary['crosspromo_campaign_hits_to_opskit']}")
    print(f"  crosspromo_campaign_hits_to_studykit: {summary['crosspromo_campaign_hits_to_studykit']}")
    print(f"  crosspromo_campaign_hits_to_careerkit: {summary['crosspromo_campaign_hits_to_careerkit']}")
    print(f"  crosspromo_campaign_hits_to_housingkit: {summary['crosspromo_campaign_hits_to_housingkit']}")
    print(f"  crosspromo_campaign_hits_to_taxkit: {summary['crosspromo_campaign_hits_to_taxkit']}")
    print(f"  crosspromo_non_bot_hits_to_datekit: {summary['crosspromo_non_bot_hits_to_datekit']}")
    print(f"  crosspromo_non_bot_hits_to_budgetkit: {summary['crosspromo_non_bot_hits_to_budgetkit']}")
    print(f"  crosspromo_non_bot_hits_to_healthkit: {summary['crosspromo_non_bot_hits_to_healthkit']}")
    print(f"  crosspromo_non_bot_hits_to_sleepkit: {summary['crosspromo_non_bot_hits_to_sleepkit']}")
    print(f"  crosspromo_non_bot_hits_to_focuskit: {summary['crosspromo_non_bot_hits_to_focuskit']}")
    print(f"  crosspromo_non_bot_hits_to_opskit: {summary['crosspromo_non_bot_hits_to_opskit']}")
    print(f"  crosspromo_non_bot_hits_to_studykit: {summary['crosspromo_non_bot_hits_to_studykit']}")
    print(f"  crosspromo_non_bot_hits_to_careerkit: {summary['crosspromo_non_bot_hits_to_careerkit']}")
    print(f"  crosspromo_non_bot_hits_to_housingkit: {summary['crosspromo_non_bot_hits_to_housingkit']}")
    print(f"  crosspromo_non_bot_hits_to_taxkit: {summary['crosspromo_non_bot_hits_to_taxkit']}")
    print(f"  crosspromo_source_attributed_hits: {summary['crosspromo_source_attributed_hits']}")
    print(f"  crosspromo_non_bot_source_attributed_hits: {summary['crosspromo_non_bot_source_attributed_hits']}")
    print(f"  crosspromo_hits_with_param_source: {summary['crosspromo_hits_with_param_source']}")
    print(f"  crosspromo_non_bot_hits_with_param_source: {summary['crosspromo_non_bot_hits_with_param_source']}")
    print(
        "  crosspromo_hits_with_param_source_without_referrer: "
        f"{summary['crosspromo_hits_with_param_source_without_referrer']}"
    )
    print(
        "  crosspromo_non_bot_hits_with_param_source_without_referrer: "
        f"{summary['crosspromo_non_bot_hits_with_param_source_without_referrer']}"
    )
    print(f"  crosspromo_hits_with_internal_referrer: {summary['crosspromo_hits_with_internal_referrer']}")
    print(f"  crosspromo_hits_with_inferred_source: {summary['crosspromo_hits_with_inferred_source']}")
    print(f"  crosspromo_inferred_verified_hits: {summary['crosspromo_inferred_verified_hits']}")
    print(f"  crosspromo_inferred_unverified_hits: {summary['crosspromo_inferred_unverified_hits']}")
    print(f"  crosspromo_hits_unattributed: {summary['crosspromo_hits_unattributed']}")
    print(f"  crosspromo_non_bot_hits_with_internal_referrer: {summary['crosspromo_non_bot_hits_with_internal_referrer']}")
    print(f"  crosspromo_non_bot_hits_with_inferred_source: {summary['crosspromo_non_bot_hits_with_inferred_source']}")
    print(f"  crosspromo_non_bot_inferred_verified_hits: {summary['crosspromo_non_bot_inferred_verified_hits']}")
    print(f"  crosspromo_non_bot_inferred_unverified_hits: {summary['crosspromo_non_bot_inferred_unverified_hits']}")
    print(f"  crosspromo_non_bot_hits_unattributed: {summary['crosspromo_non_bot_hits_unattributed']}")
    print(f"  crosspromo_hits_with_any_referrer: {summary['crosspromo_hits_with_any_referrer']}")
    print(f"  crosspromo_hits_without_referrer: {summary['crosspromo_hits_without_referrer']}")
    print(f"  crosspromo_non_bot_hits_with_any_referrer: {summary['crosspromo_non_bot_hits_with_any_referrer']}")
    print(f"  crosspromo_non_bot_hits_without_referrer: {summary['crosspromo_non_bot_hits_without_referrer']}")
    print(f"  crosspromo_hits_without_referrer_known_bot: {summary['crosspromo_hits_without_referrer_known_bot']}")
    print(f"  crosspromo_hits_without_referrer_non_bot: {summary['crosspromo_hits_without_referrer_non_bot']}")
    print(f"  crosspromo_known_bot_hits: {summary['crosspromo_known_bot_hits']}")
    print(f"  crosspromo_non_bot_hits: {summary['crosspromo_non_bot_hits']}")
    print(f"  crosspromo_non_bot_high_confidence_hits: {summary['crosspromo_non_bot_high_confidence_hits']}")
    print(f"  crosspromo_non_bot_low_confidence_hits: {summary['crosspromo_non_bot_low_confidence_hits']}")
    print(f"  crosspromo_suspected_automation_hits: {summary['crosspromo_suspected_automation_hits']}")
    print(f"  crosspromo_suspected_automation_unique_ips: {summary['crosspromo_suspected_automation_unique_ips']}")
    print(f"  crosspromo_source_mismatch_hits: {summary['crosspromo_source_mismatch_hits']}")
    print(f"  internal_crossproperty_referrals: {summary['internal_crossproperty_referrals']}")
    print(f"  internal_crossproperty_non_bot_referrals: {summary['internal_crossproperty_non_bot_referrals']}")
    print(f"  internal_crossproperty_inferred_referrals: {summary['internal_crossproperty_inferred_referrals']}")
    print(f"  internal_crossproperty_inferred_non_bot_referrals: {summary['internal_crossproperty_inferred_non_bot_referrals']}")
    print(f"  internal_crossproperty_inferred_verified_referrals: {summary['internal_crossproperty_inferred_verified_referrals']}")
    print(
        "  internal_crossproperty_inferred_non_bot_verified_referrals: "
        f"{summary['internal_crossproperty_inferred_non_bot_verified_referrals']}"
    )
    print(f"  internal_crossproperty_inferred_unverified_referrals: {summary['internal_crossproperty_inferred_unverified_referrals']}")
    print(
        "  internal_crossproperty_inferred_non_bot_unverified_referrals: "
        f"{summary['internal_crossproperty_inferred_non_bot_unverified_referrals']}"
    )
    print(f"  internal_crossproperty_effective_referrals: {summary['internal_crossproperty_effective_referrals']}")
    print(f"  internal_crossproperty_effective_non_bot_referrals: {summary['internal_crossproperty_effective_non_bot_referrals']}")
    print(
        "  internal_crossproperty_high_confidence_non_bot_referrals: "
        f"{summary['internal_crossproperty_high_confidence_non_bot_referrals']}"
    )
    print(
        "  internal_crossproperty_low_confidence_non_bot_referrals: "
        f"{summary['internal_crossproperty_low_confidence_non_bot_referrals']}"
    )
    print(f"  known_bot_requests: {summary['known_bot_requests']}")
    print(f"  known_bot_unique_ips: {summary['known_bot_unique_ips']}")
    print(f"  top_organic_non_bot_section: {summary['top_organic_non_bot_section']}")
    print(f"  top_organic_non_bot_page: {summary['top_organic_non_bot_page']}")
    print(f"  top_organic_non_bot_kit_section: {summary['top_organic_non_bot_kit_section']}")
    print(f"  top_organic_non_bot_kit_page: {summary['top_organic_non_bot_kit_page']}")
    print(f"  top_crosspromo_campaign_source: {summary['top_crosspromo_campaign_source']}")
    print(f"  top_crosspromo_campaign_target_section: {summary['top_crosspromo_campaign_target_section']}")
    print(f"  top_crosspromo_campaign_source_target_section: {summary['top_crosspromo_campaign_source_target_section']}")
    print(f"  clean_request_ratio: {summary['clean_request_ratio']}%")
    print(f"  suspicious_request_ratio: {summary['suspicious_request_ratio']}%")
    print(f"  known_bot_request_ratio: {summary['known_bot_request_ratio']}%")
    print(f"  organic_referral_ratio: {summary['organic_referral_ratio']}%")
    print(f"  organic_non_bot_referral_ratio: {summary['organic_non_bot_referral_ratio']}%")
    print(f"  organic_non_bot_kit_referral_ratio: {summary['organic_non_bot_kit_referral_ratio']}%")
    print(f"  internal_crossproperty_referral_ratio: {summary['internal_crossproperty_referral_ratio']}%")
    print(f"  internal_crossproperty_non_bot_referral_ratio: {summary['internal_crossproperty_non_bot_referral_ratio']}%")
    print(f"  internal_crossproperty_inferred_referral_ratio: {summary['internal_crossproperty_inferred_referral_ratio']}%")
    print(
        f"  internal_crossproperty_inferred_non_bot_referral_ratio: {summary['internal_crossproperty_inferred_non_bot_referral_ratio']}%"
    )
    print(f"  internal_crossproperty_effective_referral_ratio: {summary['internal_crossproperty_effective_referral_ratio']}%")
    print(
        f"  internal_crossproperty_effective_non_bot_referral_ratio: {summary['internal_crossproperty_effective_non_bot_referral_ratio']}%"
    )
    print(
        "  internal_crossproperty_high_confidence_non_bot_referral_ratio: "
        f"{summary['internal_crossproperty_high_confidence_non_bot_referral_ratio']}%"
    )
    print(
        "  internal_crossproperty_low_confidence_non_bot_referral_ratio: "
        f"{summary['internal_crossproperty_low_confidence_non_bot_referral_ratio']}%"
    )
    print(
        "  internal_crossproperty_high_confidence_non_bot_of_effective_ratio: "
        f"{summary['internal_crossproperty_high_confidence_non_bot_of_effective_ratio']}%"
    )
    print(f"  crosspromo_source_attribution_ratio: {summary['crosspromo_source_attribution_ratio']}%")
    print(f"  crosspromo_known_bot_ratio: {summary['crosspromo_known_bot_ratio']}%")
    print(f"  crosspromo_suspected_automation_ratio: {summary['crosspromo_suspected_automation_ratio']}%")
    print(f"  crosspromo_non_bot_source_attribution_ratio: {summary['crosspromo_non_bot_source_attribution_ratio']}%")
    print(f"  crosspromo_non_bot_high_confidence_ratio: {summary['crosspromo_non_bot_high_confidence_ratio']}%")
    print(f"  crosspromo_non_bot_low_confidence_ratio: {summary['crosspromo_non_bot_low_confidence_ratio']}%")
    print(f"  crosspromo_without_referrer_ratio: {summary['crosspromo_without_referrer_ratio']}%")
    print(f"  crosspromo_non_bot_without_referrer_ratio: {summary['crosspromo_non_bot_without_referrer_ratio']}%")
    print(f"  crosspromo_param_source_ratio: {summary['crosspromo_param_source_ratio']}%")
    print(f"  crosspromo_non_bot_param_source_ratio: {summary['crosspromo_non_bot_param_source_ratio']}%")
    print(
        "  crosspromo_param_source_without_referrer_ratio: "
        f"{summary['crosspromo_param_source_without_referrer_ratio']}%"
    )
    print(
        "  crosspromo_non_bot_param_source_without_referrer_ratio: "
        f"{summary['crosspromo_non_bot_param_source_without_referrer_ratio']}%"
    )
    print(f"  crosspromo_inferred_verification_ratio: {summary['crosspromo_inferred_verification_ratio']}%")
    print(
        "  crosspromo_non_bot_inferred_verification_ratio: "
        f"{summary['crosspromo_non_bot_inferred_verification_ratio']}%"
    )
    print(
        "  internal_crossproperty_inferred_verified_referral_ratio: "
        f"{summary['internal_crossproperty_inferred_verified_referral_ratio']}%"
    )
    print(
        "  internal_crossproperty_inferred_non_bot_verified_referral_ratio: "
        f"{summary['internal_crossproperty_inferred_non_bot_verified_referral_ratio']}%"
    )
    print(
        "  internal_crossproperty_inferred_unverified_referral_ratio: "
        f"{summary['internal_crossproperty_inferred_unverified_referral_ratio']}%"
    )
    print(
        "  internal_crossproperty_inferred_non_bot_unverified_referral_ratio: "
        f"{summary['internal_crossproperty_inferred_non_bot_unverified_referral_ratio']}%"
    )
    print()

    print("=== CONTENT SECTION BREAKDOWN (clean, non-asset) ===")
    for section_name in CONTENT_SECTION_NAMES:
        section_count = summary.get(f"content_{section_name}_requests", 0)
        section_share = summary.get("content_section_share_pct", {}).get(section_name, 0)
        print(f"  {section_name}: {section_count} ({section_share}%)")
    print()

    print("=== ORGANIC SECTION BREAKDOWN ===")
    for section_name in CONTENT_SECTION_NAMES:
        section_count = summary.get(f"organic_{section_name}_referrals", 0)
        section_share = summary.get("organic_section_share_pct", {}).get(section_name, 0)
        print(f"  {section_name}: {section_count} ({section_share}%)")
    print()

    print("=== ORGANIC NON-BOT SECTION BREAKDOWN ===")
    for section_name in CONTENT_SECTION_NAMES:
        section_count = summary.get(f"organic_non_bot_{section_name}_referrals", 0)
        section_share = summary.get("organic_non_bot_section_share_pct", {}).get(section_name, 0)
        print(f"  {section_name}: {section_count} ({section_share}%)")
    print()

    if comparison:
        print("=== WINDOW COMPARISON (current vs previous same-duration window) ===")
        for metric in [
            "total_requests",
            "unique_ips",
            "content_requests",
            "content_blog_requests",
            "content_tools_requests",
            "content_cheatsheets_requests",
            "content_datekit_requests",
            "content_budgetkit_requests",
            "content_healthkit_requests",
            "content_sleepkit_requests",
            "content_focuskit_requests",
            "content_opskit_requests",
            "content_studykit_requests",
            "content_careerkit_requests",
            "content_housingkit_requests",
            "content_taxkit_requests",
            "suspicious_requests",
            "not_found_requests",
            "organic_referrals",
            "organic_non_bot_referrals",
            "organic_kit_referrals",
            "organic_non_bot_kit_referrals",
            "organic_blog_referrals",
            "organic_tools_referrals",
            "organic_cheatsheets_referrals",
            "organic_datekit_referrals",
            "organic_budgetkit_referrals",
            "organic_healthkit_referrals",
            "organic_sleepkit_referrals",
            "organic_focuskit_referrals",
            "organic_opskit_referrals",
            "organic_studykit_referrals",
            "organic_careerkit_referrals",
            "organic_housingkit_referrals",
            "organic_taxkit_referrals",
            "organic_non_bot_blog_referrals",
            "organic_non_bot_tools_referrals",
            "organic_non_bot_cheatsheets_referrals",
            "organic_non_bot_datekit_referrals",
            "organic_non_bot_budgetkit_referrals",
            "organic_non_bot_healthkit_referrals",
            "organic_non_bot_sleepkit_referrals",
            "organic_non_bot_focuskit_referrals",
            "organic_non_bot_opskit_referrals",
            "organic_non_bot_studykit_referrals",
            "organic_non_bot_careerkit_referrals",
            "organic_non_bot_housingkit_referrals",
            "organic_non_bot_taxkit_referrals",
            "crosspromo_campaign_hits",
            "crosspromo_campaign_hits_to_datekit",
            "crosspromo_campaign_hits_to_budgetkit",
            "crosspromo_campaign_hits_to_healthkit",
            "crosspromo_campaign_hits_to_sleepkit",
            "crosspromo_campaign_hits_to_focuskit",
            "crosspromo_campaign_hits_to_opskit",
            "crosspromo_campaign_hits_to_studykit",
            "crosspromo_campaign_hits_to_careerkit",
            "crosspromo_campaign_hits_to_housingkit",
            "crosspromo_campaign_hits_to_taxkit",
            "crosspromo_non_bot_hits_to_datekit",
            "crosspromo_non_bot_hits_to_budgetkit",
            "crosspromo_non_bot_hits_to_healthkit",
            "crosspromo_non_bot_hits_to_sleepkit",
            "crosspromo_non_bot_hits_to_focuskit",
            "crosspromo_non_bot_hits_to_opskit",
            "crosspromo_non_bot_hits_to_studykit",
            "crosspromo_non_bot_hits_to_careerkit",
            "crosspromo_non_bot_hits_to_housingkit",
            "crosspromo_non_bot_hits_to_taxkit",
            "crosspromo_source_attributed_hits",
            "crosspromo_non_bot_source_attributed_hits",
            "crosspromo_hits_with_param_source",
            "crosspromo_non_bot_hits_with_param_source",
            "crosspromo_hits_with_param_source_without_referrer",
            "crosspromo_non_bot_hits_with_param_source_without_referrer",
            "crosspromo_hits_with_internal_referrer",
            "crosspromo_hits_with_inferred_source",
            "crosspromo_inferred_verified_hits",
            "crosspromo_inferred_unverified_hits",
            "crosspromo_hits_unattributed",
            "crosspromo_non_bot_hits_with_internal_referrer",
            "crosspromo_non_bot_hits_with_inferred_source",
            "crosspromo_non_bot_inferred_verified_hits",
            "crosspromo_non_bot_inferred_unverified_hits",
            "crosspromo_non_bot_hits_unattributed",
            "crosspromo_hits_with_any_referrer",
            "crosspromo_hits_without_referrer",
            "crosspromo_non_bot_hits_with_any_referrer",
            "crosspromo_non_bot_hits_without_referrer",
            "crosspromo_hits_without_referrer_known_bot",
            "crosspromo_hits_without_referrer_non_bot",
            "crosspromo_known_bot_hits",
            "crosspromo_non_bot_hits",
            "crosspromo_non_bot_high_confidence_hits",
            "crosspromo_non_bot_low_confidence_hits",
            "crosspromo_source_mismatch_hits",
            "internal_crossproperty_referrals",
            "internal_crossproperty_referrals_to_datekit",
            "internal_crossproperty_referrals_to_budgetkit",
            "internal_crossproperty_referrals_to_healthkit",
            "internal_crossproperty_referrals_to_sleepkit",
            "internal_crossproperty_referrals_to_focuskit",
            "internal_crossproperty_referrals_to_opskit",
            "internal_crossproperty_referrals_to_studykit",
            "internal_crossproperty_referrals_to_careerkit",
            "internal_crossproperty_referrals_to_housingkit",
            "internal_crossproperty_referrals_to_taxkit",
            "internal_crossproperty_non_bot_referrals",
            "internal_crossproperty_non_bot_referrals_to_datekit",
            "internal_crossproperty_non_bot_referrals_to_budgetkit",
            "internal_crossproperty_non_bot_referrals_to_healthkit",
            "internal_crossproperty_non_bot_referrals_to_sleepkit",
            "internal_crossproperty_non_bot_referrals_to_focuskit",
            "internal_crossproperty_non_bot_referrals_to_opskit",
            "internal_crossproperty_non_bot_referrals_to_studykit",
            "internal_crossproperty_non_bot_referrals_to_careerkit",
            "internal_crossproperty_non_bot_referrals_to_housingkit",
            "internal_crossproperty_non_bot_referrals_to_taxkit",
            "internal_crossproperty_inferred_referrals",
            "internal_crossproperty_inferred_referrals_to_datekit",
            "internal_crossproperty_inferred_referrals_to_budgetkit",
            "internal_crossproperty_inferred_referrals_to_healthkit",
            "internal_crossproperty_inferred_referrals_to_sleepkit",
            "internal_crossproperty_inferred_referrals_to_focuskit",
            "internal_crossproperty_inferred_referrals_to_opskit",
            "internal_crossproperty_inferred_referrals_to_studykit",
            "internal_crossproperty_inferred_referrals_to_careerkit",
            "internal_crossproperty_inferred_referrals_to_housingkit",
            "internal_crossproperty_inferred_referrals_to_taxkit",
            "internal_crossproperty_inferred_non_bot_referrals",
            "internal_crossproperty_inferred_non_bot_referrals_to_datekit",
            "internal_crossproperty_inferred_non_bot_referrals_to_budgetkit",
            "internal_crossproperty_inferred_non_bot_referrals_to_healthkit",
            "internal_crossproperty_inferred_non_bot_referrals_to_sleepkit",
            "internal_crossproperty_inferred_non_bot_referrals_to_focuskit",
            "internal_crossproperty_inferred_non_bot_referrals_to_opskit",
            "internal_crossproperty_inferred_non_bot_referrals_to_studykit",
            "internal_crossproperty_inferred_non_bot_referrals_to_careerkit",
            "internal_crossproperty_inferred_non_bot_referrals_to_housingkit",
            "internal_crossproperty_inferred_non_bot_referrals_to_taxkit",
            "internal_crossproperty_inferred_verified_referrals",
            "internal_crossproperty_inferred_non_bot_verified_referrals",
            "internal_crossproperty_inferred_unverified_referrals",
            "internal_crossproperty_inferred_non_bot_unverified_referrals",
            "internal_crossproperty_effective_referrals",
            "internal_crossproperty_effective_referrals_to_datekit",
            "internal_crossproperty_effective_referrals_to_budgetkit",
            "internal_crossproperty_effective_referrals_to_healthkit",
            "internal_crossproperty_effective_referrals_to_sleepkit",
            "internal_crossproperty_effective_referrals_to_focuskit",
            "internal_crossproperty_effective_referrals_to_opskit",
            "internal_crossproperty_effective_referrals_to_studykit",
            "internal_crossproperty_effective_referrals_to_careerkit",
            "internal_crossproperty_effective_referrals_to_housingkit",
            "internal_crossproperty_effective_referrals_to_taxkit",
            "internal_crossproperty_effective_non_bot_referrals",
            "internal_crossproperty_effective_non_bot_referrals_to_datekit",
            "internal_crossproperty_effective_non_bot_referrals_to_budgetkit",
            "internal_crossproperty_effective_non_bot_referrals_to_healthkit",
            "internal_crossproperty_effective_non_bot_referrals_to_sleepkit",
            "internal_crossproperty_effective_non_bot_referrals_to_focuskit",
            "internal_crossproperty_effective_non_bot_referrals_to_opskit",
            "internal_crossproperty_effective_non_bot_referrals_to_studykit",
            "internal_crossproperty_effective_non_bot_referrals_to_careerkit",
            "internal_crossproperty_effective_non_bot_referrals_to_housingkit",
            "internal_crossproperty_effective_non_bot_referrals_to_taxkit",
            "internal_crossproperty_high_confidence_non_bot_referrals",
            "internal_crossproperty_high_confidence_non_bot_referrals_to_datekit",
            "internal_crossproperty_high_confidence_non_bot_referrals_to_budgetkit",
            "internal_crossproperty_high_confidence_non_bot_referrals_to_healthkit",
            "internal_crossproperty_high_confidence_non_bot_referrals_to_sleepkit",
            "internal_crossproperty_high_confidence_non_bot_referrals_to_focuskit",
            "internal_crossproperty_high_confidence_non_bot_referrals_to_opskit",
            "internal_crossproperty_high_confidence_non_bot_referrals_to_studykit",
            "internal_crossproperty_high_confidence_non_bot_referrals_to_careerkit",
            "internal_crossproperty_high_confidence_non_bot_referrals_to_housingkit",
            "internal_crossproperty_high_confidence_non_bot_referrals_to_taxkit",
            "internal_crossproperty_low_confidence_non_bot_referrals",
            "known_bot_requests",
            "known_bot_unique_ips",
        ]:
            delta = comparison["deltas"][metric]
            delta_pct = comparison["deltas"][f"{metric}_pct"]
            delta_pct_label = "n/a" if delta_pct is None else f"{delta_pct:+.2f}%"
            print(f"  {metric}: {delta:+d} ({delta_pct_label})")
        print()

    print("=== STATUS CODES ===")
    for code, count in current_window.status_counts.most_common(args.max_items):
        print(f"  {code}: {count}")
    print()

    print("=== TOP PAGES (non-asset) ===")
    for path, count in current_window.page_counts.most_common(args.max_items):
        print(f"  {count:4d}  {path}")
    print()

    print("=== ORGANIC ENGINES ===")
    for engine, count in current_window.organic_engine_counts.most_common(args.max_items):
        print(f"  {engine}: {count}")
    print()

    print("=== ORGANIC NON-BOT ENGINES ===")
    for engine, count in current_window.organic_non_bot_engine_counts.most_common(args.max_items):
        print(f"  {engine}: {count}")
    print()

    print("=== TOP ORGANIC LANDING PAGES ===")
    for path, count in current_window.organic_page_counts.most_common(args.max_items):
        print(f"  {count:4d}  {path}")
    print()

    print("=== TOP ORGANIC NON-BOT LANDING PAGES ===")
    for path, count in current_window.organic_non_bot_page_counts.most_common(args.max_items):
        print(f"  {count:4d}  {path}")
    print()

    print("=== TOP ORGANIC NON-BOT KIT LANDING PAGES ===")
    organic_non_bot_kit_page_counts = Counter(
        {
            path: count
            for path, count in current_window.organic_non_bot_page_counts.items()
            if classify_content_section(path) in KIT_SECTION_NAMES
        }
    )
    for path, count in organic_non_bot_kit_page_counts.most_common(args.max_items):
        print(f"  {count:4d}  {path}")
    print()

    print("=== TOP EXTERNAL REFERRERS ===")
    for referrer, count in current_window.external_referrers.most_common(args.max_items):
        print(f"  {count:4d}  {referrer}")
    print()

    print("=== CROSSPROMO CAMPAIGN LANDINGS ===")
    for path, count in current_window.crosspromo_campaign_pages.most_common(args.max_items):
        print(f"  {count:4d}  {path}")
    print()

    print("=== CROSSPROMO CAMPAIGN SOURCES ===")
    for source, count in current_window.crosspromo_campaign_sources.most_common(args.max_items):
        print(f"  {count:4d}  {source}")
    print()

    print("=== CROSSPROMO CAMPAIGN SOURCE PAGES ===")
    for source_path, count in current_window.crosspromo_campaign_source_pages.most_common(args.max_items):
        print(f"  {count:4d}  {source_path}")
    print()

    print("=== CROSSPROMO CAMPAIGN PARAM-SOURCE PAGES (from utm_content) ===")
    for source_path, count in current_window.crosspromo_campaign_param_source_pages.most_common(args.max_items):
        print(f"  {count:4d}  {source_path}")
    print()

    print("=== CROSSPROMO CAMPAIGN SOURCE SECTIONS ===")
    for section, count in current_window.crosspromo_campaign_source_sections.most_common(args.max_items):
        print(f"  {section}: {count}")
    print()

    print("=== CROSSPROMO CAMPAIGN PARAM-SOURCE SECTIONS (from utm_content) ===")
    for section, count in current_window.crosspromo_campaign_param_source_sections.most_common(args.max_items):
        print(f"  {section}: {count}")
    print()

    print("=== CROSSPROMO CAMPAIGN TARGET SECTIONS ===")
    for section, count in current_window.crosspromo_campaign_target_sections.most_common(args.max_items):
        print(f"  {section}: {count}")
    print()

    print("=== CROSSPROMO CAMPAIGN SOURCE->TARGET SECTION PAIRS ===")
    for pair, count in current_window.crosspromo_campaign_source_target_sections.most_common(args.max_items):
        print(f"  {count:4d}  {pair}")
    print()

    print("=== CROSSPROMO CAMPAIGN SOURCE->TARGET PAGE PAIRS ===")
    for pair, count in current_window.crosspromo_campaign_page_path_pairs.most_common(args.max_items):
        print(f"  {count:4d}  {pair}")
    print()

    print("=== CROSSPROMO NON-BOT CAMPAIGN SOURCES ===")
    for source, count in current_window.crosspromo_non_bot_campaign_sources.most_common(args.max_items):
        print(f"  {count:4d}  {source}")
    print()

    print("=== CROSSPROMO NON-BOT CAMPAIGN SOURCE PAGES ===")
    for source_path, count in current_window.crosspromo_non_bot_campaign_source_pages.most_common(args.max_items):
        print(f"  {count:4d}  {source_path}")
    print()

    print("=== CROSSPROMO NON-BOT CAMPAIGN PARAM-SOURCE PAGES (from utm_content) ===")
    for source_path, count in current_window.crosspromo_non_bot_campaign_param_source_pages.most_common(args.max_items):
        print(f"  {count:4d}  {source_path}")
    print()

    print("=== CROSSPROMO NON-BOT CAMPAIGN SOURCE SECTIONS ===")
    for section, count in current_window.crosspromo_non_bot_campaign_source_sections.most_common(args.max_items):
        print(f"  {section}: {count}")
    print()

    print("=== CROSSPROMO NON-BOT CAMPAIGN PARAM-SOURCE SECTIONS (from utm_content) ===")
    for section, count in current_window.crosspromo_non_bot_campaign_param_source_sections.most_common(args.max_items):
        print(f"  {section}: {count}")
    print()

    print("=== CROSSPROMO NON-BOT CAMPAIGN TARGET SECTIONS ===")
    for section, count in current_window.crosspromo_non_bot_campaign_target_sections.most_common(args.max_items):
        print(f"  {section}: {count}")
    print()

    print("=== CROSSPROMO NON-BOT CAMPAIGN SOURCE->TARGET SECTION PAIRS ===")
    for pair, count in current_window.crosspromo_non_bot_campaign_source_target_sections.most_common(args.max_items):
        print(f"  {count:4d}  {pair}")
    print()

    print("=== CROSSPROMO NON-BOT CAMPAIGN SOURCE->TARGET PAGE PAIRS ===")
    for pair, count in current_window.crosspromo_non_bot_campaign_page_path_pairs.most_common(args.max_items):
        print(f"  {count:4d}  {pair}")
    print()

    print("=== TOP CROSSPROMO KNOWN BOT USER AGENTS ===")
    for user_agent, count in current_window.crosspromo_known_bot_user_agents.most_common(args.max_items):
        print(f"  {count:4d}  {user_agent}")
    print()

    print("=== TOP CROSSPROMO SUSPECTED AUTOMATION USER AGENTS ===")
    for user_agent, count in current_window.crosspromo_suspected_automation_user_agents.most_common(args.max_items):
        print(f"  {count:4d}  {user_agent}")
    print()

    print(
        "=== INTERNAL CROSS-PROPERTY REFERRALS "
        "(to DateKit/BudgetKit/HealthKit/SleepKit/FocusKit/OpsKit/StudyKit/CareerKit/HousingKit/TaxKit) ==="
    )
    print(f"  total: {current_window.internal_crossproperty_referrals}")
    print(f"  inferred total from campaign source paths: {current_window.internal_crossproperty_inferred_referrals}")
    print(f"  inferred verified (recent source evidence): {current_window.internal_crossproperty_inferred_verified_referrals}")
    print(f"  inferred unverified (no recent source evidence): {current_window.internal_crossproperty_inferred_unverified_referrals}")
    print(
        "  effective total (referrer + inferred): "
        f"{current_window.internal_crossproperty_referrals + current_window.internal_crossproperty_inferred_referrals}"
    )
    print("  by target section:")
    for section, count in current_window.internal_crossproperty_target_sections.most_common(args.max_items):
        print(f"    {section}: {count}")
    print("  inferred by target section:")
    for section, count in current_window.internal_crossproperty_inferred_target_sections.most_common(args.max_items):
        print(f"    {section}: {count}")
    print("  by source section:")
    for section, count in current_window.internal_crossproperty_source_sections.most_common(args.max_items):
        print(f"    {section}: {count}")
    print("  top source pages:")
    for source_path, count in current_window.internal_crossproperty_source_pages.most_common(args.max_items):
        print(f"    {count:4d}  {source_path}")
    print("  top target pages:")
    for target_path, count in current_window.internal_crossproperty_target_pages.most_common(args.max_items):
        print(f"    {count:4d}  {target_path}")
    print("  non-bot total:")
    print(f"    {current_window.internal_crossproperty_non_bot_referrals}")
    print("  non-bot inferred total:")
    print(f"    {current_window.internal_crossproperty_inferred_non_bot_referrals}")
    print("  non-bot inferred verified:")
    print(f"    {current_window.internal_crossproperty_inferred_non_bot_verified_referrals}")
    print("  non-bot inferred unverified:")
    print(f"    {current_window.internal_crossproperty_inferred_non_bot_unverified_referrals}")
    print("  non-bot effective total (referrer + inferred):")
    print(
        "    "
        f"{current_window.internal_crossproperty_non_bot_referrals + current_window.internal_crossproperty_inferred_non_bot_referrals}"
    )
    print("  non-bot by target section:")
    for section, count in current_window.internal_crossproperty_non_bot_target_sections.most_common(args.max_items):
        print(f"    {section}: {count}")
    print("  non-bot inferred by target section:")
    for section, count in current_window.internal_crossproperty_inferred_non_bot_target_sections.most_common(args.max_items):
        print(f"    {section}: {count}")
    print("  non-bot by source section:")
    for section, count in current_window.internal_crossproperty_non_bot_source_sections.most_common(args.max_items):
        print(f"    {section}: {count}")
    print("  non-bot top source pages:")
    for source_path, count in current_window.internal_crossproperty_non_bot_source_pages.most_common(args.max_items):
        print(f"    {count:4d}  {source_path}")
    print("  non-bot top target pages:")
    for target_path, count in current_window.internal_crossproperty_non_bot_target_pages.most_common(args.max_items):
        print(f"    {count:4d}  {target_path}")
    print()

    print("=== TOP 404 PAGES ===")
    for path, count in current_window.not_found_pages.most_common(args.max_items):
        print(f"  {count:4d}  {path}")
    print()

    print("=== TOP CLEAN 404 PAGES ===")
    for path, count in current_window.clean_not_found_pages.most_common(args.max_items):
        print(f"  {count:4d}  {path}")
    print()

    print("=== TOP SUSPICIOUS PATHS ===")
    for path, count in current_window.suspicious_paths.most_common(args.max_items):
        print(f"  {count:4d}  {path}")

    report = {
        "summary": summary,
        "status_codes": counter_to_sorted_list(current_window.status_counts, "code", args.max_items),
        "content_sections": counter_to_sorted_list(current_window.content_section_counts, "section", args.max_items),
        "organic_sections": counter_to_sorted_list(current_window.organic_section_counts, "section", args.max_items),
        "organic_non_bot_sections": counter_to_sorted_list(current_window.organic_non_bot_section_counts, "section", args.max_items),
        "top_pages": counter_to_sorted_list(current_window.page_counts, "path", args.max_items),
        "organic_engines": counter_to_sorted_list(current_window.organic_engine_counts, "engine", args.max_items),
        "organic_non_bot_engines": counter_to_sorted_list(
            current_window.organic_non_bot_engine_counts,
            "engine",
            args.max_items,
        ),
        "top_organic_pages": counter_to_sorted_list(current_window.organic_page_counts, "path", args.max_items),
        "top_organic_non_bot_pages": counter_to_sorted_list(current_window.organic_non_bot_page_counts, "path", args.max_items),
        "top_organic_non_bot_kit_pages": counter_to_sorted_list(organic_non_bot_kit_page_counts, "path", args.max_items),
        "top_external_referrers": counter_to_sorted_list(current_window.external_referrers, "referrer", args.max_items),
        "crosspromo_campaign_pages": counter_to_sorted_list(current_window.crosspromo_campaign_pages, "path", args.max_items),
        "crosspromo_campaign_sources": counter_to_sorted_list(current_window.crosspromo_campaign_sources, "source", args.max_items),
        "crosspromo_campaign_source_pages": counter_to_sorted_list(
            current_window.crosspromo_campaign_source_pages,
            "path",
            args.max_items,
        ),
        "crosspromo_campaign_param_source_pages": counter_to_sorted_list(
            current_window.crosspromo_campaign_param_source_pages,
            "path",
            args.max_items,
        ),
        "crosspromo_campaign_source_sections": counter_to_sorted_list(
            current_window.crosspromo_campaign_source_sections,
            "section",
            args.max_items,
        ),
        "crosspromo_campaign_param_source_sections": counter_to_sorted_list(
            current_window.crosspromo_campaign_param_source_sections,
            "section",
            args.max_items,
        ),
        "crosspromo_campaign_target_sections": counter_to_sorted_list(
            current_window.crosspromo_campaign_target_sections,
            "section",
            args.max_items,
        ),
        "crosspromo_campaign_source_target_sections": counter_to_sorted_list(
            current_window.crosspromo_campaign_source_target_sections,
            "pair",
            args.max_items,
        ),
        "crosspromo_campaign_page_path_pairs": counter_to_sorted_list(
            current_window.crosspromo_campaign_page_path_pairs,
            "pair",
            args.max_items,
        ),
        "crosspromo_non_bot_campaign_sources": counter_to_sorted_list(
            current_window.crosspromo_non_bot_campaign_sources,
            "source",
            args.max_items,
        ),
        "crosspromo_non_bot_campaign_source_pages": counter_to_sorted_list(
            current_window.crosspromo_non_bot_campaign_source_pages,
            "path",
            args.max_items,
        ),
        "crosspromo_non_bot_campaign_param_source_pages": counter_to_sorted_list(
            current_window.crosspromo_non_bot_campaign_param_source_pages,
            "path",
            args.max_items,
        ),
        "crosspromo_non_bot_campaign_source_sections": counter_to_sorted_list(
            current_window.crosspromo_non_bot_campaign_source_sections,
            "section",
            args.max_items,
        ),
        "crosspromo_non_bot_campaign_param_source_sections": counter_to_sorted_list(
            current_window.crosspromo_non_bot_campaign_param_source_sections,
            "section",
            args.max_items,
        ),
        "crosspromo_non_bot_campaign_target_sections": counter_to_sorted_list(
            current_window.crosspromo_non_bot_campaign_target_sections,
            "section",
            args.max_items,
        ),
        "crosspromo_non_bot_campaign_source_target_sections": counter_to_sorted_list(
            current_window.crosspromo_non_bot_campaign_source_target_sections,
            "pair",
            args.max_items,
        ),
        "crosspromo_non_bot_campaign_page_path_pairs": counter_to_sorted_list(
            current_window.crosspromo_non_bot_campaign_page_path_pairs,
            "pair",
            args.max_items,
        ),
        "crosspromo_known_bot_user_agents": counter_to_sorted_list(
            current_window.crosspromo_known_bot_user_agents,
            "user_agent",
            args.max_items,
        ),
        "crosspromo_suspected_automation_user_agents": counter_to_sorted_list(
            current_window.crosspromo_suspected_automation_user_agents,
            "user_agent",
            args.max_items,
        ),
        "internal_crossproperty_target_sections": counter_to_sorted_list(
            current_window.internal_crossproperty_target_sections,
            "section",
            args.max_items,
        ),
        "internal_crossproperty_source_sections": counter_to_sorted_list(
            current_window.internal_crossproperty_source_sections,
            "section",
            args.max_items,
        ),
        "internal_crossproperty_source_pages": counter_to_sorted_list(
            current_window.internal_crossproperty_source_pages,
            "path",
            args.max_items,
        ),
        "internal_crossproperty_target_pages": counter_to_sorted_list(
            current_window.internal_crossproperty_target_pages,
            "path",
            args.max_items,
        ),
        "internal_crossproperty_non_bot_target_sections": counter_to_sorted_list(
            current_window.internal_crossproperty_non_bot_target_sections,
            "section",
            args.max_items,
        ),
        "internal_crossproperty_non_bot_source_sections": counter_to_sorted_list(
            current_window.internal_crossproperty_non_bot_source_sections,
            "section",
            args.max_items,
        ),
        "internal_crossproperty_non_bot_source_pages": counter_to_sorted_list(
            current_window.internal_crossproperty_non_bot_source_pages,
            "path",
            args.max_items,
        ),
        "internal_crossproperty_non_bot_target_pages": counter_to_sorted_list(
            current_window.internal_crossproperty_non_bot_target_pages,
            "path",
            args.max_items,
        ),
        "internal_crossproperty_inferred_target_sections": counter_to_sorted_list(
            current_window.internal_crossproperty_inferred_target_sections,
            "section",
            args.max_items,
        ),
        "internal_crossproperty_inferred_non_bot_target_sections": counter_to_sorted_list(
            current_window.internal_crossproperty_inferred_non_bot_target_sections,
            "section",
            args.max_items,
        ),
        "internal_crossproperty_inferred_verified_target_sections": counter_to_sorted_list(
            current_window.internal_crossproperty_inferred_verified_target_sections,
            "section",
            args.max_items,
        ),
        "internal_crossproperty_inferred_non_bot_verified_target_sections": counter_to_sorted_list(
            current_window.internal_crossproperty_inferred_non_bot_verified_target_sections,
            "section",
            args.max_items,
        ),
        "internal_crossproperty_inferred_unverified_target_sections": counter_to_sorted_list(
            current_window.internal_crossproperty_inferred_unverified_target_sections,
            "section",
            args.max_items,
        ),
        "internal_crossproperty_inferred_non_bot_unverified_target_sections": counter_to_sorted_list(
            current_window.internal_crossproperty_inferred_non_bot_unverified_target_sections,
            "section",
            args.max_items,
        ),
        "top_404_pages": counter_to_sorted_list(current_window.not_found_pages, "path", args.max_items),
        "top_clean_404_pages": counter_to_sorted_list(current_window.clean_not_found_pages, "path", args.max_items),
        "top_suspicious_paths": counter_to_sorted_list(current_window.suspicious_paths, "path", args.max_items),
    }
    if comparison:
        report["comparison"] = comparison

    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
            f.write("\n")


if __name__ == "__main__":
    main()
