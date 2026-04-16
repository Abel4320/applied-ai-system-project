from pawpal_system import Owner, Pet, Task, Priority, TaskType, Scheduler


def print_tasks(label: str, tasks: list[Task]) -> None:
    print(f"\n{label}")
    if not tasks:
        print("  (none)")
    for t in tasks:
        status = "done" if t.completed else "pending"
        print(f"  [{t.priority.value.upper()}] {t.name} — {t.duration} min | {t.task_type.value} | {status}")


def main():
    # ── Setup ──────────────────────────────────────────────────────────────────
    alice = Owner(name="Alice", time_available=90)

    buddy = Pet(name="Buddy", species="dog", age=3)

    # Tasks added intentionally out of order (priority and duration mixed)
    buddy.add_task(Task("Grooming",   30, Priority.LOW,    TaskType.GROOMING))
    buddy.add_task(Task("Medication",  5, Priority.HIGH,   TaskType.MEDICATION))
    buddy.add_task(Task("Enrichment", 20, Priority.MEDIUM, TaskType.ENRICHMENT))
    buddy.add_task(Task("Walk",       25, Priority.HIGH,   TaskType.WALK))
    buddy.add_task(Task("Feeding",    10, Priority.MEDIUM, TaskType.FEEDING))

    # Mark one task complete for filter demo
    buddy.tasks[0].mark_complete()  # Grooming -> done

    alice.add_pet(buddy)
    all_tasks = buddy.get_tasks()

    # ── Sorting ────────────────────────────────────────────────────────────────
    print("=== Sorting ===")
    print_tasks("sort_by_time (shortest first):",
                Scheduler.sort_by_time(all_tasks))

    print_tasks("sort_by_priority (HIGH -> MEDIUM -> LOW):",
                Scheduler.sort_by_priority(all_tasks))

    # ── Filtering ──────────────────────────────────────────────────────────────
    print("\n=== Filtering ===")
    print_tasks("filter_by_status(completed=True):",
                Scheduler.filter_by_status(all_tasks, completed=True))

    print_tasks("filter_by_status(completed=False):",
                Scheduler.filter_by_status(all_tasks, completed=False))

    print_tasks("filter_by_type(WALK):",
                Scheduler.filter_by_type(all_tasks, TaskType.WALK))

    print_tasks("filter_by_type(MEDICATION):",
                Scheduler.filter_by_type(all_tasks, TaskType.MEDICATION))

    # ── Schedule ───────────────────────────────────────────────────────────────
    print("\n=== Daily Schedule ===")
    scheduler = Scheduler(alice)
    for plan in scheduler.generate_schedule():
        print(plan.get_summary())


if __name__ == "__main__":
    main()
