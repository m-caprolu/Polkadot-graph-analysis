from substrateinterface import SubstrateInterface

# Connect to the local Polkadot node (HTTP or WS endpoint)
substrate = SubstrateInterface(
    url="http://10.76.170.108:9933", 
    type_registry_preset='polkadot'
)
print(f"Connected to chain: {substrate.chain} (SS58 prefix {substrate.ss58_format})")

era_validators_info = {}

# Get current active era index
active_era_info = substrate.query('Staking', 'ActiveEra').value
if not active_era_info:
    raise Exception("Could not retrieve ActiveEra from node")
current_era_index = active_era_info['index']
# We will iterate through all *completed* eras (0 up to current_era_index - 1)
if current_era_index is None or current_era_index == 0:
    print("No completed eras to process.")
else:
    # Get history depth (number of past eras kept in state)
    history_depth = substrate.query('Staking', 'HistoryDepth').value
    if history_depth is None:
        history_depth = 84  # default value if not found, typically 84 on Polkadot&#8203;:contentReference[oaicite:4]{index=4}

    # Estimate blocks per era (approximately 14400 blocks per era on Polkadot ~24h)
    era_block_estimate = 14400  
    # Get current block number (for safety in block hash queries)
    latest_block = substrate.get_block_header()['number']

    for era in range(0, int(current_era_index)):
        era = int(era)
        # Determine if era data is in current state or pruned
        use_block_hash = None
        # If era is older than the earliest kept era, we need a historical block
        # The staking pallet stores last `history_depth` eras. If era < currentEra - history_depth, it's pruned&#8203;:contentReference[oaicite:5]{index=5}.
        if history_depth and era < max(0, int(current_era_index) - int(history_depth)):
            # Choose a block at the end of era + history_depth - 1 (just before pruning of this era would occur)
            target_era_for_block = era + int(history_depth) - 1
            if target_era_for_block >= current_era_index:
                target_era_for_block = int(current_era_index) - 1
            # Estimate a block near the end of target_era_for_block
            block_est = (target_era_for_block + 1) * era_block_estimate - 1
            if block_est > latest_block:
                block_est = latest_block
            try:
                use_block_hash = substrate.get_block_hash(block_est)
            except Exception as e:
                # Fallback: if block hash lookup failed, use latest block hash as fallback
                use_block_hash = substrate.get_block_hash(latest_block)
        # Query era reward (total payout for that era)&#8203;:contentReference[oaicite:6]{index=6}
        try:
            era_reward_obj = substrate.query('Staking', 'ErasValidatorReward', [era], block_hash=use_block_hash)
        except Exception as e:
            print(f"Warning: Skipping era {era} due to query error: {e}")
            continue
        era_reward = era_reward_obj.value
        if era_reward is None:
            # No reward recorded (era might not exist or was removed)
            continue

        # Query era reward points (to get total points and each validator's points)&#8203;:contentReference[oaicite:7]{index=7}
        era_points_obj = substrate.query('Staking', 'ErasRewardPoints', [era], block_hash=use_block_hash)
        era_points = era_points_obj.value  # should be a dict like {"total": ..., "individual": {...}}
        total_points = era_points.get('total') if era_points else None

        # Query all validators' exposures (stake distribution) for this era
        try:
            era_exposures = substrate.query_map('Staking', 'ErasStakers', params=[era], block_hash=use_block_hash)
        except Exception as e:
            print(f"Warning: Could not fetch exposures for era {era}: {e}")
            continue

        # Query all validators' prefs (commission) for this era
        try:
            era_prefs = substrate.query_map('Staking', 'ErasValidatorPrefs', params=[era], block_hash=use_block_hash)
        except Exception as e:
            print(f"Warning: Could not fetch prefs for era {era}: {e}")
            era_prefs = []  # continue with empty prefs if error

        # Convert prefs list to a dict for quick lookup
        prefs_dict = {}
        for val_key, prefs in era_prefs:
            acct_bytes = val_key.value  # AccountId bytes
            # Decode commission; prefs.value might be a dict with 'commission'
            if prefs.value is None:
                continue
            commission = 0
            # Polkadot commission is typically in per-billion (parts per 1e9)
            if isinstance(prefs.value, dict) and 'commission' in prefs.value:
                commission = int(prefs.value['commission'])
            else:
                # If prefs is given as a single number (old format), use it
                commission = int(prefs.value)
            prefs_dict[acct_bytes] = commission

        # Initialize this era's entry in result dict
        era_validators_info[era] = {}

        # Iterate over all validator exposures for this era
        for val_key, exposure in era_exposures:
            validator_account = val_key.value  # AccountId (bytes)
            exp = exposure.value  # exposure data (dict with 'own', 'total', 'others')
            if exp is None:
                continue  # skip if no exposure data
            total_stake = int(exp.get('total', 0))
            own_stake = int(exp.get('own', 0))
            others = exp.get('others', []) or []  # list of nominators {who, value}

            # Find the validator's era points (default 0 if missing)
            validator_points = 0
            if era_points and 'individual' in era_points:
                # keys in 'individual' may be bytes as well; match by bytes
                ind_points = era_points['individual']
                # The keys in ind_points might already be decoded to SS58 or hex. We try matching bytes or decoded forms
                # substrateinterface might decode AccountId keys in BTreeMap as SS58 string (if it knows prefix).
                # To cover both, compare by encoded ss58.
                for acct_id, pts in ind_points.items():
                    # acct_id could be already a str address or bytes
                    if isinstance(acct_id, bytes):
                        if acct_id == validator_account:
                            validator_points = int(pts)
                            break
                    else:
                        # if it's not bytes, assume it's an SS58 address string
                        try:
                            decoded = substrate.ss58_decode(acct_id)
                        except Exception:
                            decoded = None
                        if decoded == validator_account:
                            validator_points = int(pts)
                            break
            # If total_points is zero (should not happen unless no validators), avoid division
            if not total_points or total_points == 0:
                group_reward = 0
            else:
                # Calculate this validator's portion of era reward based on points
                group_reward = int(int(era_reward) * validator_points // int(total_points))
            # Commission fraction (per billion) for this validator
            commission = prefs_dict.get(validator_account, 0)
            # Validator's commission reward
            commission_reward = int(group_reward * commission // 1_000_000_000)  # assuming commission is Perbill (1e9 basis)
            # Remaining reward to be split among all stakers (including validator's own stake)
            rest_reward = group_reward - commission_reward

            # Compute rewards for validator and each nominator
            # Avoid division by zero if total_stake is 0 (shouldn't happen if validator had stake)
            validator_reward = commission_reward
            nominator_rewards = []
            if total_stake > 0:
                # Validator's own stake share of rest
                validator_reward += int(rest_reward * own_stake // total_stake)
                # Each nominator's share
                for nom in others:
                    nom_stash = nom.get('who')
                    nom_stake = int(nom.get('value', 0))
                    if nom_stake == 0 or nom_stash is None:
                        continue
                    nom_reward = int(rest_reward * nom_stake // total_stake)
                    # Convert nominator stash to SS58 address string
                    try:
                        nom_address = substrate.ss58_encode(nom_stash, substrate.ss58_format)
                    except Exception:
                        # If ss58 encoding fails, fall back to hex
                        nom_address = nom_stash.hex() if isinstance(nom_stash, bytes) else str(nom_stash)
                    nominator_rewards.append({'stash': nom_address, 'reward': nom_reward})
            # Convert validator stash AccountId to SS58 address string
            try:
                val_address = substrate.ss58_encode(validator_account, substrate.ss58_format)
            except Exception:
                val_address = validator_account.hex() if isinstance(validator_account, bytes) else str(validator_account)
            # Store results
            era_validators_info[era][val_address] = {
                'validator_reward': validator_reward,
                'nominators': nominator_rewards
            }

# Example: print result for a specific era (uncomment to debug)
# import json; print(json.dumps(era_validators_info.get(0, {}), indent=2))
