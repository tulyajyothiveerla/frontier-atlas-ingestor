import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

def build_architecture_pdf(filename="architecture.pdf"):
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=16,
        leading=20,
        textColor=colors.HexColor("#0F172A"),
        fontName="Helvetica-Bold",
        spaceAfter=2
    )
    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#475569"),
        fontName="Helvetica",
        spaceAfter=6
    )
    h1_style = ParagraphStyle(
        'H1',
        parent=styles['Heading2'],
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#1E3A8A"),
        fontName="Helvetica-Bold",
        spaceBefore=8,
        spaceAfter=3
    )
    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontSize=8.5,
        leading=11.5,
        textColor=colors.HexColor("#334155"),
        fontName="Helvetica"
    )
    bullet_style = ParagraphStyle(
        'Bullet',
        parent=body_style,
        leftIndent=10,
        firstLineIndent=-6,
        spaceAfter=2
    )
    callout_style = ParagraphStyle(
        'Callout',
        parent=body_style,
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#1E293B"),
        fontName="Helvetica-Oblique"
    )

    story = []

    # Title Banner
    story.append(Paragraph("FrontierAtlas / GraphOne — Production Intelligence System Architecture", title_style))
    story.append(Paragraph("<b>System Design Document:</b> High-Throughput Ingestion (500k Scale), Resilient Multi-Tier LLMs, Anti-Bot Camouflage & Knowledge Graph Persistence", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#1E3A8A"), spaceAfter=8))

    # Section 1: 500k Scaling Architecture
    story.append(Paragraph("1. Distributed Ingestion Pipeline & Scaling to 500k+ Records", h1_style))
    story.append(Paragraph("To scale entity extraction from 1,000 to 500,000+ records without pipeline degradation, the system decouples crawler discovery, LLM inference, and graph persistence into an event-driven microservices architecture:", body_style))
    story.append(Spacer(1, 3))
    story.append(Paragraph("• <b>Domain-Partitioned Kafka Queues:</b> Target discovery jobs are partitioned by root domain (e.g., <i>arxiv.org</i>, <i>techcrunch.com</i>), allowing independent concurrency limits and politeness controls per source without global throughput bottlenecks.", bullet_style))
    story.append(Paragraph("• <b>Stateless Async Workers:</b> Python worker nodes running <code>aiohttp</code> and <code>asyncio</code> auto-scale horizontally on Kubernetes (HPA) governed by consumer queue lag metrics.", bullet_style))
    story.append(Paragraph("• <b>Batch Checkpointing & Memory Safety:</b> Workers flush records incrementally to durable staging storage every 100 items with non-blocking I/O, preventing memory exhaustion and ensuring zero data loss on unexpected restarts.", bullet_style))

    # Section 2: Anti-Bot Strategy
    story.append(Paragraph("2. Anti-Bot Navigation & Stealth Harvesting", h1_style))
    story.append(Paragraph("• <b>TLS/JA4 Fingerprint Camouflage:</b> Employs <code>curl_cffi</code> to match standard Chrome/Safari TLS cipher suites and HTTP/2 settings, preventing automated flags from Cloudflare Turnstile, DataDome, and Akamai.", bullet_style))
    story.append(Paragraph("• <b>Headless Browser Management:</b> Aggressive JavaScript pages use Playwright Async wrapped with <code>playwright-stealth</code>, randomized viewport geometries, human mouse bezier paths, and rotating residential IP proxies.", bullet_style))
    story.append(Paragraph("• <b>Politeness Rate Shaping:</b> Adaptive token-bucket rate limiters dynamically adjust per-domain request intervals based on upstream HTTP response codes (e.g., automatically backing off upon encountering HTTP 429).", bullet_style))

    # Section 3: Multi-Tier LLM Orchestrator
    story.append(Paragraph("3. Resilient Multi-Tier LLM Orchestration (413 & 429 Mitigation)", h1_style))
    story.append(Paragraph("• <b>413 Payload Too Large Prevention:</b> Raw HTML documents undergo structural DOM pruning (stripping scripts, styles, SVG vectors, and base64 binaries) followed by sentence-aware window chunking to cap prompt payloads under token limits. If an upstream 413 is received, chunks dynamically halve and retry.", bullet_style))
    story.append(Paragraph("• <b>429 Rate-Limit Exponential Backoff:</b> Rate limits trigger full exponential backoff with randomized jitter [<i>T = 2^attempt + Uniform(0.5, 1.5)</i>], preventing synchronized thundering-herd retries across concurrent worker nodes.", bullet_style))
    story.append(Paragraph("• <b>Circuit-Breaker Failover Chain:</b> Seamlessly cascades across providers: <b>Tier 1 (Gemini 1.5 Flash)</b> → <b>Tier 2 (Groq Llama-3-70B)</b> → <b>Tier 3 (DeepSeek-V3)</b>. If a tier exhausts retries, requests fail over automatically without worker interruption.", bullet_style))

    # Section 4: Freshness & Deduplication
    story.append(Paragraph("4. 24-Hour Freshness Tracking & Deduplication Engine", h1_style))
    story.append(Paragraph("• <b>RedisBloom Fast-Path Deduplication:</b> Distributed Bloom filters check URL and title signatures in sub-millisecond O(1) time (false-positive rate &lt; 0.1%), preventing redundant parsing across worker nodes.", bullet_style))
    story.append(Paragraph("• <b>Strict UTC Delta Window:</b> Ingested publication timestamps are parsed across RFC-822, ISO-8601, and natural-language formats, normalizing to UTC. Records where <i>Δt = now_utc - t_published &gt; 24.0h</i> are rejected at the ingestion boundary.", bullet_style))
    story.append(Paragraph("• <b>Content-Hashing Identity:</b> Entity records generate SHA-256 signatures over normalized attributes (<code>name + date + url</code>) with a 7-day sliding TTL to prevent duplicate insertions.", bullet_style))

    # Section 5: Storage & Knowledge Graph
    story.append(Paragraph("5. Primary Storage & Intelligence Graph Architecture", h1_style))
    story.append(Paragraph("• <b>PostgreSQL (ACID Primary Store):</b> Stores schema-validated entities, raw payload backups, ingestion telemetry, and historical GitHub star metrics.", bullet_style))
    story.append(Paragraph("• <b>Neo4j Property Graph Layer:</b> Models dynamic industry relations: <code>(Startup)-[:BUILT]->(Product)</code>, <code>(Startup)-[:PUBLISHED]->(Paper)</code>, <code>(Paper)-[:HAS_REPO]->(GitHubRepo)</code>, and <code>(Startup)-[:OPENED]->(Job)</code>.", bullet_style))
    story.append(Paragraph("• <b>Qdrant Vector Database:</b> Stores 1536-dimensional embeddings for research abstracts and news articles to enable semantic deduplication, topic clustering, and retrieval.", bullet_style))

    doc.build(story)
    print(f"✅ Successfully compiled {filename}")

if __name__ == "__main__":
    build_architecture_pdf()