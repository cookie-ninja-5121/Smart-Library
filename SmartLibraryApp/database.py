
import mysql.connector
from mysql.connector import Error

# MySQL connection settings
DB_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "root",
    "database": "smart_library",
}


def get_connection():
    """Create and return a MySQL database connection."""
    return mysql.connector.connect(**DB_CONFIG)


def test_connection():
    """Test the connection and display the existing tables."""
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        print("Connected to Smart Library database!")

        cursor.execute("SHOW TABLES")

        print("\nTables found:")
        for row in cursor.fetchall():
            print("-", row[0])

    except Error as error:
        print("Database connection failed:", error)

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None and connection.is_connected():
            connection.close()


if __name__ == "__main__":
    test_connection()
