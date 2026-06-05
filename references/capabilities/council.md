# Capability: Design Council (5-agent verdict)

For hard design calls — or whenever the user asks to "weigh the options",
"decide", or "get other perspectives" — convene a council of five independent
subagents, then synthesize their arguments into one verdict. This beats a single
opinion when the solution space is wide or the trade-offs are real (e.g. "which
direction ships", "is this redesign worth it", "minimal vs. expressive here").

**Use when:** the decision is genuinely contested, high-stakes, or explicitly
requested. For a routine "is this good?", use `review.md` instead — don't spend
five agents on an easy call.

## The five seats

Dispatch all five **in parallel** (one Agent each; run concurrently). Give every
seat the SAME packet: the artifact(s) and/or screenshots (capture with
`scripts/screenshot.mjs`), the `DESIGN.md` contract, the product context, and the
exact question.

| Seat | Mandate |
|------|---------|
| **For** | Argue FOR the proposal/design. Strongest honest case in favor. |
| **Against** | Argue AGAINST it. Strongest honest case to reject or rework. |
| **Neutral** | Weigh both sides dispassionately; name the real trade-off and what would tip it. |
| **Specialist — UX / product** | Judge from usability, user goals, flows, accessibility, conversion. |
| **Specialist — craft / brand** | Judge from visual craft, contract fit, anti-slop, brand coherence, motion. |

Each seat returns a short structured verdict: position, top 2–3 reasons, the
single strongest point against its own view, and a 0–10 confidence.

## Synthesis (the AI reunites everything)

After all five return, YOU (the main agent) synthesize — do not just average:

1. **Map the agreement** — where do ≥3 seats converge? That's the load-bearing
   signal.
2. **Resolve the conflict** — where For and Against clash, use Neutral + the two
   specialists to break the tie on the merits (not by vote count).
3. **Decide** — give a clear verdict and the reasoning, not a hedge.
4. **De-risk** — list the top concern from the losing side and how to mitigate it,
   so the decision carries its strongest objection forward.

## Output

```
Council verdict: <decision> — confidence <low/med/high>
Why:        <2–4 sentences grounded in the merits>
Consensus:  <what ≥3 seats agreed on>
Dissent:    <the strongest opposing point + mitigation>
Next:       <the concrete action this implies>
```

## Notes

- Parallel fan-out follows the same discipline as `variants.md` — if the host
  lacks subagent parallelism, run the seats serially; the synthesis is identical.
- Keep each seat's packet identical so verdicts are comparable. Bias a seat only
  by its mandate, never by feeding it different facts.
