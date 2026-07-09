"""
account_data.py

Fetching Account Balance Snapshots over a range of specified block numbers

<Author>: Hanaa Abbas
<Email>: hanaaloutfy94@gmail.com
<Date>: 31 May, 2023

GNU General Public License Version 3
""" 
import getopt
import logging
import sys
import traceback
from logging.handlers import RotatingFileHandler
from timeit import default_timer as timer

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy import tuple_, asc, text

from substrateinterface import SubstrateInterface

from app.models.data import Event, Account, AccountInfoSnapshot

DB_NAME = "polkadot_analysis"
DB_HOST = "localhost"
DB_PORT = 3306
DB_USERNAME = "root"
DB_PASSWORD = "root"
DEBUG = False

DB_CONNECTION = "mysql+mysqlconnector://{}:{}@{}:{}/{}".format(
    DB_USERNAME, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME)

engine = create_engine(DB_CONNECTION, echo=DEBUG, isolation_level="READ_UNCOMMITTED", pool_pre_ping=True)
session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
db_session = scoped_session(session_factory)

# create and configure logger
filename = "../../logs/account_data.log"
logging.basicConfig(level=logging.INFO,
                    handlers=[RotatingFileHandler(filename, maxBytes=1000000000, backupCount=100, mode='a'),
                              logging.StreamHandler(sys.stdout)],
                    format="[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s",
                    datefmt='%Y-%m-%dT%H:%M:%S', )
logger = logging.getLogger()

EXTERNAL_URL = "wss://rpc.polkadot.io"
INTERNAL_URL = "ws://172.20.135.65:9944"


def handle_event_attributes(attributes):
    for attr in attributes:
        if type(attr) is str:
            return attributes[0]
        elif attr['type'] == 'AccountId':
            addr = attr['value']
    return addr


# Main
if __name__ == '__main__':

    try:

        argv = sys.argv[1:]
        url = None
        try:
            opts, args = getopt.getopt(argv, "h:u", ["url="])
        except getopt.GetoptError:
            print('main.py -u <url>')
            sys.exit(2)
        for opt, arg in opts:
            if opt == '-h':
                print('main.py -u <url>')
                sys.exit()
            elif opt in ("-u", "--url"):
                url = arg

        if not url:
            url = INTERNAL_URL

        logger.info("Substrate URL: {}".format(url))
        with SubstrateInterface(url=url, ss58_format=0, type_registry_preset='polkadot',
                                use_remote_preset=True) as substrate:
            logger.info(
                "Connected to chain {} using {} v {}".format(substrate.chain, substrate.name, substrate.version))

            start = timer()

            try:

                # first_index = 7229124
                # block_ids = [1293957, 1739297, 2168299, 2612529, 3042945, 3487164, 3932501, 4332719, 4778061, 5206293,
                #              5650640, 6082432, 6527621, 6973768, 7405900, 7847525, 8279239, 8725455,
                #              9171661, 9573880, 10019762, 10448617, 10883304, 11307029]

                block_ids = [7405900]
                keys = [('Balances', 'Endowed')]  # ('System', 'KilledAccount'),

                # block ranges
                for i in range(0, len(block_ids)):

                    second_index = block_ids[i]

                    # handle account creation and reaping
                    account_event_list = Event.query(db_session) \
                        .filter(tuple_(Event.module_id, Event.event_id).in_(keys)) \
                        .filter(Event.block_id.between(first_index, second_index)). \
                        order_by(text("block_id asc, extrinsic_idx asc, event_idx asc"))

                    logger.info("First set of events size #{}".format(account_event_list.count()))

                    for account_event in account_event_list:
                        addr = handle_event_attributes(account_event.attributes)
                        # check if account entry exists in database
                        account = Account.query(db_session).filter_by(address=addr).first()

                        # if entry did not exist before, create it
                        if not account:
                            account = Account(
                                address=addr,
                                pkey=substrate.ss58_decode(addr),
                                # balance_free=account_info['data']['free'].value / 10 ** token_decimals,
                                # balance_reserved=account_info['data']['reserved'].value / 10 ** token_decimals,
                                # balance_total=(account_info["data"]["free"].value + account_info["data"][
                                #     "reserved"].value) / 10 ** token_decimals,
                                # nonce=account_info['nonce'].value,
                                created_at_block=account_event.block_id,
                                updated_at_block=account_event.block_id,
                                # is_reaped=False,
                            )
                            logger.info(
                                "{} {} at block{}...".format(account_event.event_id, addr, account_event.block_id))
                            account.save(db_session)

                            # else:
                            #     logger.error("FAILURE IN {} {} at Block {}".format(account_event.event_id, addr,
                            #                                                        account_event.block_id))
                    db_session.commit()
                    #reaping an account that exists
                    # else:
                    #     if account_event.event_id == 'KilledAccount':
                    #         Account.query(db_session).filter_by(
                    #             address=account.address
                    #         ).update({Account.balance_free: 0,
                    #                   Account.balance_reserved: 0,
                    #                   Account.balance_total: 0,
                    #                   Account.is_reaped: True,
                    #                   Account.count_reaped: Account.count_reaped + 1,
                    #                   Account.updated_at_block: account_event.block_id},
                    #                  synchronize_session='fetch')
                    #         logger.info(
                    #             "{} {} at Block {}".format(account_event.event_id, addr, account_event.block_id))
                    #         db_session.commit()
                    #
                    #     else:
                    #         logger.error("FAILURE IN {} {} at Block {}".format(account_event.event_id, addr,
                    #                                                            account_event.block_id))

                    # search existing accounts created between specified block range AND
                    # are not reaped
                    # then query account info at designated block_id (second_index)
                    accounts_list = Account.query(db_session).filter(
                        Account.created_at_block.between(1, second_index),
                        # Account.is_reaped.is_not(True)
                    )
                    token_decimals = substrate.token_decimals if second_index >= 1248328 else 12

                    for account in accounts_list:
                        account_info = substrate.query(
                            module='System',
                            storage_function='Account',
                            params=[account.address],
                            block_hash=substrate.get_block_hash(second_index)
                        )

                        snapshot = AccountInfoSnapshot(
                            block_id=second_index,
                            account_id=account.address,
                            pkey=account.pkey_hex,
                            balance_free=account_info['data']['free'].value / 10 ** token_decimals,
                            balance_reserved=account_info['data']['reserved'].value / 10 ** token_decimals,
                            balance_total=(account_info["data"]["free"].value + account_info["data"][
                                "reserved"].value) / 10 ** token_decimals,
                            nonce=account_info['nonce'].value,
                        )
                        snapshot.save(db_session)
                        logger.info(
                            "account_info at {} for {} with balance_total {}".format(second_index, account.address,
                                                                                     snapshot.balance_total))

                    # update the event search range
                    db_session.commit()
                    first_index = second_index + 1

            except Exception as err:
                # clear the db session
                db_session.rollback()
                logger.error(traceback.format_exc())

        logger.info("Block Processing Total Execution Time (seconds): {}".format(timer() - start))
        print("End of Execution....")

    except Exception as err:
        substrate.close()  # close substrate connection
        db_session.remove()  # close db connection
        logger.error(traceback.format_exc())
        sys.exit(0)

    finally:
        substrate.close()
        db_session.remove()
