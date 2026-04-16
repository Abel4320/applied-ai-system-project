from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import Enum


class Priority(Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

    def _rank(self) -> int:
        """Return sort order integer where lower = higher priority."""
        return {"high": 1, "medium": 2, "low": 3}[self.value]


class TaskType(Enum):
    WALK = "walk"
    FEEDING = "feeding"
    MEDICATION = "medication"
    ENRICHMENT = "enrichment"
    GROOMING = "grooming"


@dataclass
class Task:
    name: str
    duration: int  # minutes
    priority: Priority
    task_type: TaskType
    completed: bool = False
    pet_name: str = ""            # back-reference so skipped tasks know which pet they belong to
    due_date: date | None = None  # None = no deadline; used for deadline-aware sorting
    frequency: str = "once"       # "once" | "daily" | "weekly"
    scheduled_time: str = ""      # "HH:MM" wall-clock start time, empty if unscheduled

    def mark_complete(self) -> None:
        """Mark this task as completed."""
        self.completed = True

    def next_due_date(self) -> date | None:
        """Return the next due date based on frequency, or None if once/no due date."""
        if self.frequency == "daily" and self.due_date:
            return self.due_date + timedelta(days=1)
        if self.frequency == "weekly" and self.due_date:
            return self.due_date + timedelta(weeks=1)
        return None

    def __lt__(self, other: "Task") -> bool:
        """Compare tasks by priority, then deadline, then duration for stable greedy sorting."""
        return (
            self.priority._rank(),
            self.due_date or date.max,
            self.duration,
        ) < (
            other.priority._rank(),
            other.due_date or date.max,
            other.duration,
        )


@dataclass
class Pet:
    name: str
    species: str
    age: int
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        """Append a task to this pet and stamp it with the pet's name."""
        task.pet_name = self.name
        self.tasks.append(task)

    def remove_task(self, task: Task) -> None:
        """Remove a task from this pet's task list."""
        self.tasks.remove(task)

    def get_tasks(self) -> list[Task]:
        """Return a shallow copy of all tasks for this pet."""
        return self.tasks.copy()

    def get_incomplete_tasks(self) -> list[Task]:
        """Return only tasks that have not yet been completed."""
        return [t for t in self.tasks if not t.completed]

    def get_tasks_by_type(self, task_type: TaskType) -> list[Task]:
        """Return all tasks matching the given TaskType."""
        return [t for t in self.tasks if t.task_type == task_type]

    def get_tasks_by_status(self, completed: bool) -> list[Task]:
        """Return tasks filtered by completed status."""
        return [t for t in self.tasks if t.completed == completed]

    def get_tasks_by_priority(self, priority: Priority) -> list[Task]:
        """Return all tasks matching the given Priority."""
        return [t for t in self.tasks if t.priority == priority]

    def complete_task(self, task: Task) -> Task | None:
        """Mark a task complete and, if recurring, add the next occurrence to the pet's list.

        Returns the newly created Task if one was created, otherwise None.
        """
        task.mark_complete()
        next_due = task.next_due_date()
        if next_due is not None:
            next_task = Task(
                name=task.name,
                duration=task.duration,
                priority=task.priority,
                task_type=task.task_type,
                frequency=task.frequency,
                due_date=next_due,
            )
            self.add_task(next_task)
            return next_task
        return None

    def reset_recurring_tasks(self) -> None:
        """Mark all daily/weekly tasks incomplete so they re-enter the next day's schedule."""
        for task in self.tasks:
            if task.frequency in ("daily", "weekly"):
                task.completed = False


@dataclass
class Owner:
    name: str
    time_available: int  # total daily budget in minutes
    pets: list[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        """Add a pet to this owner's pet list."""
        self.pets.append(pet)

    def remove_pet(self, pet: Pet) -> None:
        """Remove a pet from this owner's pet list."""
        self.pets.remove(pet)

    def get_available_time(self) -> int:
        """Return the owner's total daily time budget in minutes."""
        return self.time_available

    def get_all_tasks(self) -> list[Task]:
        """Return every task across all pets."""
        return [task for pet in self.pets for task in pet.tasks]


@dataclass
class DailyPlan:
    owner: Owner
    pet: Pet
    scheduled_tasks: list[Task] = field(default_factory=list)
    skipped_tasks: list[tuple[Task, str]] = field(default_factory=list)  # (task, reason)
    total_time: int = 0  # minutes consumed
    explanation: list[str] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        """Add a task to the schedule and accumulate its duration into total_time."""
        self.scheduled_tasks.append(task)
        self.total_time += task.duration

    def skip_task(self, task: Task, reason: str) -> None:
        """Record a skipped task with the reason it was excluded."""
        self.skipped_tasks.append((task, reason))
        self.explanation.append(f"Skipped '{task.name}': {reason}")

    def get_summary(self) -> str:
        """Return a formatted multi-line string of scheduled and skipped tasks."""
        lines = [
            f"Daily Plan — {self.pet.name} (Owner: {self.owner.name})",
            f"  Scheduled: {len(self.scheduled_tasks)} tasks, {self.total_time} min",
        ]
        for task in self.scheduled_tasks:
            lines.append(
                f"    [{task.priority.value.upper()}] {task.name} ({task.duration} min)"
            )
        if self.skipped_tasks:
            lines.append(f"  Skipped: {len(self.skipped_tasks)} tasks")
            for task, reason in self.skipped_tasks:
                lines.append(f"    - {task.name}: {reason}")
        return "\n".join(lines)


class Scheduler:
    def __init__(self, owner: Owner):
        """Initialize the scheduler with an owner."""
        self.owner = owner
        self._time_remaining: int = 0  # reset by generate_schedule on every call

    def generate_schedule(self) -> list[DailyPlan]:
        """Greedy schedule across all pets: highest-priority tasks first until time runs out."""
        self._time_remaining = self.owner.time_available  # reset budget each call
        return [self.generate_plan_for_pet(pet) for pet in self.owner.pets]

    def generate_plan_for_pet(self, pet: Pet) -> DailyPlan:
        """Schedule one pet's incomplete tasks against the shared time budget."""
        plan = DailyPlan(owner=self.owner, pet=pet)
        for task in self.prioritize_tasks(pet):
            if task.duration <= self._time_remaining:
                plan.add_task(task)
                self._time_remaining -= task.duration
                plan.explanation.append(
                    f"Scheduled '{task.name}' ({task.duration} min, {task.priority.value})"
                )
            else:
                plan.skip_task(
                    task,
                    f"needs {task.duration} min, only {self._time_remaining} min remaining",
                )
        return plan

    def prioritize_tasks(self, pet: Pet) -> list[Task]:
        """Sort incomplete tasks by priority, then earliest deadline, then shortest duration."""
        return sorted(pet.get_incomplete_tasks())

    def calculate_total_time(self, tasks: list[Task]) -> int:
        """Sum duration across a list of tasks."""
        return sum(t.duration for t in tasks)

    def has_time_conflict(self, pet: Pet) -> bool:
        """Return True if the pet's incomplete tasks exceed the owner's total time budget."""
        return self.calculate_total_time(pet.get_incomplete_tasks()) > self.owner.time_available

    def detect_conflicts(self) -> list[str]:
        """Return a list of warning strings describing scheduling conflicts across all pets.

        Checks performed:
        1. Total task time across all pets exceeds owner's available time.
        2. HIGH priority tasks alone exceed available time (critical tasks at risk).
        3. Tasks with scheduled_time set overlap between different pets.
        """
        warnings: list[str] = []
        budget = self.owner.time_available
        all_incomplete: list[Task] = [
            task
            for pet in self.owner.pets
            for task in pet.get_incomplete_tasks()
        ]

        # 1. Total time vs budget
        total = self.calculate_total_time(all_incomplete)
        if total > budget:
            warnings.append(
                f"Total task time ({total} min) exceeds available time "
                f"({budget} min) by {total - budget} min."
            )

        # 2. HIGH priority tasks alone exceed budget
        high_tasks = [t for t in all_incomplete if t.priority == Priority.HIGH]
        high_total = self.calculate_total_time(high_tasks)
        if high_total > budget:
            names = ", ".join(t.name for t in high_tasks)
            warnings.append(
                f"HIGH priority tasks alone ({high_total} min) exceed available time "
                f"({budget} min). At-risk tasks: {names}."
            )

        # 3. Scheduled-time overlaps across pets
        timed_tasks = sorted(
            [t for t in all_incomplete if t.scheduled_time],
            key=lambda t: t.scheduled_time,
        )
        for a, b in zip(timed_tasks, timed_tasks[1:]):
            a_end = self._to_minutes(a.scheduled_time) + a.duration
            b_start = self._to_minutes(b.scheduled_time)
            if a_end > b_start and a.pet_name != b.pet_name:
                warnings.append(
                    f"Overlap: '{a.name}' ({a.pet_name}, ends {a_end // 60:02d}:{a_end % 60:02d}) "
                    f"overlaps '{b.name}' ({b.pet_name}, starts {b.scheduled_time})."
                )

        return warnings

    @staticmethod
    def _to_minutes(time_str: str) -> int:
        """Convert 'HH:MM' string to total minutes since midnight."""
        h, m = map(int, time_str.split(":"))
        return h * 60 + m

    def find_duplicate_tasks(self, pet: Pet) -> list[str]:
        """Return names of tasks that appear more than once in the pet's task list."""
        seen: set[str] = set()
        duplicates: list[str] = []
        for task in pet.tasks:
            if task.name in seen:
                duplicates.append(task.name)
            seen.add(task.name)
        return duplicates

    # ── Sorting ───────────────────────────────────────────────────────────────

    @staticmethod
    def sort_by_time(tasks: list[Task]) -> list[Task]:
        """Return tasks sorted by duration, shortest first."""
        return sorted(tasks, key=lambda t: t.duration)

    @staticmethod
    def sort_by_priority(tasks: list[Task]) -> list[Task]:
        """Return tasks sorted HIGH → MEDIUM → LOW."""
        return sorted(tasks, key=lambda t: t.priority._rank())

    @staticmethod
    def sort_by_scheduled_time(tasks: list[Task]) -> list[Task]:
        """Return tasks sorted by scheduled_time (HH:MM); unscheduled tasks go last."""
        return sorted(tasks, key=lambda t: t.scheduled_time or "99:99")

    # ── Filtering ─────────────────────────────────────────────────────────────

    @staticmethod
    def filter_by_status(tasks: list[Task], completed: bool) -> list[Task]:
        """Return only tasks whose completed flag matches the given value."""
        return [t for t in tasks if t.completed == completed]

    @staticmethod
    def filter_by_pet(tasks: list[Task], pet_name: str) -> list[Task]:
        """Return only tasks belonging to the named pet."""
        return [t for t in tasks if t.pet_name == pet_name]

    @staticmethod
    def filter_by_type(tasks: list[Task], task_type: TaskType) -> list[Task]:
        """Return only tasks of the given TaskType."""
        return [t for t in tasks if t.task_type == task_type]
