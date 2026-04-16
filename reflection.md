# PawPal+ Project Reflection

## 1. System Design
**Core User Actions:**

1. **Add a Pet**: User enters their pet's information (name, species, age) and their own details (name, available time for pet care).

2. **Manage Care Tasks**: User creates, edits, or removes care tasks for their pet. Each task has a name, duration, priority level, and type (walk, feeding, medication, enrichment, grooming).

3. **Generate Daily Schedule**: User clicks to generate a daily care plan. The system creates a prioritized schedule that fits within the available time and explains why tasks were included or skipped.

**a. Initial design**

My initial UML design included six classes and two enumerations:

**Classes:**

1. **Owner**: Holds owner's name and available time for pet care. Responsible for managing the time constraint and storing a list of pets.

2. **Pet**: Stores pet details (name, species, age). Responsible for maintaining and managing its list of care tasks.

3. **Task**: Represents a single care activity with name, duration, priority, type, and completion status. Responsible for tracking whether it's done and comparing itself to other tasks by priority.

4. **Scheduler**: Takes an Owner and Pet as input. Responsible for running the scheduling algorithm that prioritizes tasks and respects time constraints.

5. **DailyPlan**: Holds the scheduling output—scheduled tasks, skipped tasks, total time used, and explanation text. Responsible for building and displaying the final plan summary.

**Enumerations:**

6. **Priority**: Defines task priority levels (HIGH, MEDIUM, LOW) for sorting.

7. **TaskType**: Defines valid task categories (WALK, FEEDING, MEDICATION, ENRICHMENT, GROOMING).

**Key Relationships:**
- Owner owns one or more Pets (1-to-many)
- Pet has zero or more Tasks (1-to-many)
- Scheduler uses Owner and Pet to create a DailyPlan

**b. Design changes**

Yes, my design changed significantly during implementation. Here are the key changes:

**1. Removed unused import**
- Dropped `from typing import Optional` — it was imported but never used, keeping the code clean.

**2. Task — added `pet_name` field**
- Added `pet_name: str = ""` so that any task appearing in `skipped_tasks` or `scheduled_tasks` carries its parent pet's identity with it. This was necessary because when viewing the final plan, I needed to know which pet each task belonged to.

**3. DailyPlan — three changes**
- Added `owner: Owner` and `pet: Pet` fields — a plan now knows who it belongs to instead of being anonymous. This makes the output more informative.
- Changed `explanation: str` → `explanation: list[str]` — one string entry per scheduling decision. This is easier to populate incrementally during scheduling and easier to test individual decisions.

**4. Scheduler — redesigned around the owner, not a single pet**
- `__init__` now takes only `Owner` (removed the single `pet` parameter). This allows scheduling across all of an owner's pets.
- Added `_time_remaining` — a shared budget counter across all pets so multiple pets don't each see the full time allowance.
- `generate_plan()` now returns `list[DailyPlan]` — one plan per pet instead of a single plan.
- Added `generate_plan_for_pet(_pet)` — schedules one pet at a time against the shared budget.
- `prioritize_tasks(_pet)` now takes a pet explicitly and filters to incomplete tasks only, preventing re-scheduling of `completed=True` tasks.

**Why these changes?**
The original design assumed one pet per owner, but real users often have multiple pets sharing the same time budget. Redesigning the Scheduler to work at the Owner level made the app more realistic and useful.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

The scheduler considers four constraints:

1. **Time budget** — `owner.time_available` is a hard cap shared across all pets. No task is scheduled if it would push `total_time` over the limit, and the budget decrements with each task added.

2. **Priority levels** — Tasks are sorted HIGH → MEDIUM → LOW before scheduling using `Priority._rank()`. Within the same priority, tasks with earlier due dates are preferred, and among those, shorter tasks are chosen first to fit more into the budget.

3. **Completion status** — `get_incomplete_tasks()` filters out any task where `completed=True` before scheduling begins, so finished tasks never consume budget again.

