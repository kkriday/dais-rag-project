"""
LLM-as-judge evaluation using Ollama.

Scores three RAG metrics per question:
  - Faithfulness      : Does the answer stay within the retrieved context?
  - Answer Relevance  : Does the answer actually address the question?
  - Context Relevance : Are the retrieved chunks relevant to the question?

Usage:
    python -m app.eval_llm_judge \
        --results data/eval_results.jsonl \
        --chunks  data/chunks \
        --out     data/eval_judge_results.jsonl
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1")

_JUDGE_PROMPT = """\
You are a strict evaluator for a Retrieval-Augmented Generation (RAG) system.
Given a question, retrieved context chunks, and the system's answer, score three metrics.

Return ONLY valid JSON in exactly this format (no extra text):
{{
  "faithfulness": <integer 1-5>,
  "faithfulness_reason": "<one sentence>",
  "answer_relevance": <integer 1-5>,
  "answer_relevance_reason": "<one sentence>",
  "context_relevance": <integer 1-5>,
  "context_relevance_reason": "<one sentence>"
}}

Scoring rubric:
- faithfulness      1=answer makes claims not in context, 5=answer fully grounded in context
- answer_relevance  1=answer ignores the question, 5=answer directly and completely addresses it
- context_relevance 1=chunks are irrelevant to the question, 5=chunks are highly relevant

---
QUESTION:
{question}

RETRIEVED CONTEXT:
{context}

ANSWER:
{answer}
"""


def _load_chunks(chunks_dir: str) -> Dict[str, str]:
    """Build chunk_id -> text lookup from all JSONL files in chunks_dir."""
    mapping: Dict[str, str] = {}
    for path in sorted(Path(chunks_dir).glob("*.jsonl")):
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                row = json.loads(line)
                mapping[row["chunk_id"]] = row.get("text", "")
    return mapping


def _read_jsonl(path: str) -> List[Dict[str, Any]]:
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _write_jsonl(path: str, rows: List[Dict[str, Any]]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _call_ollama(prompt: str, retries: int = 2) -> Optional[str]:
    for attempt in range(retries + 1):
        try:
            resp = requests.post(
                f"{OLLAMA_URL}/api/generate",
                json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
                timeout=120,
            )
            resp.raise_for_status()
            return resp.json().get("response", "").strip()
        except Exception as e:
            if attempt == retries:
                return None
            time.sleep(2)
    return None


def _extract_json(text: str) -> Optional[Dict[str, Any]]:
    """Extract the first JSON object from the model's response."""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group())
    except json.JSONDecodeError:
        return None


def judge_result(
    question: str,
    answer: str,
    sources: List[Dict[str, Any]],
    chunk_map: Dict[str, str],
) -> Dict[str, Any]:
    context_parts = []
    for src in sources:
        cid = src.get("chunk_id", "")
        text = chunk_map.get(cid, "")
        if text:
            context_parts.append(f"[Page {src.get('page', '?')}] {text}")

    if not context_parts:
        return {"error": "no context chunks found"}

    context = "\n\n".join(context_parts[:5])  # cap at 5 chunks to stay within token limit
    prompt = _JUDGE_PROMPT.format(question=question, context=context, answer=answer)

    raw = _call_ollama(prompt)
    if raw is None:
        return {"error": "ollama unavailable"}

    parsed = _extract_json(raw)
    if parsed is None:
        return {"error": "failed to parse JSON", "raw": raw[:300]}

    return parsed


def main() -> None:
    parser = argparse.ArgumentParser(description="LLM-as-judge RAG evaluator (Ollama)")
    parser.add_argument("--results", default="data/eval_results.jsonl", help="Eval results JSONL")
    parser.add_argument("--chunks",  default="data/chunks",             help="Chunks directory")
    parser.add_argument("--out",     default="data/eval_judge_results.jsonl", help="Output JSONL")
    args = parser.parse_args()

    print(f"Loading chunks from {args.chunks} ...")
    chunk_map = _load_chunks(args.chunks)
    print(f"  {len(chunk_map)} chunks loaded.")

    results = _read_jsonl(args.results)
    print(f"Evaluating {len(results)} questions with model '{OLLAMA_MODEL}' ...\n")

    output = []
    scores = {"faithfulness": [], "answer_relevance": [], "context_relevance": []}

    for i, row in enumerate(results, start=1):
        qid      = row.get("id", f"q{i}")
        question = row.get("question", "")
        answer   = row.get("answer", "")
        sources  = row.get("sources", [])

        if not answer or "error" in row:
            print(f"[{i}/{len(results)}] {qid} — skipped (no answer)")
            output.append({**row, "judge": {"error": "no answer"}})
            continue

        judge = judge_result(question, answer, sources, chunk_map)

        for metric in scores:
            val = judge.get(metric)
            if isinstance(val, (int, float)):
                scores[metric].append(val)

        output.append({**row, "judge": judge})

        faith = judge.get("faithfulness", "?")
        relevance = judge.get("answer_relevance", "?")
        ctx = judge.get("context_relevance", "?")
        print(f"[{i}/{len(results)}] {qid}  faith={faith}  ans_rel={relevance}  ctx_rel={ctx}")

    _write_jsonl(args.out, output)

    print(f"\n{'='*50}")
    print("SUMMARY")
    print(f"{'='*50}")
    for metric, vals in scores.items():
        if vals:
            avg = sum(vals) / len(vals)
            print(f"  {metric:<22}: {avg:.2f} / 5.0  (n={len(vals)})")
    print(f"\nFull results written to: {args.out}")


if __name__ == "__main__":
    main()
