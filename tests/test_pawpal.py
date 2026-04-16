from datetime import date, timedelta

from pawpal_system import Owner, Pet, Task, Priority, TaskType, Scheduler


# ── Existing tests ────────────────────────────────────────────────────────────

def test_task_mark_complete():
    task = Task("Walk", 20, Priority.HIGH, TaskType.WALK)
    assert task.completed is False
    task.mark_complete()
    assert task.completed is True


def test_pet_add_task():
    pet = Pet("Buddy", "dog", 3)
    assert len(pet.tasks) == 0
    pet.add_task(Task("Walk", 20, Priority.HIGH, TaskType.WALK))
    assert len(pet.tasks) == 1


# ── Sorting ───────────────────────────────────────────────────────────────────

def test_sort_by_priority_returns_high_before_low():
    tasks = [
        Task("Grooming",  30, Priority.LOW,    TaskType.GROOMING),
        Task("Walk",      20, Priority.HIGH,   TaskType.WALK),
        Task("Enrichment",15, Priority.MEDIUM, TaskType.ENRICHMENT),
    ]
    result = Scheduler.sort_by_priority(tasks)
    priorities = [t.priority for t in result]
    assert priorities == [Priority.HIGH, Priority.MEDIUM, Priority.LOW]


def test_sort_by_priority_preserves_all_tasks():
    tasks = [
        Task("A", 10, Priority.LOW,  TaskType.FEEDING),
        Task("B", 10, Priority.HIGH, TaskType.FEEDING),
    ]
    result = Scheduler.sort_by_priority(tasks)
    assert len(result) == 2


def test_sort_by_priority_single_task_unchanged():
    tasks = [Task("Walk", 20, Priority.HIGH, TaskType.WALK)]
    assert Scheduler.sort_by_priority(tasks) == tasks


def test_sort_by_time_returns_shortest_first():
    tasks = [
        Task("Grooming",   30, Priority.LOW,    TaskType.GROOMING),
        Task("Medication",  5, Priority.HIGH,   TaskType.MEDICATION),
        Task("Walk",       20, Priority.MEDIUM, TaskType.WALK),
    ]
    result = Scheduler.sort_by_time(tasks)
    durations = [t.duration for t in result]
    assert durations == [5, 20, 30]


def test_sort_by_time_does_not_mutate_original():
    tasks = [
        Task("B", 30, Priority.LOW,  TaskType.GROOMING),
        Task("A",  5, Priority.HIGH, TaskType.MEDICATION),
    ]
    original_order = [t.name for t in tasks]
    Scheduler.sort_by_time(tasks)
    assert [t.name for t in tasks] == original_order


# ── Recurrence ────────────────────────────────────────────────────────────────

def test_daily_task_creates_next_occurrence_one_day_later():
    today = date(2026, 3, 31)
    pet = Pet("Buddy", "dog", 3)
    task = Task("Feeding", 10, Priority.HIGH, TaskType.FEEDING,
                frequency="daily", due_date=today)
    pet.add_task(task)

    next_task = pet.complete_task(task)

    assert next_task is not None
    assert next_task.due_date == today + timedelta(days=1)


def test_weekly_task_creates_next_occurrence_seven_days_later():
    today = date(2026, 3, 31)
    pet = Pet("Buddy", "dog", 3)
    task = Task("Grooming", 30, Priority.LOW, TaskType.GROOMING,
                frequency="weekly", due_date=today)
    pet.add_task(task)

    next_task = pet.complete_task(task)

    assert next_task is not None
    assert next_task.due_date == today + timedelta(weeks=1)


def test_daily_task_adds_new_task_to_pet_list():
    today = date(2026, 3, 31)
    pet = Pet("Buddy", "dog", 3)
    task = Task("Feeding", 10, Priority.HIGH, TaskType.FEEDING,
                frequency="daily", due_date=today)
    pet.add_task(task)

    pet.complete_task(task)

    assert len(pet.tasks) == 2
    assert pet.tasks[1].due_date == today + timedelta(days=1)


