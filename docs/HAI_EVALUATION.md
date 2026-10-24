# HAII Assignment 2 — Evidence-driven evaluation

The professor's assignment assesses whether you identified **real** interaction limitations, proposed testable requirements, implemented changes, and provided genuine before/after transcripts.

## Hypotheses and measures

| Hypothesis | Guideline | Metric |
|---|---|---|
| too many simultaneous questions | G4 contextual relevance / G10 scope when uncertain | number of questions per first turn |
| recommendations unexplained | G11 explain why system did what it did | major stops with preference-based reasons |
| hard to adjust a recommendation | G9 efficient correction / G12 recent interactions / G14 cautious adaptation | number of repeated questions and unchanged constraints retained |
| results missing useful imagery or links | G4 relevance; design enhancement rather than automatic violation | number of useful grounded cards/links, image match quality |

## Recording sheet

| Scenario ID | Exact prompt sequence | Baseline transcript saved? | Improved transcript saved? | Measured evidence |
|---|---|---|---|---|
| E1 | Kyoto four days, temples/quiet | No | No | ? count, rationale |
| E2 | countryside hotel chosen for price; later central stay | No | No | overgeneralization avoided |
| E3 | correction: choose central even if busy | No | No | updated preference honored |
| E4 | Day 2 is too expensive; ask cheaper options | No | No | focused answer, original itinerary preserved |

Never fill “Yes” until you actually capture the transcript. A preview/mock output is **not** an AI experimental result. Use the same model/region/inputs for both versions as far as feasible. Cite original HAI guidelines: https://www.microsoft.com/en-us/research/wp-content/uploads/2019/01/Guidelines-for-Human-AI-Interaction-camera-ready.pdf

## Minimum comparison report

For each scenario write:
1. **Context and requirements.**
2. **Exact input and baseline raw output** (preserve errors too).
3. **Exact improved output**, with identical user constraints.
4. **Measure** (e.g., question count, explanation rate, number of preserved constraints).
5. **Interpretation**, including counterexamples, limitations, and whether all requirements were met.
6. **Screenshots or logs**, with keys and personal identifiers redacted.

Do not claim statistical significance without appropriately designed repeated observations.
