import argparse
import json
import time
from typing import Any, Dict, List

from app.pipeline import answer_query


def answer_question(question: str, top_k: int = 5) -> Dict[str, Any]:
    """
    Adapter for batch runner. Reuses the same query path as the chat app.
    """
    resp = answer_query(question, k=top_k)
    return {
        "answer": resp.get("answer", ""),
        "sources": resp.get("sources", []),
        "retrieved": resp.get("sources", []),
    }


def read_jsonl(path: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON on line {line_num} in {path}: {e}")
    return rows


def write_jsonl(path: str, rows: List[Dict[str, Any]]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Minimal batch query runner")
    parser.add_argument("--in", dest="in_path", required=True, help="Input JSONL file")
    parser.add_argument("--out", dest="out_path", required=True, help="Output JSONL file")
    parser.add_argument("--top-k", dest="top_k", type=int, default=5, help="Top-k retrieval")
    args = parser.parse_args()

    items = read_jsonl(args.in_path)
    results: List[Dict[str, Any]] = []

    for i, item in enumerate(items, start=1):
        q = item.get("question")
        qid = item.get("id", f"q{i}")
        if not isinstance(q, str) or not q.strip():
            results.append(
                {
                    "id": qid,
                    "question": q,
                    "error": "Missing/invalid 'question' field",
                }
            )
            continue

        start = time.time()
        try:
            resp = answer_question(q.strip(), top_k=args.top_k)
            latency_ms = int((time.time() - start) * 1000)

            results.append(
                {
                    "id": qid,
                    "question": q.strip(),
                    "answer": resp.get("answer", ""),
                    "sources": resp.get("sources", []),
                    "retrieved": resp.get("retrieved", []),  # optional
                    "latency_ms": latency_ms,
                }
            )
        except Exception as e:
            latency_ms = int((time.time() - start) * 1000)
            results.append(
                {
                    "id": qid,
                    "question": q.strip(),
                    "error": str(e),
                    "latency_ms": latency_ms,
                }
            )

        print(f"[{i}/{len(items)}] {qid} done")

    write_jsonl(args.out_path, results)
    print(f"\nWrote {len(results)} results to {args.out_path}")


if __name__ == "__main__":
    main()
