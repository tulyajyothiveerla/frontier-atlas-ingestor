# FrontierAtlas — Intelligence Ingestion & Entity Resolution Engine

A production-grade intelligence ingestion pipeline designed for the global AI ecosystem. Built for **GraphOne / FrontierAtlas**, this system ingests, normalizes, deduplicates, and correlates entities across multi-modal data sources into a canonical Knowledge Graph.

---

## 📊 Live Deliverable: Google Sheet Dataset
👉 **[Click Here to View the Ingested Dataset on Google Sheets](PASTE_YOUR_GOOGLE_SHEET_URL_HERE)**

### Dataset Tabs Included:
1. **`Startups`**: 1,000 AI organization entities with validated metadata and source references.
2. **`Products`**: 1,000 AI model/product artifacts with canonical naming and repository mappings.
3. **`Research Papers`**: 1,000 ArXiv AI research papers correlated with real-time GitHub repository URLs and star counts.
4. **`Jobs`**: Verified 24-hour fresh AI engineering roles and hiring signals.
5. **`News`**: Real-time 24-hour industry intelligence across top tier AI news outlets.
6. **`Entity Mapping Log`**: Comprehensive resolution audit trail capturing match types (`EXACT`, `FUZZY`, `FALLBACK`) and similarity confidence scores.

---

## 🏗️ Architecture & System Design
The complete architectural blueprint is documented in [`architecture.pdf`](./architecture.pdf), covering:
- **Resilient Multi-Source Scraping**: Concurrency-controlled, rate-limited extraction with anti-bot mitigation and dynamic user-agent rotation.
- **Multi-Tier LLM Orchestration**: Primary high-reasoning LLM extraction with automatic lightweight fallback upon encountering 413 (Payload Too Large) or 429 (Rate Limit) errors.
- **Real-Time Freshness Ingestion**: Strict 24-hour time window enforcement ($\Delta t \le 24\text{ hours}$) for dynamic news and job signal feeds.
- **Deterministic & Fuzzy Entity Resolution**: Automated entity normalization, exact matching against canonical dictionaries, and Levenshtein-based fuzzy clustering with strict threshold barriers.
- **Knowledge Graph Target Schema**: Formatted for seamless ingestion into Neo4j graph schemas (`Organization`, `Product`, `Paper`, `JobPosting`, `NewsArticle`).

---

## 🚀 Setup & Execution

### 1. Install Dependencies
```bash
pip install -r requirements.txt
