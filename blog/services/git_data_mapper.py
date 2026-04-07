"""Common data transformations for Git providers."""
from typing import Any, Dict, List


def format_stars(count: int) -> str:
    """Format star count with K suffix for thousands."""
    return f"{count / 1000:.1f}K" if count >= 1000 else str(count)


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
