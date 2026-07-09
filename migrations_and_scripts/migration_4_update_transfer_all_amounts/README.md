## Migration Script 1
Amounts for transfer_all transactoins is not added in the extrinsic details. It should be fetched from the events emitted by this extrinsic.
- This is still not done automatically in the transactions fetcher. This handles already built database.

-----
## Migration Script 2
- This is a hard coded script. 
- I ignore blocks having nested transactions with ambigious events `balances.transfer` that can not tell whether original transaction is `balances.transfer_all` or something else.
- What I do: is get all transactions having `balances.transfer_all` and get their `block_id` and `extrinsic_idx` and get any other extrinsics in the same batch having `balances.(transfer, transfer_keep_alive, transfer_allow_death)` transaction, and ignore them.
- Until current block, only 22 transactions are ignored, having 51-31 only 20 events not handled. 
- Query used:
    ```
    SELECT DISTINCT(e2.block_id)
        FROM (
            SELECT DISTINCT block_id, extrinsic_idx
            FROM polkadot_analysis.extrinsic
            WHERE
                extrinsic.module_id = "Balances"
                AND extrinsic.call_id = "transfer_all"
                AND extrinsic.value = 0
        ) AS e1
        JOIN polkadot_analysis.extrinsic as e2
        ON e1.block_id = e2.block_id
        AND e1.extrinsic_idx = e2.extrinsic_idx
        WHERE e2.module_id = "Balances"
        AND e2.call_id IN ("transfer", "transfer_allow_death", "transfer_keep_alive")
    ```
- Then, all `balances.transfer` event in all other blocks are added immediately.