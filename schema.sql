CREATE USER 'root'@'127.0.0.1' IDENTIFIED BY 'root';
GRANT ALL PRIVILEGES ON *.* TO 'root'@'127.0.0.1' WITH GRANT OPTION;
FLUSH PRIVILEGES;
-- MySQL Workbench Forward Engineering

SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0;
SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0;
SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='ONLY_FULL_GROUP_BY,STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION';

-- -----------------------------------------------------
-- Schema mydb
-- -----------------------------------------------------
-- -----------------------------------------------------
-- Schema polkadot_analysis
-- -----------------------------------------------------

-- -----------------------------------------------------
-- Schema polkadot_analysis
-- -----------------------------------------------------
CREATE SCHEMA IF NOT EXISTS `polkadot_analysis` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci ;
USE `polkadot_analysis` ;

-- -----------------------------------------------------
-- Table `polkadot_analysis`.`account`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `polkadot_analysis`.`account` (
  `address` VARCHAR(64) NOT NULL,
  `pkey` VARCHAR(64) NULL DEFAULT NULL,
  `index_address` VARCHAR(24) NULL DEFAULT NULL,
  `is_reaped` TINYINT(1) NOT NULL DEFAULT 0,
  `is_proxy` TINYINT(1) NOT NULL DEFAULT 0,
  `proxied` TINYINT(1) NOT NULL DEFAULT 0,
  `is_multisig` TINYINT(1) NOT NULL DEFAULT 0,
  `is_validator` TINYINT(1) NOT NULL DEFAULT 0,
  `was_validator` TINYINT(1) NOT NULL DEFAULT 0,
  `is_nominator` TINYINT(1) NOT NULL DEFAULT 0,
  `was_nominator` TINYINT(1) NOT NULL DEFAULT 0,
  `is_council_member` TINYINT(1) NOT NULL DEFAULT 0,
  `was_council_member` TINYINT(1) NOT NULL DEFAULT 0,
  `is_tech_comm_member` TINYINT(1) NOT NULL DEFAULT 0,
  `was_tech_comm_member` TINYINT(1) NOT NULL DEFAULT 0,
  `is_registrar` TINYINT(1) NOT NULL DEFAULT 0,
  `was_registrar` TINYINT(1) NOT NULL DEFAULT 0,
  `is_sudo` TINYINT(1) NOT NULL DEFAULT 0,
  `was_sudo` TINYINT(1) NOT NULL DEFAULT 0,
  `is_treasury` TINYINT(1) NOT NULL DEFAULT 0,
  `count_reaped` INT NOT NULL DEFAULT 0,
  `balance_total` DECIMAL(65,10) NULL DEFAULT NULL,
  `balance_free` DECIMAL(65,10) NULL DEFAULT NULL,
  `balance_reserved` DECIMAL(65,10) NULL DEFAULT NULL,
  `nonce` INT NULL DEFAULT NULL,
  `has_identity` TINYINT(1) NOT NULL DEFAULT 0,
  `has_subidentity` TINYINT(1) NOT NULL DEFAULT 0,
  `identity_display` VARCHAR(32) NULL DEFAULT NULL,
  `identity_legal` VARCHAR(32) NULL DEFAULT NULL,
  `identity_web` VARCHAR(32) NULL DEFAULT NULL,
  `identity_riot` VARCHAR(32) NULL DEFAULT NULL,
  `identity_email` VARCHAR(32) NULL DEFAULT NULL,
  `identity_twitter` VARCHAR(32) NULL DEFAULT NULL,
  `identity_judgement_good` INT NOT NULL DEFAULT 0,
  `identity_judgement_bad` INT NOT NULL DEFAULT 0,
  `parent_identity` VARCHAR(64) NULL DEFAULT NULL,
  `subidentity_display` VARCHAR(32) NULL DEFAULT NULL,
  `created_at_block` INT NOT NULL,
  `updated_at_block` INT NOT NULL,
  PRIMARY KEY (`address`),
  INDEX `ix_account_address` (`address`),
  INDEX `ix_account_balance_free` (`balance_free`),
  INDEX `ix_account_balance_reserved` (`balance_reserved`),
  INDEX `ix_account_is_nominator` (`is_nominator`),
  INDEX `ix_account_is_validator` (`is_validator`),
  INDEX `ix_account_index_address` (`index_address`),
  INDEX `ix_account_pkey` (`pkey`)
)
ENGINE = InnoDB
DEFAULT CHARACTER SET = utf8mb4
COLLATE = utf8mb4_0900_ai_ci;


