"""
RPC timing test for block fetching (no DB writes).

Tests sequential vs concurrent RPC calls for:
- get_block(block_number, include_author=True)
- get_events(block_hash)
- get_block_runtime_version(parent_hash)

Default URL targets local HTTP RPC.
"""

import argparse
import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from statistics import mean
from timeit import default_timer as timer
from urllib.request import Request, urlopen

from substrateinterface import SubstrateInterface


_tls = threading.local()
_substrate_instances = []
_substrate_lock = threading.Lock()


def _get_substrate(url: str) -> SubstrateInterface:
    substrate = getattr(_tls, "substrate", None)
    current_url = getattr(_tls, "url", None)
    if substrate is None or current_url != url:
        substrate = SubstrateInterface(
            url=url, ss58_format=0, type_registry_preset="polkadot"
        )
        _tls.substrate = substrate
        _tls.url = url
        with _substrate_lock:
            _substrate_instances.append(substrate)
    return substrate


def _close_all_substrates():
    with _substrate_lock:
        for substrate in _substrate_instances:
            try:
                substrate.close()
            except Exception:
                pass


def fetch_block_bundle(block_number: int, url: str, substrate=None):
    """Fetch block, events, and runtime version for a block number."""
    t0 = timer()
    if substrate is None:
        substrate = _get_substrate(url)
    t1 = timer()
    block = substrate.get_block(block_number=block_number, include_author=True)
    t2 = timer()
    block_hash = block["header"]["hash"]
    parent_hash = block["header"]["parentHash"]
    events = substrate.get_events(block_hash=block_hash)
    t3 = timer()
    runtime_version = substrate.get_block_runtime_version(parent_hash)
    t4 = timer()

    return {
        "block_number": block_number,
        "block_hash": block_hash,
        "parent_hash": parent_hash,
        "connect_s": t1 - t0,
        "get_block_s": t2 - t1,
        "get_events_s": t3 - t2,
        "get_runtime_version_s": t4 - t3,
        "total_s": t4 - t0,
        "events_count": len(events),
        "spec_version": (
            runtime_version.get("specVersion")
            if isinstance(runtime_version, dict)
            else None
        ),
    }


def run_sequential(url: str, start_block: int, count: int):
    results = []
    substrate = _get_substrate(url)
    for block_number in range(start_block, start_block + count):
        results.append(fetch_block_bundle(block_number, url, substrate=substrate))
    return results


def run_concurrent(url: str, start_block: int, count: int, workers: int):
    results = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(fetch_block_bundle, block_number, url): block_number
            for block_number in range(start_block, start_block + count)
        }
        for future in as_completed(futures):
            results.append(future.result())
    return results


def summarize(label: str, results):
    totals = [r["total_s"] for r in results]
    blocks = [r["block_number"] for r in results]
    print(f"\n{label}")
    print(f"Blocks: {min(blocks)}..{max(blocks)} (n={len(results)})")
    print(f"Total time: {sum(totals):.3f}s")
    print(f"Avg/block: {mean(totals):.3f}s")


def _rpc_batch(url: str, payloads):
    data = json.dumps(payloads).encode("utf-8")
    req = Request(url, data=data, headers={"Content-Type": "application/json"})
    with urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def run_batch_blocks(url: str, start_block: int, count: int, batch_size: int):
    results = []
    block_numbers = list(range(start_block, start_block + count))
    for i in range(0, len(block_numbers), batch_size):
        chunk = block_numbers[i : i + batch_size]
        t0 = timer()
        hash_payloads = [
            {
                "jsonrpc": "2.0",
                "id": f"h{bn}",
                "method": "chain_getBlockHash",
                "params": [bn],
            }
            for bn in chunk
        ]
        hash_resp = _rpc_batch(url, hash_payloads)
        t1 = timer()

        hash_map = {item["id"]: item.get("result") for item in hash_resp}
        block_payloads = [
            {
                "jsonrpc": "2.0",
                "id": f"b{bn}",
                "method": "chain_getBlock",
                "params": [hash_map.get(f"h{bn}")],
            }
            for bn in chunk
        ]
        block_resp = _rpc_batch(url, block_payloads)
        t2 = timer()

        block_map = {item["id"]: item.get("result") for item in block_resp}
        for bn in chunk:
            block = block_map.get(f"b{bn}") or {}
            header = (block.get("block") or {}).get("header") or {}
            results.append(
                {
                    "block_number": bn,
                    "block_hash": hash_map.get(f"h{bn}"),
                    "parent_hash": header.get("parentHash"),
                    "number_hex": header.get("number"),
                    "connect_s": 0.0,
                    "get_block_s": t2 - t1,
                    "get_events_s": 0.0,
                    "get_runtime_version_s": 0.0,
                    "total_s": t2 - t0,
                    "events_count": 0,
                    "spec_version": None,
                    "block_found": bool(block),
                }
            )
    return results


