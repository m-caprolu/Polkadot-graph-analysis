# Run the following command to execute the migration on the database:
"""
    CREATE TABLE IF NOT EXISTS `polkadot_analysis`.`proxy_extrinsic_real_address` (
    `block_id` INT NOT NULL,
    `extrinsic_idx` INT NOT NULL,
    `nesting_idx` INT NOT NULL DEFAULT 0,
    `batch_idx` INT NOT NULL DEFAULT 0,
    `real_address` VARCHAR(64) NOT NULL,
    PRIMARY KEY (`block_id`, `extrinsic_idx`, `nesting_idx`, `batch_idx`),
    FOREIGN KEY (`block_id`, `extrinsic_idx`, `nesting_idx`, `batch_idx`)
    REFERENCES `extrinsic`(`block_id`, `extrinsic_idx`, `nesting_idx`, `batch_idx`)
    ON DELETE CASCADE
    ON UPDATE CASCADE
    )
    ENGINE = InnoDB
    DEFAULT CHARACTER SET = utf8mb4
    COLLATE = utf8mb4_0900_ai_ci;
"""

""" Code to be added in the main function
    block_ids = []
    file_path = './migrations/migration_3_add_proxy_real_addresses/proxy_extrinsics.csv'
    with open(file_path, mode='r') as file:
        csv_reader = csv.reader(file)
        block_ids = [int(row[0]) for row in csv_reader]

    Block.query(db_session).filter(Block.id.in_(block_ids)).delete()
    Transaction.query(db_session).filter(Transaction.block_id.in_(block_ids)).delete()
    Event.query(db_session).filter(Event.block_id.in_(block_ids)).delete()
    db_session.commit()

    print("Done deleting blocks...")
    for block_id in block_ids:
        try:
            process_block(block_id)
            print("Block {} processed successfully".format(block_id))
        except BlockAlreadyAdded:
            print("Block Already Added, Skipping Block...")
        except Exception as err:
            # clear the db session
            db_session.rollback()
            create_error_log(block_id, traceback.format_exc())
            logger.error(traceback.format_exc())
            
"""