-- -----------------------------------------------------
-- Table `polkadot_analysis`.`proxy_account`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `polkadot_analysis`.`proxy_account` (
  `address` VARCHAR(64) NOT NULL,
  `proxied_account_address` VARCHAR(64) NOT NULL,
  `proxy_type` VARCHAR(64) NOT NULL,
  PRIMARY KEY (`address`, proxied_account_address)
)
ENGINE = InnoDB
DEFAULT CHARACTER SET = utf8mb4
COLLATE = utf8mb4_0900_ai_ci;

-- -----------------------------------------------------
-- Table `polkadot_analysis`.`account_history`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `polkadot_analysis`.`account_history` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `address` VARCHAR(66) NOT NULL,
  `balance_free` DECIMAL(65,10) NULL DEFAULT NULL,
  `balance_reserved` DECIMAL(65,10) NULL DEFAULT NULL,
  `is_reaped` TINYINT(1) NULL DEFAULT NULL,
  `is_validator` TINYINT(1) NULL DEFAULT NULL,
  `is_nominator` TINYINT(1) NULL DEFAULT NULL,
  `identity_display` JSON NULL DEFAULT NULL,
  `identity_judgement` JSON NULL DEFAULT NULL,
  `updated_at_block` INT NULL DEFAULT NULL,
  PRIMARY KEY (`id`, `address`),
  INDEX `ix_account_is_nominator` (`is_nominator` ASC) VISIBLE,
  INDEX `ix_account_is_validator` (`is_validator` ASC) VISIBLE,
  INDEX `ix_account_history_address` (`address` ASC) INVISIBLE,
  INDEX `ix_account_history_updated_at_block` (`updated_at_block` ASC) VISIBLE)
ENGINE = MyISAM
AUTO_INCREMENT = 2735
DEFAULT CHARACTER SET = utf8mb4
COLLATE = utf8mb4_0900_ai_ci;


-- -----------------------------------------------------
-- Table `polkadot_analysis`.`block`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `polkadot_analysis`.`block` (
  `id` INT NOT NULL,
  `parent_id` INT NOT NULL,
  `hash` VARCHAR(66) NOT NULL,
  `parent_hash` VARCHAR(66) NOT NULL,
  `state_root` VARCHAR(66) NOT NULL,
  `extrinsics_root` VARCHAR(66) NOT NULL,
  `author` VARCHAR(48) NULL DEFAULT NULL,
  `count_extrinsics` INT NOT NULL,
  `count_extrinsics_unsigned` INT NOT NULL,
  `count_extrinsics_signed` INT NOT NULL,
  `count_extrinsics_error` INT NOT NULL,
  `count_extrinsics_success` INT NOT NULL,
  `count_events` INT NOT NULL,
  `count_accounts_new` INT NOT NULL,
  `count_accounts_reaped` INT NOT NULL,
  `count_sessions_new` INT NOT NULL,
  `count_log` INT NOT NULL,
  `datetime` DATETIME NULL DEFAULT NULL,
  `timestamp` BIGINT NULL DEFAULT NULL,
  `logs` JSON NULL DEFAULT NULL,
  `authority_index` INT NULL DEFAULT NULL,
  `slot_number` DECIMAL(65,0) NULL DEFAULT NULL,
  `spec_version_id` VARCHAR(64) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE INDEX `ix_block_hash` (`hash` ASC) VISIBLE,
  INDEX `ix_block_parent_hash` (`parent_hash` ASC) VISIBLE)
ENGINE = InnoDB
DEFAULT CHARACTER SET = utf8mb4
COLLATE = utf8mb4_0900_ai_ci;


