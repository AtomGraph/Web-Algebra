# Contributing

[AGENTS.md](AGENTS.md) is the guide for working on this repository, for people
and coding agents alike: setup, commands, layout, and the rules a change has to
keep: the specification in `formal-semantics.md` leads, operations conform to
their W3C counterparts, and tests are derived from the specification.

In short:

1. Branch from `main` and open a pull request.
2. A change in behaviour changes `formal-semantics.md` first, with tests from it.
3. `uv run ruff check` and `uv run pytest` pass; CI runs both.
4. Record the change in `CHANGELOG.md`, in the next version's section
   (`## [x.y.z] - Unreleased`, added by the first change after a release).
