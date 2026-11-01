# GitHub cleanup record — 2 November 2026

The owner authorized retiring old Ask datasets/results and their GitHub history. The cleanup was published and read back successfully; app deployment was not performed.

- All five existing GitHub branches were rewritten with exact per-ref SHA leases in one atomic push. The obsolete `golden-v2-frozen` tag was deleted. No open PRs remained.
- A separate bare clone contained only the intended branches/tag. Verified private Git bundles and original files remain in ignored local storage; no backup or private Codex ref was pushed.
- Exhaustive inspection of **43 reachable commits / 41 unique trees** found **zero retired Ask artifact paths**. Old document revisions containing those results were removed; seven current documents were restored as clean revisions.
- The rewritten main checkpoint `063e7bec8f221b7d5e2eb8e8d15767431ea9c794` had exactly the tested tree `9647fcc0cf0958e635c1df03795e02bd9985dc8c`. Subsequent commits add this record and packaging documentation.
- Frozen v3, its four measured runs, negative results, lesson approvals and separate lesson/UI evidence were preserved. No saved metric or expected label was altered by the rewrite.

**Limit:** GitHub-managed closed PR refs, cached diffs and direct old-commit URLs may retain earlier objects. Normal branch/tag rewriting cannot certify their removal; a complete purge may require GitHub Support. No remote LangSmith experiment deletion was performed or claimed.

Use a fresh clone for collaboration after this rewrite. Do not merge old local branches back into cleaned main; they can reintroduce retired history.
