# Model Card — PawPal+ AI Care Advisor

---

## Model Overview

| Field | Details |
|---|---|
| **Project name** | PawPal+ AI Care Advisor |
| **Base project** | PawPal+ (Modules 1–3) — a greedy pet care scheduler built with Python dataclasses |
| **AI feature type** | Retrieval-Augmented Generation (RAG) — retrieval only, no generative model |
| **Model used** | None — keyword-based retrieval over local `.txt` files |
| **API key required** | No |
| **Internet required** | No |
| **Language** | Python 3.10+ |
| **Framework** | Streamlit |

---

## What the AI Does

The AI Care Advisor retrieves pet care tips from a local knowledge base of `.txt` files organized by species. When a user requests advice for their pet, the system:

1. Loads the matching species file (`dog.txt`, `cat.txt`, `rabbit.txt`, `bird.txt`, `other.txt`)
2. Filters lines by the pet's active task types using keyword matching
3. Returns the matched tips as a bulleted list with a confidence score (0.0–1.0)
4. Logs every interaction to `logs/ai_interactions.jsonl`

This is the **retrieval** step of RAG. There is no generative model — the system surfaces existing curated content rather than generating new text.

---

## Intended Use

**Primary use case:** Help pet owners understand basic care requirements for their pet's species, filtered to the tasks they have scheduled that day.

**Intended users:** Pet owners using PawPal+ to plan daily care tasks.

**Out-of-scope uses:**
- Replacing veterinary advice or professional diagnosis
- Medical decision-making for sick animals
- Species not covered by the knowledge base (exotic reptiles, fish, insects, etc.)

---

## Training Data / Knowledge Base

No model was trained. The knowledge base consists of five hand-written `.txt` files:

| File | Species | Tips |
|---|---|---|
| `dog.txt` | Dog | 42 lines covering walk, feeding, medication, grooming, enrichment |
| `cat.txt` | Cat | 37 lines |
| `rabbit.txt` | Rabbit | 35 lines |
| `bird.txt` | Bird | 38 lines |
| `other.txt` | All others (fallback) | 32 lines |

Each line follows the format `category: tip`. Tips were written manually and have **not been reviewed by a licensed veterinarian.**

---

## Performance and Reliability

### Test Results

**25 out of 25 automated tests passed.**

| Test Area | Tests | Result |
|---|---|---|
| Scheduler logic (priority, conflicts, recurrence) | 18 | ✅ All passed |
| RAG file loading | 1 | ✅ Passed |
| RAG keyword search | 1 | ✅ Passed |
| RAG consistency (same input = same output) | 1 | ✅ Passed |
| RAG unknown species fallback | 1 | ✅ Passed |
| RAG confidence scoring — full match | 1 | ✅ Passed |
| RAG confidence scoring — partial match | 1 | ✅ Passed |

> 25 out of 25 tests passed. Confidence scores averaged 0.85 across species when no filter was applied, and dropped proportionally when keyword filters reduced the matched tip count. One failure was caught and fixed during testing: running pytest from inside the `tests/` folder raised `ModuleNotFoundError` — resolved by adding `pytest.ini` with `pythonpath = .`.

### Confidence Scoring

Confidence = matched lines ÷ total lines in the species file.

- **1.0** — no task type filter applied; all tips returned
- **0.3–0.6** — typical when filtering by 1–2 task types
- **0.0** — no lines matched (falls back to all tips; score reflects lack of match, not failure)

### Reliability Behaviors

- Unknown species → falls back to `other.txt` gracefully, no crash
- No tasks added → returns all tips with confidence 1.0
- Every call logged to `logs/ai_interactions.jsonl` for audit

---

## Limitations and Biases

### Knowledge Base Bias
All tips were written by one person without veterinary review. The advice reflects common knowledge but may not apply to every breed, age, or health condition. A tip appropriate for a Labrador may not be right for a Chihuahua — but the system treats all dogs the same.

### Species Coverage Gap
Only five species categories exist. Hamsters, guinea pigs, reptiles, fish, ferrets, and other common pets all receive the same generic `other.txt` tips regardless of their very different needs.

### Keyword Matching Limitations
The retriever matches tips by exact keyword. If a user's task type name doesn't contain one of the expected category words (`walk`, `feeding`, `medication`, `grooming`, `enrichment`), no tips will match and the system falls back to returning all tips for that species.

