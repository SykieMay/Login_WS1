import mysql.connector

# 1. Establish the connection
db_connection = mysql.connector.connect(
    host="localhost",        # Or your server IP
    user="root",    # Your MySQL username
    password="",# Your MySQL password
    database="user_account" # The database name
)

# 2. Create a cursor object to execute commands
cursor = db_connection.cursor()

# 3. Execute a SQL query
cursor.execute("SELECT * FROM users")

# 4. Fetch and print the results
results = cursor.fetchall()
for row in results:
    print(row)

# 5. Clean up and close connections
cursor.close()
db_connection.close()