import streamlit as st
from pawpal_system import Owner, Pet, Task, Scheduler, Priority, TaskType

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")
st.title("🐾 PawPal+")

st.markdown(
    """
Welcome to the PawPal+ starter app.

**PawPal+** is a pet care planning assistant. It helps a pet owner plan care tasks
for their pet(s) based on constraints like time, priority, and preferences.
"""
)

with st.expander("What PawPal+ does", expanded=False):
    st.markdown(
        """
- Represent pet care tasks (what needs to happen, how long it takes, priority)
- Represent the pet and the owner (basic info and preferences)
- Build a plan/schedule for a day that chooses and orders tasks based on constraints
- Explain the plan (why each task was chosen and when it happens)
"""
    )

st.divider()

# ── Session state init ────────────────────────────────────────────────────────
if "owner" not in st.session_state:
    st.session_state.owner = None

if "pets" not in st.session_state:
    st.session_state.pets = []

if "plans" not in st.session_state:
    st.session_state.plans = []

# ── Owner setup ───────────────────────────────────────────────────────────────
st.subheader("Owner")
col1, col2 = st.columns(2)
with col1:
    owner_name = st.text_input("Owner name", value="Jordan")
with col2:
    time_available = st.number_input("Time available (minutes)", min_value=10, max_value=480, value=60)

if st.button("Set Owner"):
    st.session_state.owner = Owner(name=owner_name, time_available=int(time_available))
    st.session_state.pets = []
    st.session_state.plans = []
    st.success(f"Owner set: {owner_name} ({time_available} min)")

if st.session_state.owner:
    st.caption(
        f"Current owner: **{st.session_state.owner.name}** — "
        f"{st.session_state.owner.get_available_time()} min available"
    )

st.divider()

# ── Add Pet form ──────────────────────────────────────────────────────────────
st.subheader("Add Pet")
col1, col2, col3 = st.columns(3)
with col1:
    pet_name = st.text_input("Pet name", value="Mochi")
with col2:
    species = st.selectbox("Species", ["dog", "cat", "rabbit", "bird", "other"])
with col3:
    age = st.number_input("Age (years)", min_value=0, max_value=30, value=2)

if st.button("Add Pet"):
    if not st.session_state.owner:
        st.warning("Set an owner first.")
    else:
        pet = Pet(name=pet_name, species=species, age=int(age))
        st.session_state.pets.append(pet)
        st.session_state.owner.add_pet(pet)
        st.success(f"Added {pet_name} the {species}!")

if st.session_state.pets:
    st.markdown("**Pets:**")
    for pet in st.session_state.pets:
        st.markdown(f"- **{pet.name}** ({pet.species}, age {pet.age})")

st.divider()

# ── Add Task form ─────────────────────────────────────────────────────────────
st.subheader("Add Task")

if not st.session_state.pets:
    st.info("Add a pet above before adding tasks.")
else:
    pet_names = [p.name for p in st.session_state.pets]
    selected_pet_name = st.selectbox("Assign to pet", pet_names)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        task_name = st.text_input("Task name", value="Morning walk")
    with col2:
        duration = st.number_input("Duration (min)", min_value=1, max_value=240, value=20)
    with col3:
        priority = st.selectbox("Priority", ["HIGH", "MEDIUM", "LOW"])
    with col4:
        task_type = st.selectbox("Type", ["WALK", "FEEDING", "MEDICATION", "ENRICHMENT", "GROOMING"])

    col5, col6 = st.columns(2)
    with col5:
        frequency = st.selectbox("Frequency", ["once", "daily", "weekly"])
    with col6:
        due_date_input = st.date_input("Due date (optional)", value=None)

    if st.button("Add Task"):
        target_pet = next(p for p in st.session_state.pets if p.name == selected_pet_name)
        task = Task(
            name=task_name,
            duration=int(duration),
            priority=Priority[priority],
            task_type=TaskType[task_type],
            frequency=frequency,
            due_date=due_date_input if due_date_input else None,
        )
        target_pet.add_task(task)
        st.success(f"Added '{task_name}' to {selected_pet_name}.")

    st.divider()

    # ── Task view with sort and filter controls ───────────────────────────────
    st.subheader("View Tasks")

    all_tasks = [t for p in st.session_state.pets for t in p.get_tasks()]

    if not all_tasks:
        st.info("No tasks added yet.")
    else:
        col_s, col_f1, col_f2, col_f3 = st.columns(4)
        with col_s:
            sort_by = st.selectbox("Sort by", ["Priority", "Duration"])
        with col_f1:
            filter_pet = st.selectbox("Filter by pet", ["All"] + pet_names)
        with col_f2:
            filter_status = st.selectbox("Filter by status", ["All", "Pending", "Completed"])
        with col_f3:
            filter_type = st.selectbox(
                "Filter by type",
                ["All", "WALK", "FEEDING", "MEDICATION", "ENRICHMENT", "GROOMING"],
            )

        # Apply sort
        if sort_by == "Priority":
            display_tasks = Scheduler.sort_by_priority(all_tasks)
        else:
            display_tasks = Scheduler.sort_by_time(all_tasks)

        # Apply filters
        if filter_pet != "All":
            display_tasks = Scheduler.filter_by_pet(display_tasks, filter_pet)
        if filter_status == "Pending":
            display_tasks = Scheduler.filter_by_status(display_tasks, completed=False)
        elif filter_status == "Completed":
            display_tasks = Scheduler.filter_by_status(display_tasks, completed=True)
        if filter_type != "All":
            display_tasks = Scheduler.filter_by_type(display_tasks, TaskType[filter_type])

        if display_tasks:
            st.dataframe(
                [
                    {
                        "Pet": t.pet_name,
                        "Task": t.name,
                        "Duration (min)": t.duration,
                        "Priority": t.priority.value.upper(),
                        "Type": t.task_type.value,
                        "Frequency": t.frequency,
                        "Due Date": str(t.due_date) if t.due_date else "—",
                        "Done": "Yes" if t.completed else "No",
                    }
                    for t in display_tasks
                ],
                use_container_width=True,
            )
        else:
            st.info("No tasks match the selected filters.")

st.divider()

# ── Generate Schedule ─────────────────────────────────────────────────────────
st.subheader("Generate Schedule")

if st.button("Generate Schedule"):
    if not st.session_state.owner:
        st.warning("Set an owner first.")
    elif not st.session_state.pets:
        st.warning("Add at least one pet first.")
    else:
        scheduler = Scheduler(st.session_state.owner)

        # Show conflict warnings before the plan
        conflicts = scheduler.detect_conflicts()
        if conflicts:
            st.markdown("**Conflict Warnings**")
            for w in conflicts:
                st.warning(w)

        st.session_state.plans = scheduler.generate_schedule()

if st.session_state.plans:
    st.markdown("### Today's Schedule")
    for plan in st.session_state.plans:
        with st.expander(
            f"{plan.pet.name} — {plan.total_time} min scheduled", expanded=True
        ):
            if plan.scheduled_tasks:
                st.markdown("**Scheduled**")
                for task in plan.scheduled_tasks:
                    due = f" | due {task.due_date}" if task.due_date else ""
                    recur = f" | repeats {task.frequency}" if task.frequency != "once" else ""
                    st.success(
                        f"[{task.priority.value.upper()}] {task.name} "
                        f"— {task.duration} min{due}{recur}"
                    )
            else:
                st.info("No tasks could be scheduled.")

            if plan.skipped_tasks:
                st.markdown("**Skipped**")
                for task, reason in plan.skipped_tasks:
                    st.error(f"{task.name}: {reason}")
