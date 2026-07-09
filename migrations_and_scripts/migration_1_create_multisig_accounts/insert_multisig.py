import pymysql
import csv

# Database credentials
DB_NAME = "polkadot_analysis"
DB_HOST = "localhost"
DB_PORT = 3306
DB_USERNAME = "root"
DB_PASSWORD = "root"

# CSV file path
CSV_FILE = "multisig_data.csv"

def insert_multisig_account(cursor, address, threshold):
    try:
        # Insert record into multisig_account table
        cursor.execute(
            """
            INSERT INTO multisig_account (address, threshold)
            VALUES (%s, %s)
            """,
            (address, threshold)
        )
    except Exception as e:
        print(f"Error inserting multisig account: {e}")

def insert_multisig_member_account(cursor, multisig_account_address, connected_address):
    try:
        # Insert record into multisig_member_account table
        cursor.execute(
            """
            INSERT INTO multisig_member_account (address, multisig_account_address)
            VALUES (%s, %s)
            """,
            (connected_address, multisig_account_address)
        )
    except Exception as e:
        print(f"Error inserting multisig member account: {e}")

def main():
    # Connect to the database
    connection = pymysql.connect(
        host=DB_HOST,
        user=DB_USERNAME,
        password=DB_PASSWORD,
        database=DB_NAME,
        port=DB_PORT,
        charset='utf8mb4'
    )

    try:
        cursor = connection.cursor()

        # Open the CSV file
        with open(CSV_FILE, newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                # Extract data from CSV
                multisig_address = row[0]
                threshold = int(row[1])
                connected_addresses = row[2:]

                # Insert into multisig_account
                insert_multisig_account(cursor, multisig_address, threshold)

                # Insert into multisig_member_account
                for connected_address in connected_addresses:
                    insert_multisig_member_account(cursor, multisig_address, connected_address)

        # Commit changes
        connection.commit()

    except Exception as e:
        print(f"Error: {e}")

    finally:
        connection.close()

if __name__ == "__main__":
    main()