-- -----------------------------------------------------
-- Table `polkadot_analysis`.`event`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `polkadot_analysis`.`event` (
  `block_id` INT NOT NULL,
  `event_idx` INT NOT NULL,
  `extrinsic_idx` INT NULL DEFAULT NULL,
  `type` VARCHAR(4) NULL DEFAULT NULL,
  `module_id` VARCHAR(64) NULL DEFAULT NULL,
  `event_id` VARCHAR(64) NULL DEFAULT NULL,
  `system` SMALLINT NOT NULL,
  `phase` VARCHAR(100) NULL DEFAULT NULL,
  `attributes` JSON NULL DEFAULT NULL,
  `spec_version_id` INT NULL DEFAULT NULL,
  PRIMARY KEY (`block_id`, `event_idx`),
  INDEX `ix_event_block_id` (`block_id` ASC) VISIBLE,
  INDEX `ix_event_event_id` (`event_id` ASC) VISIBLE,
  INDEX `ix_event_event_idx` (`event_idx` ASC) VISIBLE,
  INDEX `ix_event_extrinsic_idx` (`extrinsic_idx` ASC) VISIBLE,
  INDEX `ix_event_module_id` (`module_id` ASC) VISIBLE,
  INDEX `ix_event_system` (`system` ASC) VISIBLE,
  INDEX `ix_event_type` (`type` ASC) VISIBLE)
ENGINE = InnoDB
DEFAULT CHARACTER SET = utf8mb4
COLLATE = utf8mb4_0900_ai_ci;


-- -----------------------------------------------------
-- Table `polkadot_analysis`.`extrinsic`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `polkadot_analysis`.`extrinsic` (
  `block_id` INT NOT NULL,
  `extrinsic_idx` INT NOT NULL,
  `nesting_idx` INT NOT NULL DEFAULT '0',
  `batch_idx` INT NOT NULL DEFAULT '0',
  `extrinsic_length` VARCHAR(10) NULL DEFAULT NULL,
  `extrinsic_hash` VARCHAR(66) NULL DEFAULT NULL,
  `signed` SMALLINT NOT NULL,
  `from_address` VARCHAR(64) NULL DEFAULT NULL,
  `to_address` VARCHAR(64) NULL DEFAULT NULL,
  `signature` VARCHAR(150) NULL DEFAULT NULL,
  `value` DECIMAL(65,10) NULL DEFAULT NULL,
  `tip` DECIMAL(65,10) NULL DEFAULT NULL,
  `fee` DECIMAL(65,10) NULL DEFAULT NULL,
  `nonce` INT NULL DEFAULT NULL,
  `module_id` VARCHAR(64) NULL DEFAULT NULL,
  `call_id` VARCHAR(64) NULL DEFAULT NULL,
  `success` SMALLINT NOT NULL,
  `spec_version_id` INT NULL DEFAULT NULL,
  `debug_info` JSON NULL DEFAULT NULL,
  `timestamp` BIGINT NULL DEFAULT NULL,
  `datetime` DATETIME NULL DEFAULT NULL,
  PRIMARY KEY (`block_id`, `extrinsic_idx`, `nesting_idx`, `batch_idx`),
  INDEX `ix_extrinsic_from_address` (`from_address` ASC) INVISIBLE,
  INDEX `ix_extrinsic_block_id` (`block_id` ASC) VISIBLE,
  INDEX `ix_extrinsic_call_id` (`call_id` ASC) VISIBLE,
  INDEX `ix_extrinsic_extrinsic_idx` (`extrinsic_idx` ASC) VISIBLE,
  INDEX `ix_extrinsic_module_id` (`module_id` ASC) VISIBLE,
  INDEX `ix_extrinsic_signed` (`signed` ASC) VISIBLE,
  INDEX `ix_extrinsic_to_address` (`to_address` ASC) VISIBLE)
ENGINE = InnoDB
DEFAULT CHARACTER SET = utf8mb4
COLLATE = utf8mb4_0900_ai_ci;

