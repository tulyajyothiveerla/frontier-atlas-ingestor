import os
import re
import asyncio
import aiohttp
from typing import Optional, Tuple, Dict
from dotenv import load_dotenv
from rapidfuzz import fuzz

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# Regex to extract clean owner/repo
GITHUB_REGEX = re.compile(
    r"https?://github\.com/([a-zA-Z0-9_-]+)/([a-zA-Z0-9_.-]+)",
    re.IGNORECASE
)


class PaperGitHubMatcher:
    def __init__(self, github_token: Optional[str] = None):
        self.github_token = github_token or GITHUB_TOKEN
        self.headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "GraphOne-FrontierAtlas-Ingestion"
        }
        if self.github_token:
            self.headers["Authorization"] = f"token {self.github_token}"

    def extract_github_from_text(self, text: str) -> Optional[str]:
        """Tier 1: Direct regex extraction from arXiv abstract/comments."""
        if not text:
            return None
        match = GITHUB_REGEX.search(text)
        if match:
            owner, repo = match.group(1), match.group(2).rstrip(".git").rstrip("/").rstrip(")")
            # Ignore generic links (e.g., github.com/topics, github.com/features)
            if owner.lower() in ["topics", "features", "about", "pricing", "explore"]:
                return None
            return f"https://github.com/{owner}/{repo}"
        return None

    async def query_papers_with_code(self, session: aiohttp.ClientSession, arxiv_id: str) -> Optional[str]:
        """Tier 2: Papers With Code API lookup by arXiv ID."""
        if not arxiv_id:
            return None

        clean_id = arxiv_id.split("/")[-1].split("v")[0].strip()
        url = f"https://paperswithcode.com/api/v1/papers/?arxiv_id={clean_id}"

        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=6)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    results = data.get("results", [])
                    if results and results[0].get("repository_url"):
                        return results[0]["repository_url"]
        except Exception:
            pass
        return None

    async def get_repo_stars(self, session: aiohttp.ClientSession, github_url: str) -> int:
        """Fetches live stargazers_count directly from repo metadata endpoint."""
        match = GITHUB_REGEX.search(github_url)
        if not match:
            return 0

        owner, repo = match.group(1), match.group(2).rstrip(".git").rstrip("/")
        api_url = f"https://api.github.com/repos/{owner}/{repo}"

        try:
            async with session.get(api_url, headers=self.headers, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("stargazers_count", 0)
        except Exception:
            pass
        return 0

    async def resolve_and_enrich(
        self,
        session: aiohttp.ClientSession,
        paper_title: str,
        paper_id: str,
        raw_text: str
    ) -> Tuple[Optional[str], int]:
        """
        Determines the correct GitHub repository and fetches real-time star count.
        Returns: (github_url, github_stars)
        """
        # Step 1: Direct link in paper abstract/comments (Most reliable)
        github_url = self.extract_github_from_text(raw_text)

        # Step 2: Papers With Code verification if not in text
        if not github_url:
            github_url = await self.query_papers_with_code(session, paper_id)

        # Step 3: Fetch dynamic live stars if URL was resolved
        stars = 0
        if github_url:
            stars = await self.get_repo_stars(session, github_url)

        return (github_url if github_url else None, stars)