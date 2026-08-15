import os
import re
import csv
import socket
import asyncio
import aiohttp
import xml.etree.ElementTree as ET
from dotenv import load_dotenv

load_dotenv()

ARXIV_URL = "https://export.arxiv.org/api/query"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

NAMESPACE = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom"
}

GITHUB_REGEX = re.compile(
    r"https?://github\.com/([a-zA-Z0-9_-]+)/([a-zA-Z0-9_.-]+)",
    re.IGNORECASE
)

FIELDNAMES = [
    "schemaVersion",
    "recordType",
    "content.title",
    "content.authors",
    "content.paper_url",
    "content.github_url",
    "content.github_stars",
    "content.published_date"
]


def extract_github_url_from_text(text: str) -> str:
    """Extracts first valid GitHub repository link from text."""
    if not text:
        return ""
    match = GITHUB_REGEX.search(text)
    if match:
        owner = match.group(1)
        repo = match.group(2).rstrip(".git").rstrip("/").rstrip(")")
        if owner.lower() in ["topics", "features", "about", "pricing", "explore", "site"]:
            return ""
        return f"https://github.com/{owner}/{repo}"
    return ""


async def query_papers_with_code(session: aiohttp.ClientSession, paper_url: str) -> str:
    """Fallback: Checks Papers With Code API using arXiv ID."""
    arxiv_id = paper_url.split("/")[-1].split("v")[0].strip()
    api_url = f"https://paperswithcode.com/api/v1/papers/?arxiv_id={arxiv_id}"

    try:
        async with session.get(api_url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
            if resp.status == 200:
                data = await resp.json()
                results = data.get("results", [])
                if results and results[0].get("repository_url"):
                    return results[0]["repository_url"]
    except Exception:
        pass
    return ""


async def get_github_stars(session: aiohttp.ClientSession, github_url: str) -> int:
    """Fetches live stargazers count from GitHub REST API."""
    if not github_url:
        return 0

    match = GITHUB_REGEX.search(github_url)
    if not match:
        return 0

    owner, repo = match.group(1), match.group(2).rstrip(".git").rstrip("/")
    api_url = f"https://api.github.com/repos/{owner}/{repo}"

    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "AI-Paper-Pipeline"
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"

    try:
        async with session.get(api_url, headers=headers, timeout=aiohttp.ClientTimeout(total=6)) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get("stargazers_count", 0)
    except Exception:
        pass
    return 0


def append_to_csv(filepath: str, rows: list):
    """Appends records immediately to CSV so data is saved incrementally."""
    file_exists = os.path.exists(filepath)
    with open(filepath, "a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDNAMES)
        if not file_exists:
            writer.writeheader()
        writer.writerows(rows)


async def fetch_papers(target_count: int = 1000, batch_size: int = 100):
    output_csv = "data/research_papers.csv"
    os.makedirs("data", exist_ok=True)

    # Clean existing file before fresh run
    if os.path.exists(output_csv):
        os.remove(output_csv)

    total_collected = 0
    start = 0

    # Force IPv4 socket resolution to prevent Windows DNS bugs
    connector = aiohttp.TCPConnector(family=socket.AF_INET)

    print(f"🚀 Starting resilient ingestion pipeline: Target = {target_count} papers...")

    async with aiohttp.ClientSession(connector=connector) as session:
        while total_collected < target_count:
            print(f"Fetching arXiv batch: start={start}, batch_size={batch_size}...")

            params = {
                "search_query": "cat:cs.AI OR cat:cs.LG OR cat:cs.CL OR cat:cs.CV",
                "start": start,
                "max_results": batch_size,
                "sortBy": "submittedDate",
                "sortOrder": "descending"
            }

            # Retry loop with exponential backoff for network resilience
            xml_data = None
            for attempt in range(1, 5):
                try:
                    async with session.get(ARXIV_URL, params=params, timeout=aiohttp.ClientTimeout(total=20)) as response:
                        if response.status == 200:
                            xml_data = await response.text()
                            break
                        else:
                            print(f"⚠️ arXiv returned status {response.status}. Retrying...")
                except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
                    print(f"⚠️ Network glitch ({exc}). Retrying attempt {attempt}/4 in {attempt * 3}s...")
                    await asyncio.sleep(attempt * 3)

            if not xml_data:
                print(f"❌ Failed to fetch batch starting at {start} after 4 retries. Moving to next...")
                start += batch_size
                continue

            root = ET.fromstring(xml_data)
            entries = root.findall("atom:entry", NAMESPACE)

            if not entries:
                print("No more entries returned.")
                break

            batch_records = []
            for entry in entries:
                if total_collected + len(batch_records) >= target_count:
                    break

                title_el = entry.find("atom:title", NAMESPACE)
                title = " ".join(title_el.text.split()) if title_el is not None and title_el.text else ""

                published_el = entry.find("atom:published", NAMESPACE)
                published = published_el.text.strip() if published_el is not None else ""

                authors = []
                for author in entry.findall("atom:author", NAMESPACE):
                    name_el = author.find("atom:name", NAMESPACE)
                    if name_el is not None and name_el.text:
                        authors.append(name_el.text.strip())

                id_el = entry.find("atom:id", NAMESPACE)
                paper_url = id_el.text.strip() if id_el is not None else ""

                summary_el = entry.find("atom:summary", NAMESPACE)
                summary = summary_el.text if summary_el is not None else ""

                comment_el = entry.find("arxiv:comment", NAMESPACE)
                comment = comment_el.text if comment_el is not None else ""

                github_url = extract_github_url_from_text(f"{summary} {comment}")
                if not github_url:
                    github_url = await query_papers_with_code(session, paper_url)

                github_stars = 0
                if github_url:
                    github_stars = await get_github_stars(session, github_url)

                batch_records.append({
                    "schemaVersion": "1.0",
                    "recordType": "RESEARCH_PAPER",
                    "content.title": title,
                    "content.authors": ", ".join(authors),
                    "content.paper_url": paper_url,
                    "content.github_url": github_url,
                    "content.github_stars": github_stars,
                    "content.published_date": published
                })

            # Save batch immediately
            append_to_csv(output_csv, batch_records)
            total_collected += len(batch_records)

            print(f"✅ Accumulated: {total_collected} / {target_count} papers saved.")
            start += batch_size

            # Polite 2.5s delay
            await asyncio.sleep(2.5)

    print(f"\n🎉 Finished! Exactly {total_collected} research papers saved to {output_csv}")


if __name__ == "__main__":
    asyncio.run(fetch_papers(target_count=1000, batch_size=100))