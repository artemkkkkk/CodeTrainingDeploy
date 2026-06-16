from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Boolean,
    ForeignKey,
    DateTime
)
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)

    name = Column(Text, nullable=False)
    description = Column(Text, nullable=False)

    complete = Column(Integer, default=0)
    tried = Column(Integer, default=0)

    difficult = Column(Text, nullable=False)


class Profile(Base):
    __tablename__ = "profile"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    avatar_url = Column(Text, nullable=False)
    rating = Column(Integer, nullable=False)
    easy_tasks = Column(Integer, nullable=False)
    medium_tasks = Column(Integer, nullable=False)
    hard_tasks = Column(Integer, nullable=False)


class TestCase(Base):
    __tablename__ = "testcases"

    id = Column(Integer, primary_key=True)

    task_id = Column(
        Integer,
        nullable=False
    )

    input = Column(Text, nullable=False)

    wanted_output = Column(
        Text,
        nullable=False
    )

    max_time_ms = Column(
        Integer,
        nullable=False
    )


class Solution(Base):
    __tablename__ = "solutions"

    id = Column(Integer, primary_key=True)

    user_id = Column(Integer, nullable=False)

    task_id = Column(
        Integer,
        nullable=False
    )

    solved_at = Column(DateTime)

    test_case_id = Column(
        Integer,
    )

    status = Column(Boolean)

    recieved_output = Column(Text)

    recieved_time_ms = Column(Integer)


class Tag(Base):
    __tablename__ = "Tags"

    id = Column(Integer, primary_key=True)

    name = Column(
        String(50),
        unique=True,
        nullable=False
    )


class TaskTag(Base):
    __tablename__ = "task_tags"

    task_id = Column(
        Integer,
        ForeignKey("tasks.id"),
        primary_key=True
    )

    tag_id = Column(
        Integer,
        ForeignKey("Tags.id"),
        primary_key=True
    )
