import os
import requests
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

headers = {
    "Accept": "application/vnd.github+json"
}

# Attach authorization only if token exists
if GITHUB_TOKEN:
    headers["Authorization"] = f"token {GITHUB_TOKEN}"


def search_github(query: str):
    url = "https://api.github.com/search/repositories"

    params = {
        "q": query,
        "sort": "stars",
        "order": "desc"
    }

    try:
        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=10
        )
        print("Status:", response.status_code)

        if response.status_code != 200:
            print("Error response:", response.text)
            return []

        data = response.json()
        return data.get("items", [])
    except Exception as e:
        print(f"Request failed: {e}")
        return []


if __name__ == "__main__":
    results = search_github("BERT")

    for repo in results[:5]:
        print("Repository:", repo["full_name"])
        print("Stars:", repo["stargazers_count"])
        print("URL:", repo["html_url"])
        print("-------------------")