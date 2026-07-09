from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, scoped_session
from substrateinterface import SubstrateInterface, Keypair

def main():
    # Database Connection
    DB_CONNECTION = "mysql+mysqlconnector://crilab_db_admin:CRI%40admin24%21@10.70.43.249:3306/polkadot_analysis"
    engine = create_engine(DB_CONNECTION, echo=False, isolation_level="READ_UNCOMMITTED", pool_pre_ping=True)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    db_session = scoped_session(session_factory)

    # Step 2: Run query
    query = """
    SELECT extrinsic.from_address, proxy_extrinsic_real_address.real_address
    FROM polkadot_analysis.extrinsic
    JOIN polkadot_analysis.proxy_extrinsic_real_address ON 
        extrinsic.block_id = proxy_extrinsic_real_address.block_id
        AND extrinsic.extrinsic_idx = proxy_extrinsic_real_address.extrinsic_idx
        AND extrinsic.nesting_idx = proxy_extrinsic_real_address.nesting_idx
        AND extrinsic.batch_idx = proxy_extrinsic_real_address.batch_idx
        AND extrinsic.unique_sequence = proxy_extrinsic_real_address.unique_sequence
    WHERE
        extrinsic.module_id = "multisig"
        AND extrinsic.call_id = "as_multi"
        AND extrinsic.from_address IN 
        (
            SELECT DISTINCT proxy_account.proxied_account_address as address FROM polkadot_analysis.multisig_member_account 
                JOIN polkadot_analysis.proxy_account 
                    ON multisig_member_account.address = proxy_account.proxied_account_address
                GROUP BY address
        )
    GROUP BY extrinsic.from_address, proxy_extrinsic_real_address.real_address
    """

    results = db_session.execute(text(query)).fetchall()

    # Step 3: Store results as a dict
    address_dict = {row['from_address']: row['real_address'] for row in results}
    print("Member to real_address mapping", address_dict)


    # Step 4: Get all unique multisig_account_address that have proxy addresses
    address_dict_keys_string = '(' + ', '.join([f'"{key}"' for key in address_dict.keys()]) + ')'
    multisig_query = f"""
    SELECT DISTINCT multisig_account_address 
    FROM polkadot_analysis.multisig_member_account 
    WHERE address IN {address_dict_keys_string}
    """
    multisig_addresses = db_session.execute(text(multisig_query)).fetchall()
    print("Multisig Addresses: ", multisig_addresses)

    # Step 5: Fetch threshold for each multisig_account_address
    multisig_addresses_string = '(' + ', '.join([f'"{row["multisig_account_address"]}"' for row in multisig_addresses]) + ')'
    threshold_query = f"""
    SELECT address, threshold 
    FROM polkadot_analysis.multisig_account 
    WHERE address IN {multisig_addresses_string}
    """
    thresholds = db_session.execute(text(threshold_query)).fetchall()
    print("Thresholds: ", thresholds)

    # Step 6: Create a dict of member accounts
    member_accounts_query = f"""
    SELECT multisig_account.address as multisig_account_address, multisig_member_account.address as member_account_address 
    FROM polkadot_analysis.multisig_account 
    JOIN polkadot_analysis.multisig_member_account 
    ON multisig_account.address = multisig_member_account.multisig_account_address
    WHERE multisig_account.address IN {multisig_addresses_string}
    """
    member_accounts = db_session.execute(text(member_accounts_query)).fetchall()
    print("Member Accounts: ", member_accounts)

    multisig_members_dict = {}
    for row in member_accounts:
        if row['multisig_account_address'] not in multisig_members_dict:
            multisig_members_dict[row['multisig_account_address']] = []
        multisig_members_dict[row['multisig_account_address']].append(row['member_account_address'])

    print("Multisig Members Dict: ", multisig_members_dict)
    # Step 7: Update the member account address in the first dict
    for multisig_account, members in multisig_members_dict.items():
        for i, member in enumerate(members):
            if member in address_dict:
                members[i] = address_dict[member]

    # Step 8: Create new multisig account address and print results
    for multisig_account, members in multisig_members_dict.items():
        threshold = next((row['threshold'] for row in thresholds if row['address'] == multisig_account), None)
        assert threshold is not None, f"Threshold not found for multisig account: {multisig_account}"
        new_multisig_address = generate_multisig(members, threshold)
        print(members)
        print(threshold)
        print(f"Old multisig account: {multisig_account}, New multisig account: {new_multisig_address}")
        for member in members:
            if address_dict.get(member, 'N/A') != 'N/A':
                import pdb; pdb.set_trace()
        #     print(f"Real address: {address_dict.get(member, 'N/A')}, Old multisig member address: {member}")
        

def generate_multisig(addresses, threshold):
    # Connect to a Polkadot node
    substrate = SubstrateInterface(
        url="wss://rpc.polkadot.io",
        type_registry_preset='polkadot'
    )

    # Generate multisig address
    multisig_address = substrate.generate_multisig_account(
        signatories=addresses,
        threshold=threshold
    )

    return multisig_address

if __name__ == "__main__":
    main()