-- -----------------------------------------------------
-- Table `polkadot_analysis`.`error_log`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `polkadot_analysis`.`error_log` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `block_id` INT NOT NULL,
  `error_log` VARCHAR(1500) NOT NULL,
  PRIMARY KEY (`id`),
  INDEX `ix_error_log` (`error_log`(255)) VISIBLE,
  INDEX `ix_block_id` (`block_id` ASC) VISIBLE
)
ENGINE = InnoDB
DEFAULT CHARACTER SET = utf8mb4
COLLATE = utf8mb4_0900_ai_ci;

-- -----------------------------------------------------
-- Table `polkadot_analysis`.`multisig_account`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `polkadot_analysis`.`multisig_account` (
  `address` VARCHAR(255) NOT NULL,
  `threshold` INT NOT NULL,
  PRIMARY KEY (`address`)
)
ENGINE = InnoDB
DEFAULT CHARACTER SET = utf8mb4
COLLATE = utf8mb4_0900_ai_ci;

-- -----------------------------------------------------
-- Table `polkadot_analysis`.`multisig_member_account`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `polkadot_analysis`.`multisig_member_account` (
  `address` VARCHAR(255) NOT NULL,
  `multisig_account_address` VARCHAR(255) NOT NULL,
  PRIMARY KEY (`address`, `multisig_account_address`),
  FOREIGN KEY (`multisig_account_address`) REFERENCES `multisig_account`(`address`)
    ON DELETE CASCADE
    ON UPDATE CASCADE
)
ENGINE = InnoDB
DEFAULT CHARACTER SET = utf8mb4
COLLATE = utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `polkadot_analysis`.`proxy_extrinsic_real_address` (
    `block_id` INT NOT NULL,
    `extrinsic_idx` INT NOT NULL,
    `nesting_idx` INT NOT NULL DEFAULT 0,
    `batch_idx` INT NOT NULL DEFAULT 0,
    `unique_sequence` INT NOT NULL DEFAULT 0,
    `real_address` VARCHAR(64) NOT NULL,
    PRIMARY KEY (`block_id`, `extrinsic_idx`, `nesting_idx`, `batch_idx`, `unique_sequence`),
    FOREIGN KEY (`block_id`, `extrinsic_idx`, `nesting_idx`, `batch_idx`, `unique_sequence`)
    REFERENCES `extrinsic`(`block_id`, `extrinsic_idx`, `nesting_idx`, `batch_idx`, `unique_sequence`)
    ON DELETE CASCADE
    ON UPDATE CASCADE
)
ENGINE = InnoDB
DEFAULT CHARACTER SET = utf8mb4
COLLATE = utf8mb4_0900_ai_ci;

USE `polkadot_analysis`;

DELIMITER $$
USE `polkadot_analysis`$$
CREATE
DEFINER=`root`@`localhost`
TRIGGER `polkadot_analysis`.`account__ai`
AFTER INSERT ON `polkadot_analysis`.`account`
FOR EACH ROW
INSERT INTO account_history SELECT NULL, 
d.address, d.balance_free, d.balance_reserved, d.is_reaped, d.is_validator, d.is_nominator, d.is_council_member,
d.is_tech_comm_member, d.is_registrar, d.is_sudo, d.is_treasury, d.identity_display, d.updated_at_block
    FROM account AS d WHERE d.address = NEW.address$$

USE `polkadot_analysis`$$
CREATE
DEFINER=`root`@`localhost`
TRIGGER `polkadot_analysis`.`account__au`
AFTER UPDATE ON `polkadot_analysis`.`account`
FOR EACH ROW
INSERT INTO account_history SELECT NULL, 
d.address, d.balance_free, d.balance_reserved, d.is_reaped, d.is_validator, d.is_nominator, d.is_council_member,
d.is_tech_comm_member, d.is_registrar, d.is_sudo, d.is_treasury, d.identity_display, d.updated_at_block
    FROM account AS d WHERE d.address = NEW.address$$


DELIMITER ;

SET SQL_MODE=@OLD_SQL_MODE;
SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS;
SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS;
