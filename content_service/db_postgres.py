import os

import psycopg2
from dotenv import load_dotenv


load_dotenv()


class Database:

    def __init__(self):
        self.conn = None
        self.connect()

    def connect(self):
        dsn = f"postgresql://{os.getenv("DB_USER")}:{os.getenv("DB_PASSWORD")}@{os.getenv("DB_HOST")}:{os.getenv("DB_PORT")}/{os.getenv("DB_NAME")}"
        print(f"{dsn=}")
        self.conn = psycopg2.connect(dsn=dsn)

    def create_tables(self):
        cursor = self.conn.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS "users" (
        "id" SERIAL PRIMARY KEY,
        "name" text,
        "email" text,
        "password" varchar(255),
        "created_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS "tasks" (
        "id" SERIAL PRIMARY KEY,
        "user_id" int,
        "name" text,
        "description" text,
        "complete" int DEFAULT 0,
        "tried" int DEFAULT 0,
        "difficult" text
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS "profile" (
        "id" SERIAL PRIMARY KEY,
        "user_id" int,
        "avatar_url" text,
        "rating" int DEFAULT 0,
        "easy_tasks" int DEFAULT 0,
        "medium_tasks" int DEFAULT 0,
        "hard_tasks" int DEFAULT 0
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS "testcases" (
        "id" SERIAL PRIMARY KEY,
        "task_id" int,
        "input" text,
        "wanted_output" text,
        "max_time_ms" int
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS "solutions" (
        "id" SERIAL PRIMARY KEY,
        "user_id" int,
        "task_id" int,
        "solved_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        "test_case_id" int,
        "status" bool,
        "recieved_output" text,
        "recieved_time_ms" int
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS "Tags" (
        "id" SERIAL PRIMARY KEY,
        "name" varchar(50) UNIQUE NOT NULL
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS "task_tags" (
        "task_id" SERIAL,
        "tag_id" SERIAL,
        PRIMARY KEY ("task_id", "tag_id")
        );
        """)

        # cursor.execute("""
        # ALTER TABLE "tasks"
        # ADD FOREIGN KEY ("user_id")
        # REFERENCES "users" ("id")
        # DEFERRABLE INITIALLY IMMEDIATE;
        # """)

        cursor.execute("""
        ALTER TABLE "profile"
        ADD FOREIGN KEY ("user_id")
        REFERENCES "users" ("id")
        DEFERRABLE INITIALLY IMMEDIATE;
        """)

        # cursor.execute("""
        # ALTER TABLE "testcases"
        # ADD FOREIGN KEY ("task_id")
        # REFERENCES "tasks" ("id")
        # DEFERRABLE INITIALLY IMMEDIATE;
        # """)
        #
        # cursor.execute("""
        # ALTER TABLE "Solutions"
        # ADD FOREIGN KEY ("user_id")
        # REFERENCES "users" ("id")
        # DEFERRABLE INITIALLY IMMEDIATE;
        # """)
        #
        # cursor.execute("""
        # ALTER TABLE "Solutions"
        # ADD FOREIGN KEY ("task_id")
        # REFERENCES "tasks" ("id")
        # DEFERRABLE INITIALLY IMMEDIATE;
        # """)
        #
        # cursor.execute("""
        # ALTER TABLE "Solutions"
        # ADD FOREIGN KEY ("test_case_id")
        # REFERENCES "testcases" ("id")
        # DEFERRABLE INITIALLY IMMEDIATE;
        # """)
        #
        # cursor.execute("""
        # ALTER TABLE "task_tags"
        # ADD FOREIGN KEY ("task_id")
        # REFERENCES "tasks" ("id")
        # DEFERRABLE INITIALLY IMMEDIATE;
        # """)
        #
        # cursor.execute("""
        # ALTER TABLE "task_tags"
        # ADD FOREIGN KEY ("tag_id")
        # REFERENCES "Tags" ("id")
        # DEFERRABLE INITIALLY IMMEDIATE;
        # """)
        #
        # cursor.execute("""
        # CREATE INDEX IF NOT EXISTS idx_task_tags_task
        # ON task_tags(task_id);
        # """)
        #
        # cursor.execute("""
        # CREATE INDEX IF NOT EXISTS idx_task_tags_tag
        # ON task_tags(tag_id);
        # """)
        #
        # cursor.execute("""
        # CREATE INDEX IF NOT EXISTS idx_solutions_time
        # ON "Solutions"(solved_at);
        # """)

        self.conn.commit()

    def get_tasks(self, offset, limit, difficult):
        cursor = self.conn.cursor()

        if limit <= 0:
            limit = 10

        if difficult:
            cursor.execute(
                """
                SELECT name, description, difficult, complete, tried
                FROM tasks
                WHERE difficult = %s
                LIMIT %s OFFSET %s
                """,
                (difficult, limit, offset)
            )
        else:
            cursor.execute(
                """
                SELECT name, description, difficult, complete, tried
                FROM tasks
                LIMIT %s OFFSET %s
                """,
                (limit, offset)
            )

        rows = cursor.fetchall()

        tasks = []

        for row in rows:
            tasks.append({
                "name": row[0],
                "description": row[1],
                "difficult": row[2],
                "complete": row[3] if row[3] else 0,
                "tried": row[4] if row[4] else 0,
                "tags": []
            })

        return tasks

    def get_profile(self, user_id):
        cursor = self.conn.cursor()

        cursor.execute(
            """
            SELECT users.name,
                users.email,
                profile.avatar_url,
                profile.rating,
                profile.easy_tasks,
                profile.medium_tasks,
                profile.hard_tasks
            FROM users
            LEFT JOIN profile
            ON users.id = profile.user_id
            WHERE users.id = %s
            """,
            (user_id,)
        )

        row = cursor.fetchone()

        if not row:
            return None

        return {
            "name": row[0],
            "description": row[1],
            "avatar_url": row[2] if row[2] else "",
            "rating": row[3] if row[3] else 0,
            "easy_tasks": row[4] if row[4] else 0,
            "medium_tasks": row[5] if row[5] else 0,
            "hard_tasks": row[6] if row[6] else 0
        }

    def get_submission(self, user_id, task_name) -> tuple[bool, bool]:
        cursor = self.conn.cursor()

        try:
            cursor.execute(
                """
                SELECT id FROM tasks WHERE name = %s
                """,
                (task_name,)
            )
        except Exception as e:
            print(f"ERROR: {e}")

        task_id = cursor.fetchone()[0]
        print(f"TASK ID: {task_id=}")

        try:
            cursor.execute(
                """
                SELECT status FROM solutions WHERE user_id = %s AND task_id = %s
                """,
                (user_id, task_id)
            )
        except Exception as e:
            print(f"ERROR: {e}")

        rows = cursor.fetchall()
        print(f"STATUS ROWS: {rows=}")

        cursor.execute("SELECT * FROM solutions")
        rows = cursor.fetchall()
        print(f"SOLUTIONS ROWS: {rows=}")

        if not rows:
            return False, False

        if any(rows):
            return True, True

        return True, False