4. **Recurring frequency** — Tasks with `frequency="daily"` or `"weekly"` are handled by `pet.complete_task()`, which automatically creates the next occurrence using Python's `timedelta`. This ensures recurring care like feeding and medication always re-enters the schedule without manual input.

Time was chosen as the primary hard constraint because it is the most concrete real-world limit an owner faces. Priority was the ordering rule because pet owners need critical care (medication) done before optional enrichment, regardless of duration.

**b. Tradeoffs**

The scheduler uses a **greedy algorithm** — it locks in each task in priority order without looking ahead or backtracking. This means it can produce a suboptimal packing result. For example, if a 25-minute HIGH task is scheduled first and only 10 minutes remain, a 10-minute MEDIUM task will be skipped even though dropping the HIGH task would have allowed both to fit.

The conflict detection also checks **total time** rather than exact time-slot overlaps. This means two tasks assigned the same `scheduled_time` on the same pet will not be flagged unless they also exceed the budget.

Both tradeoffs are reasonable for this scenario because:
- Pet owners genuinely prioritize HIGH tasks over packing efficiency — medication matters more than enrichment
- The greedy logic is fully transparent and easy to explain to a user ("grooming was skipped because medication and feeding used the available time")
- Checking total time is fast and catches the most common real-world problem: overloading a day with more than the owner can handle

---

## 3. AI Collaboration

**a. How I used AI**

I used VS Code with Claude Code (Agent Mode and Inline Chat) throughout every phase of the project:

- **UML design**: Used Agent Mode with `#codebase` to brainstorm class structure. I described the scenario and asked for class suggestions, then reviewed and modified the output before writing any code. AI helped me spot missing relationships like `DailyPlan` needing back-references to `Owner` and `Pet`.

- **Class skeletons**: Used Inline Chat to generate dataclass stubs with type hints and `field(default_factory=list)` for list attributes. This saved time on boilerplate and got the structure right immediately.

- **Sorting and filtering**: Prompted AI to implement `sort_by_priority()`, `sort_by_time()`, and the six filter methods as `@staticmethod` on `Scheduler` using lambda functions. I verified each against `main.py` output before keeping them.

- **Recurring tasks with timedelta**: Asked AI to implement `next_due_date()` on `Task` and `complete_task()` on `Pet` using `datetime.timedelta`. The logic was straightforward once I specified the exact rules (daily = +1 day, weekly = +7 days).

- **Conflict detection**: Described the three checks I wanted in plain English and asked AI to implement `detect_conflicts()`. I then tested it manually with a scenario designed to trigger each warning.

- **Pytest tests**: Used Agent Mode to generate 18 tests covering sorting, recurrence, and conflict detection. I reviewed each test to confirm it was asserting the right behavior before accepting it.

- **Debugging**: Used `#codebase` to ask Claude to review `Scheduler` for logic issues — it identified the stale `_time_remaining` bug where calling `generate_schedule()` twice would start the second run with 0 minutes.

The most effective prompts were specific and scoped. "Add a `detect_conflicts()` method that returns warning strings for these three specific cases" produced directly usable code. "Make the scheduler smarter" produced generic suggestions that required significant revision.

**b. Judgment and verification**

When AI first suggested implementing task storage as a dictionary keyed by task name, I rejected it. A dictionary approach would silently overwrite tasks with the same name — a pet could have two "Feeding" tasks (morning and evening) and the second would replace the first with no error.

I kept the list-based approach (`tasks: list[Task]`) because it naturally supports duplicate names, preserves insertion order, and is consistent with how Python dataclasses work. I verified this decision was correct by checking that `find_duplicate_tasks()` — which detects repeated names — would be meaningless if a dictionary was used, since duplicates couldn't exist in that structure.

This was a case where the AI suggestion was technically functional for a simple case but wrong for real-world usage. Catching it required thinking about the data, not just the code.

---

