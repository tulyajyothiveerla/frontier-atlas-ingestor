import os
import re
import csv
import socket
import asyncio
import aiohttp
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from email.utils import parsedate_to_datetime
import dateparser

NEWS_SOURCES = [
    {"name": "The Verge AI", "url": "https://www.theverge.com/rss/index.xml"},
    {"name": "TechCrunch AI", "url": "https://techcrunch.com/category/artificial-intelligence/feed/"},
    {"name": "VentureBeat AI", "url": "https://venturebeat.com/category/ai/feed/"},
    {"name": "MIT Technology Review AI", "url": "https://www.technologyreview.com/feed/"},
    {"name": "Ars Technica AI", "url": "https://feeds.arstechnica.com/arstechnica/index"}
]

JOB_SOURCES = [
    {"name": "Remotive AI Jobs", "url": "https://remotive.com/api/remote-jobs?category=software-dev&search=AI"},
    {"name": "Remotive Data & ML", "url": "https://remotive.com/api/remote-jobs?category=data"},
    {"name": "Jobicy AI Jobs", "url": "https://jobicy.com/api/v2/remote-jobs?count=50&industry=engineering&tag=ai"},
    {"name": "WeWorkRemotely AI/Backend", "url": "https://weworkremotely.com/categories/remote-back-end-programming-jobs.rss"},
    {"name": "WeWorkRemotely DevOps/Data", "url": "https://weworkremotely.com/categories/remote-devops-sysadmin-jobs.rss"}
]

def parse_date_safely(date_str: str) -> Optional[datetime]:
    """Parses various date formats into standard UTC datetime."""
    if not date_str:
        return None
    try:
        dt = parsedate_to_datetime(date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        pass

    try:
        clean_str = date_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(clean_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        pass

    try:
        dt = dateparser.parse(date_str)
        if dt:
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
    except Exception:
        pass

    return None

def is_within_last_24_hours(dt: Optional[datetime], now_utc: datetime) -> bool:
    if not dt:
        return False
    diff = now_utc - dt
    return timedelta(seconds=0) <= diff <= timedelta(hours=24)

async def scrape_fresh_news(session: aiohttp.ClientSession, now_utc: datetime) -> List[Dict[str, Any]]:
    print("\n🚀 Ingesting 24-Hour Fresh AI News...")
    news_records = []
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    for src in NEWS_SOURCES:
        try:
            async with session.get(src["url"], headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    print(f"  ├─ [{src['name']}] HTTP Status {resp.status}")
                    continue

                content = await resp.text()
                root = ET.fromstring(content)

                items = root.findall(".//item")
                if not items:
                    items = root.findall(".//{http://www.w3.org/2005/Atom}entry")

                src_count = 0
                for item in items:
                    # Title
                    title_el = item.find("title")
                    if title_el is None:
                        title_el = item.find("{http://www.w3.org/2005/Atom}title")
                    title = " ".join(title_el.text.split()) if title_el is not None and title_el.text else ""

                    # Link
                    link_el = item.find("link")
                    if link_el is None:
                        link_el = item.find("{http://www.w3.org/2005/Atom}link")
                    
                    link = ""
                    if link_el is not None:
                        link = link_el.text or link_el.attrib.get("href", "")

                    # Date
                    pub_el = item.find("pubDate")
                    if pub_el is None:
                        pub_el = item.find("{http://www.w3.org/2005/Atom}published")
                    if pub_el is None:
                        pub_el = item.find("{http://www.w3.org/2005/Atom}updated")

                    pub_str = pub_el.text.strip() if pub_el is not None and pub_el.text else ""
                    dt = parse_date_safely(pub_str)

                    if dt and is_within_last_24_hours(dt, now_utc):
                        news_records.append({
                            "schemaVersion": "1.0",
                            "recordType": "NEWS",
                            "source.name": src["name"],
                            "source.url": link or src["url"],
                            "content.title": title,
                            "content.published_date": dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
                            "collectedAt": now_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
                        })
                        src_count += 1

                print(f"  ├─ [{src['name']}]: {src_count} articles published within last 24h")
        except Exception as exc:
            print(f"  ├─ [{src['name']}] Error: {exc}")

    return news_records

async def scrape_fresh_jobs(session: aiohttp.ClientSession, now_utc: datetime) -> List[Dict[str, Any]]:
    print("\n🚀 Ingesting 24-Hour Fresh AI Jobs...")
    job_records = []
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    for src in JOB_SOURCES:
        try:
            async with session.get(src["url"], headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    continue

                src_count = 0
                if "api" in src["url"]:
                    data = await resp.json()
                    jobs = data.get("jobs", [])

                    for j in jobs:
                        company = j.get("company_name", "AI Enterprise")
                        pub_str = j.get("publication_date") or j.get("pubDate") or ""
                        dt = parse_date_safely(pub_str)

                        title = (j.get("title") or "").lower()
                        if "engineer" in title or "developer" in title:
                            role_family = "Engineering"
                        elif "research" in title or "scientist" in title:
                            role_family = "AI Research"
                        elif "product" in title:
                            role_family = "Product Management"
                        else:
                            role_family = "Data & AI"

                        if dt and is_within_last_24_hours(dt, now_utc):
                            job_records.append({
                                "schemaVersion": "1.0",
                                "recordType": "JOB",
                                "content.company": company,
                                "content.date": dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
                                "content.is_remote": True,
                                "content.role_family": role_family
                            })
                            src_count += 1
                else:
                    content = await resp.text()
                    root = ET.fromstring(content)
                    items = root.findall(".//item")

                    for item in items:
                        title_el = item.find("title")
                        raw_title = title_el.text.strip() if title_el is not None and title_el.text else ""

                        if ":" in raw_title:
                            company, role = raw_title.split(":", 1)
                        else:
                            company, role = "AI Startup", raw_title

                        pub_el = item.find("pubDate")
                        pub_str = pub_el.text.strip() if pub_el is not None and pub_el.text else ""
                        dt = parse_date_safely(pub_str)

                        if dt and is_within_last_24_hours(dt, now_utc):
                            job_records.append({
                                "schemaVersion": "1.0",
                                "recordType": "JOB",
                                "content.company": company.strip(),
                                "content.date": dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
                                "content.is_remote": True,
                                "content.role_family": "Engineering"
                            })
                            src_count += 1

                print(f"  ├─ [{src['name']}]: {src_count} fresh jobs found")
        except Exception as exc:
            print(f"  ├─ [{src['name']}] Error: {exc}")

    return job_records

def save_to_csv(filepath: str, fieldnames: List[str], data: List[Dict[str, Any]]):
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)
    print(f"✅ Saved {len(data)} fresh records to {filepath}")

async def main():
    os.makedirs("data", exist_ok=True)
    connector = aiohttp.TCPConnector(family=socket.AF_INET)
    now_utc = datetime.now(timezone.utc)

    async with aiohttp.ClientSession(connector=connector) as session:
        news = await scrape_fresh_news(session, now_utc)
        save_to_csv(
            "data/news.csv",
            ["schemaVersion", "recordType", "source.name", "source.url", "content.title", "content.published_date", "collectedAt"],
            news
        )

        jobs = await scrape_fresh_jobs(session, now_utc)
        save_to_csv(
            "data/jobs.csv",
            ["schemaVersion", "recordType", "content.company", "content.date", "content.is_remote", "content.role_family"],
            jobs
        )

if __name__ == "__main__":
    asyncio.run(main())