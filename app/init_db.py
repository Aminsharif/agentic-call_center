import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv
import os
from .database import engine
from .models import Base

def init_database():
    # Load environment variables
    load_dotenv()
    
    try:
        # Connect to MySQL server
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="123456"
        )
        
        if connection.is_connected():
            cursor = connection.cursor()
            
            # Create database if it doesn't exist
            cursor.execute("CREATE DATABASE IF NOT EXISTS call_center")
            print("Database 'call_center' created successfully")
            
            # Close connection
            cursor.close()
            connection.close()
            
            # Create all tables
            Base.metadata.create_all(bind=engine)
            print("Tables created successfully")
            
    except Error as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    init_database() 