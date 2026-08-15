import os
import aiohttp
import asyncio
from dotenv import load_dotenv


load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

GITHUB_API = "https://api.github.com/repos/google-research/bert"


async def test_github():
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }

    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(GITHUB_API) as response:
            print("Status:", response.status)

            data = await response.json()

            print("Repository:", data.get("full_name"))
            print("Stars:", data.get("stargazers_count"))


asyncio.run(test_github())