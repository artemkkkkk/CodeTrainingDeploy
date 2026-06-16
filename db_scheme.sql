CREATE TABLE "users" (
  "id" int PRIMARY KEY,
  "name" text,
  "email" text,
  "password" varchar(255),
  "created_at" timestamp
);

CREATE TABLE "tasks" (
  "id" int PRIMARY KEY,
  "user_id" int,
  "name" text,
  "description" text,
  "complete" int,
  "tried" int,
  "difficult" text
);

CREATE TABLE "profile" (
  "id" int PRIMARY KEY,
  "user_id" int,
  "avatar_url" text,
  "rating" int,
  "easy_tasks" int,
  "medium_tasks" int,
  "hard_tasks" int
);

CREATE TABLE "testcases" (
  "id" int PRIMARY KEY,
  "task_id" int,
  "input" text,
  "wanted_output" text,
  "max_time_ms" int
);

CREATE TABLE "Solutions" (
  "id" int PRIMARY KEY,
  "user_id" int,
  "task_id" int,
  "solved_at" timestamp,
  "test_case_id" int,
  "status" bool,
  "recieved_output" text,
  "recieved_time_ms" int
);

CREATE TABLE "Tags" (
  "id" int PRIMARY KEY,
  "name" varchar(50) UNIQUE NOT NULL
);

CREATE TABLE "task_tags" (
  "task_id" int,
  "tag_id" int,
  "Primary" "Key(task_id,tag_id)"
);

ALTER TABLE "tasks" ADD FOREIGN KEY ("user_id") REFERENCES "users" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "profile" ADD FOREIGN KEY ("user_id") REFERENCES "users" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "testcases" ADD FOREIGN KEY ("task_id") REFERENCES "tasks" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "Solutions" ADD FOREIGN KEY ("user_id") REFERENCES "users" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "Solutions" ADD FOREIGN KEY ("task_id") REFERENCES "tasks" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "Solutions" ADD FOREIGN KEY ("test_case_id") REFERENCES "testcases" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "task_tags" ADD FOREIGN KEY ("task_id") REFERENCES "tasks" ("id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "task_tags" ADD FOREIGN KEY ("tag_id") REFERENCES "Tags" ("id") DEFERRABLE INITIALLY IMMEDIATE;

CREATE INDEX idx_task_tags_task ON task_tags(task_id)
CREATE INDEX idx_task_tags_tag ON task_tags(tag_id)

CREATE INDEX idx_solutions_time ON Solutions(solved_at)