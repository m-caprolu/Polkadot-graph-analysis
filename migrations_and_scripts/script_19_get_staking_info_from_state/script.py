"""
Polkadot full-history staking extractor.

Walks every era from 1 to the latest fully-imported active era, queries the
staking snapshot for each, and writes one JSON file per era to OUTPUT_DIR.
"""

import json
import sys
import signal
from pathlib import Path
from substrateinterface import SubstrateInterface
from tqdm import tqdm

NODE_URL = "ws://localhost:9944"
OUTPUT_DIR = Path("era_staking")
HISTORY_DEPTH = 84
BLOCKS_PER_ERA = 14_400
ERA_OFFSET_FOR_QUERY = 2
START_ERA = 1688

# Era 1 on Polkadot began around block ~900,000 (staking activated mid-June 2020).
# Probing earlier blocks is wasteful and can hang on pre-staking runtimes.
EARLIEST_STAKING_BLOCK = 500_000


def log(msg):
    print(msg, flush=True)


# ---------- helpers ----------


def get_active_era_at_block(substrate, block_number, verbose=False):
    """Return ActiveEra index at a given block number, or None."""
    try:
        if verbose:
            log(f"    rpc: get_block_hash({block_number})")
        bh = substrate.get_block_hash(block_number)
        if verbose:
            log(f"    rpc: query ActiveEra @ {bh[:14]}...")
        ae = substrate.query("Staking", "ActiveEra", block_hash=bh)
        return ae.value["index"] if ae.value else None
    except Exception as e:
        if verbose:
            log(f"    rpc: ERROR {type(e).__name__}: {e}")
        return None


def find_era_start_block(substrate, target_era, lo, hi, verbose=False):
    """Binary-search lowest block where ActiveEra >= target_era."""
    iteration = 0
    while lo < hi:
        mid = (lo + hi) // 2
        iteration += 1
        era = get_active_era_at_block(substrate, mid, verbose=verbose)
        if verbose:
            log(
                f"  iter {iteration}: block {mid} -> ActiveEra={era} "
                f"(searching for {target_era}, lo={lo}, hi={hi})"
            )
        if era is None or era < target_era:
            lo = mid + 1
        else:
            hi = mid
    return lo


def query_era(substrate, era, block_hash):
    total_stake = substrate.query(
        "Staking", "ErasTotalStake", [era], block_hash=block_hash
    )
    total_reward = substrate.query(
        "Staking", "ErasValidatorReward", [era], block_hash=block_hash
    )
    reward_pts = substrate.query(
        "Staking", "ErasRewardPoints", [era], block_hash=block_hash
    )

    if total_stake.value in (None, 0):
        return None

    exposures = substrate.query_map(
        module="Staking",
        storage_function="ErasStakers",
        params=[era],
        block_hash=block_hash,
        page_size=1000,
    )

    individual_points = dict(
        reward_pts.value.get("individual", []) if reward_pts.value else []
    )
    era_total_pts = (reward_pts.value["total"] if reward_pts.value else 0) or 1
    era_total_reward = total_reward.value or 0

    validators = []
    for validator_id, exposure in exposures:
        v = validator_id.value
        e = exposure.value
        prefs = substrate.query(
            "Staking", "ErasValidatorPrefs", [era, v], block_hash=block_hash
        )
        v_points = individual_points.get(v, 0)

        v_reward_total = era_total_reward * v_points / era_total_pts
        commission_frac = prefs.value["commission"] / 1_000_000_000
        v_commission = v_reward_total * commission_frac
        pool = v_reward_total - v_commission
        total_backing = e["total"] or 1

        validator_reward = v_commission + pool * e["own"] / total_backing
        nominator_rewards = [
            {
                "who": n["who"],
                "stake": n["value"],
                "reward": pool * n["value"] / total_backing,
            }
            for n in e["others"]
        ]

        validators.append(
            {
                "validator": v,
                "own_stake": e["own"],
                "total_stake": e["total"],
                "commission_perbill": prefs.value["commission"],
                "points": v_points,
                "validator_reward": validator_reward,
                "nominators": nominator_rewards,
            }
        )

    return {
        "era": era,
        "queried_at_block_hash": block_hash,
        "era_total_stake": total_stake.value,
        "era_total_reward": total_reward.value,
        "era_total_points": reward_pts.value["total"],
        "num_validators": len(validators),
        "validators": validators,
    }


