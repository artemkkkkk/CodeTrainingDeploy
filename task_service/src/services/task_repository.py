from sqlalchemy.testing.pickleable import User

from task_service.src.database.models import (
    Task,
    TestCase,
    Tag,
    TaskTag,
    Profile
)
from task_service.src.database.session import SessionLocal


def create_task(
    user_id: int,
    name: str,
    description: str,
    difficult: str,
    test_cases,
    tags
):
    db = SessionLocal()

    task = Task(
        user_id=user_id,
        name=name,
        description=description,
        difficult=difficult
    )

    db.add(task)
    db.commit()
    db.refresh(task)

    for testcase in test_cases:
        db_testcase = TestCase(
            task_id=task.id,
            input=testcase.wanted_input,
            wanted_output=testcase.wanted_output,
            max_time_ms=testcase.max_time_ms
        )

        db.add(db_testcase)

    for tag_name in tags:
        tag = db.query(Tag).filter(
            Tag.name == tag_name
        ).first()

        if tag:
            task_tag = TaskTag(
                task_id=task.id,
                tag_id=tag.id
            )

            db.add(task_tag)

    db.commit()

    task_id = task.id

    db.close()

    return task_id


def get_task_testcases(task_name: str):
    db = SessionLocal()

    task = (
        db.query(Task)
        .filter(Task.name == task_name)
        .first()
    )

    if not task:
        db.close()
        return None, []

    testcases = (
        db.query(TestCase)
        .filter(TestCase.task_id == task.id)
        .all()
    )

    print("TASK:", task.name)
    print("TESTCASES COUNT:", len(testcases))
    db.close()
    return task, testcases
from datetime import datetime
from task_service.src.database.models import Solution


def save_solution_result(
    user_id: int,
    task_id: int,
    status: bool,
    solved_at: datetime = None,
    test_case_id: int = 0,
    output: str = "",
    used_time_ms: int = 0
):
    db = SessionLocal()

    solution = Solution(
        user_id=user_id,
        task_id=task_id,
        solved_at=solved_at,
        test_case_id=test_case_id,
        status=status,
        recieved_output=output,
        recieved_time_ms=used_time_ms
    )

    all_solutions = db.query(Solution).all()
    print(f"SOLUTIONS ROWS: {all_solutions=}")

    db.add(solution)
    db.commit()
    db.close()

    print(f"SOLUTION SAVED: {user_id=} {task_id=} {status=} {solved_at=}")


def update_solved_count(user_id: int, task_id: int):
    db = SessionLocal()

    task = db.query(Task).filter(Task.id == task_id).first()
    task.complete += 1

    query = db.query(Profile).filter(Profile.user_id == user_id)
    user_profile = query.first()

    print(f"{task=}")
    print(f"BEFORE UPDATE {user_id=} {user_profile=}")

    if task.difficult == "easy":
        user_profile.easy_tasks += 1
        user_profile.rating += 10
    elif task.difficult == "medium":
        user_profile.medium_tasks += 1
        user_profile.rating += 20
    elif task.difficult == "hard":
        user_profile.hard_tasks += 1
        user_profile.rating += 30

    print(f"UPDATED RATING {user_id=} {task_id=} {task.difficult=} {user_profile.rating=}")

    db.commit()
    db.close()

