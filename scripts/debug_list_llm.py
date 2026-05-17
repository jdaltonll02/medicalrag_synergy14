#!/usr/bin/env python3
"""
Debug why list questions return empty from the LLM.
Tests the exact same prompt path as the pipeline.
"""
import sys
import json
import yaml
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.llm.openai_client import OpenAIClient

CONFIG_PATH = "configs/fullpipeline.yaml"

QUERIES = [
    "Which are the most common viral haemorrhagic fevers?",
    "Please list the drugs that are used as HIV prophylaxis.",
    "What are the common symptoms of Cushing Syndrome?",
    "What are the symptoms of glucocorticoid withdrawal syndrome after surgery?",
]

def build_prompt(query: str, type_guidance: str, docs_obj: dict) -> str:
    user_part = f"User Prompt: Answer the following question: {query}{type_guidance}"
    context_part = "Context Prompt: Here are the documents:\n" + json.dumps(docs_obj, ensure_ascii=False, indent=2)
    return user_part + "\n\n" + context_part

def main():
    with open(CONFIG_PATH) as f:
        cfg = yaml.safe_load(f)

    llm_cfg = cfg["llm"]
    client = OpenAIClient(
        model=llm_cfg["model"],
        api_key=llm_cfg.get("api_key"),
        base_url=llm_cfg.get("base_url"),
        project_id=llm_cfg.get("project_id"),
        temperature=llm_cfg.get("temperature", 0.0),
        max_tokens=llm_cfg.get("max_tokens", 1024),
    )
    system_prompt = llm_cfg.get("system_prompt", "")

    type_guidance = (
        "\n\nThis is a LIST question. You MUST respond with ONLY a numbered list — no introduction, no conclusion, no prose. "
        "Each line must be a single short entity name (drug, gene, disease, protein, etc.). "
        "Format EXACTLY as:\n1. First item\n2. Second item\n3. Third item\n"
        "Use the documents and your biomedical knowledge. Always provide a list — never leave it empty."
    )

    # Test 1: Empty docs (pure model knowledge)
    print("=" * 70)
    print("TEST 1: No documents (pure model knowledge)")
    print("=" * 70)
    for query in QUERIES:
        print(f"\nQ: {query}")
        prompt = build_prompt(query, type_guidance, {})
        raw = client.generate(prompt, system_prompt=system_prompt)
        print(f"RAW response ({len(raw)} chars): {repr(raw[:300])}")

    # Test 2: One dummy relevant doc
    print("\n" + "=" * 70)
    print("TEST 2: With one relevant stub document")
    print("=" * 70)
    stub_docs = {
        "doc1": {
            "doc_id": "PMID_TEST",
            "title": "Review of viral haemorrhagic fevers",
            "abstract": "Viral haemorrhagic fevers include Ebola, Marburg, Lassa fever, Dengue, Yellow fever, Crimean-Congo haemorrhagic fever, and Rift Valley fever.",
            "relevance_score": 0.9
        }
    }
    query = "Which are the most common viral haemorrhagic fevers?"
    print(f"\nQ: {query}")
    prompt = build_prompt(query, type_guidance, stub_docs)
    raw = client.generate(prompt, system_prompt=system_prompt)
    print(f"RAW response ({len(raw)} chars): {repr(raw[:300])}")

    # Test 3: Check raw API response object (refusal field)
    print("\n" + "=" * 70)
    print("TEST 3: Check for API refusal field")
    print("=" * 70)
    query = QUERIES[0]
    prompt = build_prompt(query, type_guidance, {})
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    try:
        resp = client.client.chat.completions.create(
            model=client.model,
            messages=messages,
            temperature=client.temperature,
            max_tokens=client.max_tokens,
        )
        choice = resp.choices[0]
        print(f"finish_reason : {choice.finish_reason}")
        print(f"content       : {repr(choice.message.content)}")
        print(f"refusal       : {repr(getattr(choice.message, 'refusal', 'N/A'))}")
        print(f"full message  : {choice.message}")
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    main()
