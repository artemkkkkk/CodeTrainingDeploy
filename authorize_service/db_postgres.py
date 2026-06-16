import os

import psycopg2
from dotenv import load_dotenv


load_dotenv()


class Database:

    def init(self):
        self.conn = None
        self.connect()

    def connect(self):
        self.conn = psycopg2.connect(
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT")
        )

    def create_tables(self):
        cursor = self.conn.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            is_moder BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        self.conn.commit()

    def create_user(self, name, email, password_hash):
        cursor = self.conn.cursor()

        cursor.execute(
            """
            INSERT INTO users (name, email, password)
            VALUES (%s, %s, %s)
            RETURNING id
            """,
            (name, email, password_hash)
        )

        new_user_id = cursor.fetchone()[0]
        avatar = "https://iimg.su/i/Mmx6NE"

        cursor.execute(
            """
            INSERT INTO profile (user_id, avatar_url)
            VALUES (%s, %s)
            """,
            (new_user_id, avatar)
        )

        self.conn.commit()

    def get_user_by_name(self, name):
        cursor = self.conn.cursor()

        cursor.execute(
            """
            SELECT id, name, email, password, created_at
            FROM users
            WHERE name = %s
            """,
            (name,)
        )

        row = cursor.fetchone()

        if not row:
            return None

        return {
            "id": row[0],
            "name": row[1],
            "email": row[2],
            "password_hash": row[3],
            # "is_moder": row[4],
            "is_moder": False,
            "created_at": str(row[4])
        }

    def get_user_by_id(self, user_id):
        cursor = self.conn.cursor()

        cursor.execute(
            """
            SELECT id, name, email, created_at
            FROM users
            WHERE id = %s
            """,
            (user_id,)
        )

        row = cursor.fetchone()

        if not row:
            return None

        return {
            "id": row[0],
            "name": row[1],
            "email": row[2],
            "is_moder": False,
            "created_at": str(row[3])
        }
