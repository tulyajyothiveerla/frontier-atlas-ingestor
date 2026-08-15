import os
import re
import csv
import pandas as pd
from typing import List, Dict, Tuple, Optional
from rapidfuzz import fuzz, process

# Seed database of 50+ prominent Canonical AI Organizations
CANONICAL_SEED_LIST = [
    "OpenAI", "Anthropic", "Mistral AI", "Cohere", "Hugging Face", "Stability AI",
    "Midjourney", "Scale AI", "Perplexity AI", "Runway", "DeepSeek", "ElevenLabs",
    "Inflection AI", "Adept AI", "Character.AI", "Black Forest Labs", "Together AI",
    "Anyscale", "Weights & Biases", "Replicate", "Grok xAI", "Pinecone", "Qdrant",
    "Weaviate", "Chroma", "LangChain", "LlamaIndex", "Modal Labs", "Baseten",
    "OctoAI", "Cerebras Systems", "Groq", "SambaNova Systems", "Writer", "Glean",
    "Jasper AI", "Copy.ai", "Synthesia", "Pika Labs", "HeyGen", "Shield AI",
    "Harvey AI", "Tabnine", "Poolside", "Cognition AI", "Magic AI", "Hippocratic AI",
    "EvolutionaryScale", "Cursor", "Deci AI"
]

LEGAL_SUFFIXES_REGEX = re.compile(
    r"(?i)\b(inc|incorporated|corp|corporation|llc|ltd|limited|co|company|"
    r"technologies|technology|tech|labs|lab|ai|artificial intelligence|io|pbc)\b\.?"
)


class EntityResolverEngine:
    def __init__(self, canonical_seed: List[str], similarity_threshold: float = 80.0):
        self.canonical_seed = canonical_seed
        self.canonical_map_lower = {name.lower(): name for name in canonical_seed}
        self.similarity_threshold = similarity_threshold

    def clean_name(self, raw_name: str) -> str:
        """Strips legal entity wrappers, punctuation noise, and extra whitespace."""
        cleaned = re.sub(r"[®™,\.]", " ", raw_name)
        cleaned = LEGAL_SUFFIXES_REGEX.sub(" ", cleaned)
        return " ".join(cleaned.split()).strip()

    def resolve(self, raw_name: str) -> Tuple[str, str, Optional[float]]:
        raw_stripped = raw_name.strip()
        raw_lower = raw_stripped.lower()

        # Tier 1: Direct Exact Match
        if raw_lower in self.canonical_map_lower:
            return self.canonical_map_lower[raw_lower], "EXACT", 100.0

        # Tier 2: Cleaned Exact Match (post-suffix stripping)
        cleaned = self.clean_name(raw_stripped)
        cleaned_lower = cleaned.lower()
        if cleaned_lower in self.canonical_map_lower:
            return self.canonical_map_lower[cleaned_lower], "CLEANED_EXACT", 100.0

        # Tier 3: RapidFuzz Token-Sort Similarity
        target = cleaned if cleaned else raw_stripped
        match = process.extractOne(
            target,
            self.canonical_seed,
            scorer=fuzz.token_sort_ratio
        )

        if match:
            best_canonical, score, _ = match
            if score >= self.similarity_threshold:
                return best_canonical, "FUZZY", round(float(score), 2)

        # Tier 4: Cleaned Raw Fallback
        fallback_name = cleaned if cleaned else raw_stripped
        return fallback_name, "FALLBACK", None


def main():
    print("🚀 Running Deterministic Entity Resolution Pipeline...")
    resolver = EntityResolverEngine(CANONICAL_SEED_LIST, similarity_threshold=80.0)

    raw_entities = set()

    # Ingest raw entity names from Startups dataset
    if os.path.exists("data/startups.csv"):
        df_s = pd.read_csv("data/startups.csv")
        if "content.entityName" in df_s.columns:
            raw_entities.update(df_s["content.entityName"].dropna().astype(str).tolist())

    # Ingest raw names from Products dataset
    if os.path.exists("data/products.csv"):
        df_p = pd.read_csv("data/products.csv")
        if "content.startupName" in df_p.columns:
            raw_entities.update(df_p["content.startupName"].dropna().astype(str).tolist())

    # Include benchmark variants to showcase messy scraping normalization
    benchmark_variants = [
        "OpenAI, Inc.", "Open AI", "Anthropic PBC", "Anthropic Labs",
        "Mistral AI Technologies", "Cohere Inc.", "Hugging Face, Inc.",
        "Stability.AI", "DeepSeek-AI", "Scale AI Corp", "Groq, Inc."
    ]
    raw_entities.update(benchmark_variants)

    resolution_log = []
    for raw in sorted(raw_entities):
        if not raw.strip():
            continue
        canonical, match_type, score = resolver.resolve(raw)
        resolution_log.append({
            "raw_name": raw,
            "canonical_name": canonical,
            "match_type": match_type,
            "score": score if score is not None else ""
        })

    # Save to data/entity_mapping.csv
    output_path = "data/entity_mapping.csv"
    os.makedirs("data", exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        fieldnames = ["raw_name", "canonical_name", "match_type", "score"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(resolution_log)

    print(f"✅ Successfully mapped {len(resolution_log)} entities to {output_path}")

    # Display sample resolved logs
    df_log = pd.DataFrame(resolution_log)
    print("\nSample Resolution Log (High-Value Matches):")
    sample_view = df_log[df_log["match_type"].isin(["EXACT", "CLEANED_EXACT", "FUZZY"])]
    print(sample_view.head(10).to_string(index=False))


if __name__ == "__main__":
    main()