def _to_int(value):
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value, 16) if value.startswith("0x") else int(value)
        except ValueError:
            return None
    return None


def compare_sequential_vs_batch(seq_results, batch_results):
    seq_map = {r["block_number"]: r for r in seq_results}
    batch_map = {r["block_number"]: r for r in batch_results}
    mismatches = []

    for bn, seq in seq_map.items():
        batch = batch_map.get(bn)
        if not batch:
            mismatches.append((bn, "missing_in_batch"))
            continue

        seq_number = _to_int(seq.get("block_number"))
        batch_number = _to_int(batch.get("number_hex"))
        if seq_number != batch_number:
            mismatches.append((bn, "number"))

        if seq.get("block_hash") != batch.get("block_hash"):
            mismatches.append((bn, "block_hash"))

        if seq.get("parent_hash") != batch.get("parent_hash"):
            mismatches.append((bn, "parent_hash"))

    if not mismatches:
        print("\nData check: OK (Sequential vs Batch JSON-RPC)\n")
        return True

    print("\nData check: MISMATCHES FOUND")
    for bn, field in mismatches:
        print(f"- Block {bn}: {field}")
    print()
    return False


def parse_args():
    parser = argparse.ArgumentParser(
        description="RPC timing test (sequential vs concurrent)"
    )
    parser.add_argument("--url", default="http://127.0.0.1:9933", help="RPC URL")
    parser.add_argument(
        "--start", type=int, default=26802468, help="Start block number"
    )
    parser.add_argument("--count", type=int, default=10, help="Number of blocks")
    parser.add_argument(
        "--workers", type=int, default=5, help="Worker threads for concurrent test"
    )
    parser.add_argument(
        "--batch-size", type=int, default=10, help="Batch size for JSON-RPC batch"
    )
    parser.add_argument(
        "--mode",
        choices=["sequential", "concurrent", "batch", "verify", "all"],
        default="verify",
        help="Which test mode to run",
    )
    parser.add_argument("--rounds", type=int, default=1, help="Number of test rounds")
    parser.add_argument("--warmup", type=int, default=0, help="Warmup rounds")
    return parser.parse_args()


def main():
    args = parse_args()

    for _ in range(args.warmup):
        run_sequential(args.url, args.start, args.count)
        run_concurrent(args.url, args.start, args.count, args.workers)

    for i in range(args.rounds):
        print(f"\nRound {i + 1}/{args.rounds}")
        if args.mode in ("sequential", "verify", "all"):
            seq_results = run_sequential(args.url, args.start, args.count)
            summarize("Sequential", seq_results)

        if args.mode in ("concurrent", "all"):
            conc_results = run_concurrent(
                args.url, args.start, args.count, args.workers
            )
            summarize(f"Concurrent (workers={args.workers})", conc_results)

        if args.mode in ("batch", "verify", "all"):
            batch_results = run_batch_blocks(
                args.url, args.start, args.count, args.batch_size
            )
            summarize(f"Batch JSON-RPC (batch_size={args.batch_size})", batch_results)

        if args.mode == "verify":
            compare_sequential_vs_batch(seq_results, batch_results)

    _close_all_substrates()


if __name__ == "__main__":
    main()