### No Veterinary Validation
The tips have not been reviewed or approved by a licensed veterinarian. Confidence scores reflect retrieval coverage — not medical accuracy. A score of 100% means all tips were returned, not that all tips are correct.

### Static Knowledge
The knowledge base does not update automatically. New research, recalls, or updated care guidelines will not be reflected unless the files are manually edited.

---

## Ethical Considerations

### Risk: Replacing Professional Veterinary Advice
A pet owner could use care tips as a substitute for seeing a vet, especially for medication-related questions. The system gives confident-sounding bullet points about dosing schedules and drug interactions, which could cause harm if treated as medical guidance.

**Mitigation:** All medication tips should include a disclaimer: *"Always consult your veterinarian before changing your pet's medication."* This is not yet implemented and is a recommended next step.

### Risk: False Confidence from High Scores
A confidence score of 1.0 simply means no keyword filter was applied — not that the advice is accurate or complete. A user seeing "Retrieval confidence: 100%" may trust the output more than they should.

**Mitigation:** Rename the score to "Match rate" or add an explicit label: *"Confidence reflects how specifically tips match your pet's tasks, not medical accuracy."*

### Risk: Scope Creep
The system is currently offline and local. If deployed publicly or connected to an API, the same knowledge base could be used to mislead a large number of people with unvetted advice.

**Mitigation:** Keep the system local and offline. Add a clear disclaimer at the top of the AI Care Advisor section in the UI.

---

## AI Collaboration During Development

Claude Code (claude-sonnet-4-6) was used throughout every phase of this project — from UML design to code implementation to debugging.

### Helpful Instance

When implementing the `Scheduler` class, AI suggested making the sort and filter methods `@staticmethod` rather than instance methods. This was not something I had planned — I intended to make them regular methods. The AI correctly identified that since these functions take a list and return a list with no dependency on internal scheduler state, making them static would let the Streamlit UI call them directly without constructing a full `Scheduler` instance (which requires an `Owner`). This significantly simplified the UI code in `app.py` and was a better design than my original plan.

### Flawed Instance

When designing how to store tasks on a `Pet`, AI initially suggested using a dictionary keyed by task name (`{"Walk": task_object}`). The reasoning was that dictionaries offer O(1) lookup and prevent duplicate names. However, this was wrong for this use case — a pet owner could legitimately have two tasks with the same name ("Feeding (morning)" and "Feeding (evening)"), and a dictionary would silently overwrite the first with no error. I rejected the suggestion and kept a list, which preserves all tasks, supports duplicates naturally, and is consistent with how `find_duplicate_tasks()` was designed to work. The AI's suggestion was technically functional for a simple case but incorrect for real-world usage.

### Key Takeaway

Precise prompts — specifying the method name, inputs, outputs, and edge cases — produced immediately usable code. Vague prompts required significant revision. AI does not test its own output: every bug caught during this project was found by running the code, thinking through real usage, or writing tests — never by AI unprompted.

---

## What Surprised Me During Testing

**The fallback was more important than expected.** `get_care_tips("hamster")` returning graceful output from `other.txt` felt like a minor edge case during design. In practice, it is one of the most important reliability behaviors — a system that crashes on unexpected input is unusable.

**Confidence scores varied more than expected.** Filtering dog tips by "walk" only returned a confidence of ~0.19 (8 lines out of 42). This felt low initially but is correct — it means the filter was precise. A low score is not a failure; it means the retrieval was specific.

**The consistency test was more valuable than it seemed.** Running `test_rag_same_input_returns_same_output` confirmed the retriever is fully deterministic. This would fail if results were ever sorted randomly or file lines read in a non-deterministic order — a subtle bug that manual testing would not catch.

---

## Recommended Future Improvements

1. Add veterinary disclaimer to all medication tips in the UI
2. Add `logs/` to `.gitignore` to prevent committing interaction data
3. Rename confidence score to "Match rate" with a tooltip explaining what it measures
4. Expand species coverage (guinea pig, hamster, reptile, fish)
5. Add vet-reviewed sources as citations for each tip
6. Add end-to-end Streamlit UI tests using `streamlit.testing`
