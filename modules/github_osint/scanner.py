from typing import Any, Dict, List, Optional

import httpx

from core.module import BaseModule
from core.output import standard_response, save_output


class GithubOsintModule(BaseModule):
    name = "github_osint"
    description = "Passive GitHub user reconnaissance (public metadata only)"

    def run(self, username: str, fetch_repos: bool = False, output: Optional[str] = None) -> Dict[str, Any]:
        """Fetch basic public GitHub profile metadata and optionally repos.

        This is a passive, safe lookup against the public GitHub REST API.
        It does not attempt to access private data or clone repositories.
        """
        base = f"https://api.github.com/users/{username}"
        try:
            resp = httpx.get(base, timeout=10)
            if resp.status_code == 404:
                return standard_response("github_osint", data={"exists": False})

            resp.raise_for_status()
            profile = resp.json()

            data: Dict[str, Any] = {
                "exists": True,
                "profile": {
                    "login": profile.get("login"),
                    "name": profile.get("name"),
                    "followers": profile.get("followers"),
                    "public_repos": profile.get("public_repos"),
                    "created_at": profile.get("created_at"),
                },
            }

            if fetch_repos:
                repos_url = f"{base}/repos"
                r = httpx.get(repos_url, params={"per_page": 100}, timeout=15)
                if r.status_code == 200:
                    repos = []
                    for item in r.json():
                        repos.append(
                            {
                                "name": item.get("name"),
                                "stars": item.get("stargazers_count", 0),
                                "language": item.get("language"),
                            }
                        )
                    data["repos"] = repos

            if output:
                save_output(output, data)

            return standard_response("github_osint", data=data)
        except Exception as e:  # network / parsing errors
            return standard_response("github_osint", error=str(e))
