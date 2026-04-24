"""Common data transformations for Git providers."""
from typing import Any, Dict, List

_GITLAB_VISIBILITY_LEVELS: Dict[int, str] = {20: "public", 10: "internal", 0: "private", 5: "private"}


def format_stars(count: int) -> str:
    """Format star count with K suffix for thousands."""
    return f"{count / 1000:.1f}K" if count >= 1000 else str(count)


def sanitize_repository_url(repository_url: str) -> str:
    """Normalize repository URL for browser navigation."""
    return (repository_url or "").rstrip("/").removesuffix(".git")


def normalize_repository_info(data: Dict[str, Any], provider_type: str, repository_url: str) -> Dict[str, Any]:
    """Normalize repository metadata across providers for UI rendering."""
    fallback_url = sanitize_repository_url(repository_url)
    if not isinstance(data, dict) or not data:
        return {
            "name": "",
            "url": fallback_url,
            "description": "",
            "homepage_url": "",
            "last_updated": None,
            "visibility": "unknown",
            "clone_url_https": repository_url,
        }

    if provider_type == "github":
        return {
            "name": data.get("name", ""),
            "url": data.get("html_url") or fallback_url,
            "description": data.get("description") or "",
            "homepage_url": data.get("homepage") or "",
            "last_updated": data.get("updated_at") or data.get("pushed_at"),
            "visibility": "private" if data.get("private") else data.get("visibility", "public"),
            "clone_url_https": data.get("clone_url") or repository_url,
        }

    if provider_type == "gitlab":
        visibility = data.get("visibility") or _GITLAB_VISIBILITY_LEVELS.get(
            data.get("visibility_level"), "unknown"
        )
        return {
            "name": data.get("name", ""),
            "url": data.get("web_url") or fallback_url,
            "description": data.get("description") or "",
            "homepage_url": data.get("web_url") or "",
            "last_updated": data.get("last_activity_at") or data.get("updated_at"),
            "visibility": visibility,
            "clone_url_https": data.get("http_url_to_repo") or repository_url,
        }

    if provider_type == "gitea":
        return {
            "name": data.get("name", ""),
            "url": data.get("html_url") or fallback_url,
            "description": data.get("description") or "",
            "homepage_url": data.get("website") or "",
            "last_updated": data.get("updated_at"),
            "visibility": "private" if data.get("private") else "public",
            "clone_url_https": data.get("clone_url") or repository_url,
        }

    return {
        "name": data.get("name", ""),
        "url": fallback_url,
        "description": data.get("description") or "",
        "homepage_url": data.get("homepage_url") or "",
        "last_updated": data.get("last_updated"),
        "visibility": data.get("visibility", "unknown"),
        "clone_url_https": data.get("clone_url_https") or repository_url,
    }


def normalize_commit(commit: Dict[str, Any], provider_type: str) -> Dict:
    """Normalize commit data across all providers."""
    extractors = {
        "github": lambda c: (c["sha"][:7], c["commit"]["message"].split("\n")[0], 
                             c["commit"]["author"]["name"], c["commit"]["author"]["date"], c["html_url"]),
        "gitlab": lambda c: (c["id"][:7], c["title"], c["author_name"], c["created_at"], c["web_url"]),
        "gitea": lambda c: (c["sha"][:7], c["commit"]["message"].split("\n")[0],
                            c["commit"]["author"]["name"], c["commit"]["author"]["date"], c["html_url"]),
    }
    
    hash_val, msg, author, timestamp, url = extractors.get(provider_type, lambda c: ("", "", "", "", ""))(commit)
    return {"hash": hash_val, "message": msg, "author": author, "timestamp": timestamp, "url": url}


def normalize_branch(branch: Dict[str, Any], provider_type: str) -> Dict:
    """Normalize branch data across all providers."""
    extractors = {
        "github": lambda b: (b["name"], b["name"] in ("main", "master"), b["commit"]["sha"][:7]),
        "gitlab": lambda b: (b["name"], b.get("default", False), b["commit"]["id"][:7]),
        "gitea": lambda b: (b["name"], b.get("default", False), b["commit"]["id"][:7]),
    }
    
    name, is_default, sha = extractors.get(provider_type, lambda b: ("", False, ""))(branch)
    return {"name": name, "is_default": is_default, "last_commit_sha": sha}


def normalize_commits(data: Any, provider_type: str, limit: int = None) -> List[Dict]:
    """Normalize list of commits from any provider."""
    if not isinstance(data, list):
        return []
    items = data[:limit] if limit else data
    return [normalize_commit(item, provider_type) for item in items]


def normalize_branches(data: Any, provider_type: str) -> List[Dict]:
    """Normalize list of branches from any provider."""
    if not isinstance(data, list):
        return []
    return [normalize_branch(item, provider_type) for item in data]


def base_metadata(provider_icon: str, provider_name: str, provider_color: str) -> Dict:
    """Base metadata template for all providers."""
    return {
        "icon": provider_icon,
        "provider": provider_name,
        "provider_color": provider_color,
    }