def test_once_task_does_not_create_next_occurrence():
    pet = Pet("Buddy", "dog", 3)
    task = Task("Vet visit", 60, Priority.HIGH, TaskType.MEDICATION,
                frequency="once", due_date=date(2026, 3, 31))
    pet.add_task(task)

    next_task = pet.complete_task(task)

    assert next_task is None
    assert len(pet.tasks) == 1


def test_recurring_task_without_due_date_does_not_create_next_occurrence():
    pet = Pet("Buddy", "dog", 3)
    task = Task("Walk", 20, Priority.HIGH, TaskType.WALK, frequency="daily")
    # no due_date set
    pet.add_task(task)

    next_task = pet.complete_task(task)

    assert next_task is None


def test_recurring_task_inherits_same_name_and_duration():
    today = date(2026, 3, 31)
    pet = Pet("Buddy", "dog", 3)
    task = Task("Feeding", 10, Priority.MEDIUM, TaskType.FEEDING,
                frequency="daily", due_date=today)
    pet.add_task(task)

    next_task = pet.complete_task(task)

    assert next_task.name == task.name
    assert next_task.duration == task.duration
    assert next_task.priority == task.priority


# ── Conflict Detection ────────────────────────────────────────────────────────

def test_detect_conflicts_returns_empty_when_tasks_fit():
    owner = Owner("Alice", time_available=60)
    pet = Pet("Buddy", "dog", 3)
    pet.add_task(Task("Walk",    20, Priority.HIGH,   TaskType.WALK))
    pet.add_task(Task("Feeding", 10, Priority.MEDIUM, TaskType.FEEDING))
    owner.add_pet(pet)

    warnings = Scheduler(owner).detect_conflicts()

    assert warnings == []


def test_detect_conflicts_warns_when_total_time_exceeds_budget():
    owner = Owner("Alice", time_available=20)
    pet = Pet("Buddy", "dog", 3)
    pet.add_task(Task("Walk",    20, Priority.HIGH, TaskType.WALK))
    pet.add_task(Task("Grooming",30, Priority.LOW,  TaskType.GROOMING))
    owner.add_pet(pet)

    warnings = Scheduler(owner).detect_conflicts()

    assert any("exceeds available time" in w for w in warnings)


def test_detect_conflicts_warns_when_high_priority_tasks_exceed_budget():
    owner = Owner("Alice", time_available=15)
    pet = Pet("Buddy", "dog", 3)
    pet.add_task(Task("Walk",       20, Priority.HIGH, TaskType.WALK))
    pet.add_task(Task("Medication", 10, Priority.HIGH, TaskType.MEDICATION))
    owner.add_pet(pet)

    warnings = Scheduler(owner).detect_conflicts()

    assert any("HIGH priority" in w for w in warnings)


def test_detect_conflicts_no_warnings_for_empty_pet():
    owner = Owner("Alice", time_available=60)
    owner.add_pet(Pet("Buddy", "dog", 3))  # no tasks

    warnings = Scheduler(owner).detect_conflicts()

    assert warnings == []


def test_detect_conflicts_warns_on_cross_pet_scheduled_time_overlap():
    owner = Owner("Alice", time_available=120)
    buddy = Pet("Buddy", "dog", 3)
    buddy.add_task(Task("Walk", 30, Priority.HIGH, TaskType.WALK,
                        scheduled_time="08:00"))
    whiskers = Pet("Whiskers", "cat", 5)
    whiskers.add_task(Task("Feeding", 10, Priority.MEDIUM, TaskType.FEEDING,
                           scheduled_time="08:15"))
    owner.add_pet(buddy)
    owner.add_pet(whiskers)

    warnings = Scheduler(owner).detect_conflicts()

    assert any("Overlap" in w for w in warnings)
