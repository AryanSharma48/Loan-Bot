import sqlite3
import os

# Define the database name
DB_FILE = 'database.db'

# Delete the old database file if it exists, so we can start fresh
if os.path.exists(DB_FILE):
    os.remove(DB_FILE)

# Connect to the SQLite database (this will create the file)
conn = sqlite3.connect(DB_FILE)
cursor = conn.cursor()

print("Database created.")

# This table holds our "synthetic customer" data
cursor.execute('''
CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    kyc_status TEXT NOT NULL,      -- 'verified', 'pending', 'failed'
    credit_score INTEGER NOT NULL,
    loan_limit INTEGER NOT NULL
);
''')
print("Table 'customers' created.")

# --- Insert our mock customers ---
# This is the "Customer Simulation"
mock_customers = [
    # The "Golden Path" user - will be approved
    ('Alice', 'verified', 780, 50000),
    
    # The "KYC Fail" user - will be stopped at KYC
    ('Bob', 'pending', 650, 20000),
    
    # The "Credit Score Fail" user - will be rejected for low score
    ('Charlie', 'verified', 550, 10000),
    
    # The "Loan Limit" user - will be asked to take a lower amount
    ('David', 'verified', 720, 15000),

]

cursor.executemany('''
INSERT INTO customers (name, kyc_status, credit_score, loan_limit) 
VALUES (?, ?, ?, ?)
''', mock_customers)

print(f"Inserted {len(mock_customers)} mock customers.")

# Commit the changes and close the connection
conn.commit()
conn.close()

print("Database setup complete. You can now run 'app.py'.")