# ---------- main ----------


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    log(f"Connecting to {NODE_URL} ...")
    substrate = SubstrateInterface(url=NODE_URL)

    health = substrate.rpc_request("system_health", []).get("result", {})
    log(f"Node health: {health}")

    # ----- locate anchor block -----
    log("Locating a recent block with valid staking state ...")
    finalized_hash = substrate.rpc_request("chain_getFinalizedHead", []).get("result")
    finalized_header = substrate.rpc_request("chain_getHeader", [finalized_hash]).get(
        "result"
    )
    finalized_number = int(finalized_header["number"], 16)
    log(f"  Finalized head: block {finalized_number}")

    current_era = None
    anchor_block = finalized_number

    log(f"  Probing block {finalized_number} ...")
    idx = get_active_era_at_block(substrate, finalized_number)
    log(f"    -> ActiveEra = {idx}")

    if idx is not None:
        current_era = idx
    else:
        log("  Finalized head has no resolved state; walking backward ...")
        for step_back in range(50_000, 5_000_000, 50_000):
            probe_block = finalized_number - step_back
            if probe_block < 1:
                break
            log(f"  Probing block {probe_block} ...")
            idx = get_active_era_at_block(substrate, probe_block)
            log(f"    -> ActiveEra = {idx}")
            if idx is not None:
                current_era = idx
                anchor_block = probe_block
                break

    if current_era is None:
        raise RuntimeError("Could not find any block with a valid ActiveEra.")

    log(f"  Anchored at block {anchor_block}, active era {current_era}")

    max_era = current_era - 1
    if START_ERA < 1:
        raise ValueError("START_ERA must be >= 1")
    if START_ERA > max_era:
        raise ValueError(f"START_ERA ({START_ERA}) exceeds max era ({max_era}).")

    log(
        f"Will extract eras {START_ERA} .. {max_era} "
        f"({max_era - START_ERA + 1} eras total)\n"
    )

    # ----- locate start block for START_ERA (anchor-based estimate + bounded search) -----
    log(f"Locating era {START_ERA} start block ...")
    search_floor = 1 if START_ERA == 1 else EARLIEST_STAKING_BLOCK
    approx_start = anchor_block - (current_era - START_ERA) * BLOCKS_PER_ERA
    approx_start = max(search_floor, approx_start)

    window = 3 * BLOCKS_PER_ERA
    lo = max(search_floor, approx_start - window)
    hi = min(anchor_block, approx_start + window)

    log(f"  Estimating era {START_ERA} near block {approx_start} ...")

    # Expand forward until we see ActiveEra >= START_ERA at hi.
    while True:
        log(f"  Probing upper bound block {hi} ...")
        hi_era = get_active_era_at_block(substrate, hi, verbose=True)
        log(f"    -> ActiveEra = {hi_era}")
        if hi_era is not None and hi_era >= START_ERA:
            break
        if hi >= anchor_block:
            raise RuntimeError(
                f"Could not find ActiveEra >= {START_ERA} up to anchor block."
            )
        lo = hi + 1
        hi = min(anchor_block, hi + window)

    # Expand backward until we see ActiveEra < START_ERA at lo (or hit earliest).
    while lo > search_floor:
        log(f"  Probing lower bound block {lo} ...")
        lo_era = get_active_era_at_block(substrate, lo, verbose=True)
        log(f"    -> ActiveEra = {lo_era}")
        if lo_era is None or lo_era < START_ERA:
            break
        hi = lo
        lo = max(search_floor, lo - window)

    log(f"  Era {START_ERA} is between blocks {lo} and {hi}. Binary-searching ...")
    start_era_block = find_era_start_block(
        substrate, START_ERA, lo=lo, hi=hi, verbose=True
    )
    log(f"  Era {START_ERA} starts at block ~{start_era_block}\n")

    # ----- iterate eras -----
    eras_to_process = list(range(START_ERA, max_era + 1))
    skipped = 0
    failed = []
    pbar = tqdm(eras_to_process, desc="Eras", unit="era", dynamic_ncols=True)
    last_known_block = start_era_block

    for era in pbar:
        out_path = OUTPUT_DIR / f"era_{era:05d}.json"
        if out_path.exists():
            skipped += 1
            pbar.set_postfix(skipped=skipped, failed=len(failed))
            continue

        target_active_era = min(era + ERA_OFFSET_FOR_QUERY, current_era)
        guess = last_known_block + (target_active_era - 1) * BLOCKS_PER_ERA
        guess = min(guess, anchor_block)
        lo = last_known_block
        hi = min(guess + 2 * BLOCKS_PER_ERA, anchor_block)
        query_block = find_era_start_block(substrate, target_active_era, lo, hi)

        if query_block > anchor_block:
            failed.append((era, "query block past anchor"))
            pbar.set_postfix(skipped=skipped, failed=len(failed))
            continue

        try:
            bh = substrate.get_block_hash(query_block)
            snapshot = query_era(substrate, era, bh)
            if snapshot is None:
                failed.append((era, "empty snapshot — outside HistoryDepth"))
            else:
                snapshot["queried_at_block"] = query_block
                with open(out_path, "w") as f:
                    json.dump(snapshot, f, default=str)
                last_known_block = query_block
        except Exception as e:
            failed.append((era, repr(e)))

        pbar.set_postfix(skipped=skipped, failed=len(failed))

    pbar.close()

    log(
        f"\nDone. {len(eras_to_process)} eras targeted, "
        f"{skipped} already on disk, {len(failed)} failed."
    )
    if failed:
        with open(OUTPUT_DIR / "_failures.json", "w") as f:
            json.dump(failed, f, indent=2)
        log(f"Failure list saved to {OUTPUT_DIR / '_failures.json'}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("\nInterrupted. Progress is saved per-era; re-run to resume.")
        sys.exit(1)