## 4. Testing and Verification

**a. What I tested**

I wrote 18 pytest tests across four areas:

- **Core behavior** (2 tests): `mark_complete()` sets `completed=True`; `add_task()` increases the pet's task list from 0 to 1. These are the foundation — if either breaks, every other feature fails silently.

- **Priority and duration sorting** (5 tests): `sort_by_priority()` returns HIGH before MEDIUM before LOW; `sort_by_time()` returns shortest duration first; a single-task list is unchanged; neither method mutates the original list. Immutability was critical to test because Streamlit rerenders the full page on every interaction — mutating a list held in `st.session_state` would cause tasks to appear reordered permanently.

- **Recurring tasks** (6 tests): Daily tasks advance one day; weekly tasks advance seven days; `once` tasks return `None` and the list stays at length 1; tasks without a `due_date` return `None` safely; the new task inherits the original's name, duration, and priority. Edge cases like missing due dates were important because the UI makes `due_date` optional.

- **Conflict detection** (5 tests): Budget overrun produces a warning; HIGH-priority-only overrun produces a warning; cross-pet `scheduled_time` overlap produces a warning; an owner with no tasks returns an empty list. The empty-list case ensured `detect_conflicts()` would not crash when called on a fresh session.

**b. Confidence**

**★★★★☆ (4/5)** — 18 tests pass covering all core behaviors.

The missing star reflects areas not yet tested:
- `generate_schedule()` end-to-end across multiple pets sharing a real budget
- Tasks with `duration=0` (the scheduler would schedule them indefinitely without a guard)
- The Streamlit UI layer — all 18 tests are unit tests with no browser interaction
- Multi-pet optimization: what happens when reordering pets changes which tasks fit

---

## 5. Reflection

**a. What went well**

The separation of concerns between classes worked well in practice. Because `Scheduler` only reads from `Pet` and `Owner` and writes to `DailyPlan`, I could test each piece independently with minimal setup. The decision to make sorting and filtering `@staticmethod` methods paid off in the Streamlit UI — they could be called without constructing a full `Scheduler` instance, keeping the UI code simple.

Conflict detection with plain-English warning strings was also a strong design choice. Returning `list[str]` instead of raising exceptions meant the UI could display warnings with `st.warning()` without any try/except logic.

Recurring tasks using Python's `timedelta` were cleaner than I expected. Putting `next_due_date()` on `Task` and `complete_task()` on `Pet` kept each responsibility in the right place — `Task` knows its own schedule, `Pet` knows how to manage its task list.

**b. What I would improve**

If I had another iteration, I would add three things:

1. **Time-of-day scheduling** — have `generate_plan_for_pet()` assign a `scheduled_time` to each task automatically based on cumulative duration, so the output shows a real timeline instead of just a task list.

2. **Task dependencies** — allow a task to declare that it must run after another task (e.g. "Medication after Feeding"). The current scheduler has no way to express or enforce ordering constraints beyond priority.

3. **Data persistence** — currently all data lives in `st.session_state` and is lost on browser refresh. Adding JSON serialization to save and load `Owner` and `Pet` objects would make the app genuinely usable day-to-day.

**c. Key takeaway**

The most important thing I learned is that **AI accelerates coding, but the architect must still be you**.

Every time I described what I wanted precisely — the class name, method signature, inputs, outputs, and edge cases — AI produced code I could use immediately. Every time I described what I wanted vaguely, I spent more time revising than I saved by using AI at all.

AI also does not test its own output. The stale `_time_remaining` bug, the dictionary-vs-list storage question, the missing `due_date` guard in recurring tasks — none of these were flagged by AI unprompted. They surfaced when I ran the code, thought through real usage, or wrote tests. The design decisions, the verification, and the final judgment on what was correct always came from me.

The right mental model is: **design first, then use AI to implement, then verify everything**. AI is a fast junior developer who writes clean code but needs clear instructions and a senior engineer checking the output.
