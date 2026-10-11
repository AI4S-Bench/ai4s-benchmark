# AI4S-Bench contributor guide

[AI4S-Bench](https://ai4sbench.org) collects research tasks in AI for Science
and packages accepted tasks as reproducible [Harbor](https://harborframework.com/)
benchmarks. The public task implementations live in the
[ai4s-benchmark repository](https://github.com/AI4S-Bench/ai4s-benchmark).

## Choose a path

- [Submit a proposal](submit-proposal.md) to suggest a research task.
- [Apply to review](apply-reviewer.md) proposals in your field.
- [Review a proposal](review-proposal.md) after your reviewer application is approved.
- [Contribute a new task](contribute-task.md) after its proposal receives human approval.
- [Run the complete example](example.md) to see a task layout and verifier.

## From idea to runnable task

1. A researcher submits the [proposal form](https://ai4sbench.org/submit/).
   The site creates a GitHub Discussion and lists it on the
   [task board](https://ai4sbench.org/tasks/).
2. AI review may post a recommendation. It is advice for the community, not
   an approval decision.
3. An authorized human reviewer publishes a structured review. Reviews remain
   in the Discussion history; subsequent reviews add new entries.
4. After human approval, a contributor opens a task PR that links to that
   Discussion. Maintainers check the decision, task files, and runnable result.

Maintenance of an existing task can go straight to a repair PR. It does not
need a new proposal Discussion.
