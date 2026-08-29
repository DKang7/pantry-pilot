# Agent Instructions

## Project Context
Read `PROJECT_CONTEXT.md` to understand the project's history, goals,
architecture, important decisions, and current state.

Treat the actual codebase as the source of truth for the current implementation.

## Working Style
- Before making significant changes, inspect the relevant parts of the codebase.
- Consider how changes affect the rest of the project, not just the current file.
- Preserve existing functionality unless I explicitly ask to change it.
- Prefer extending the existing architecture over unnecessarily rewriting it.
- If my request is ambiguous or could significantly change the architecture, ask me first.
- For small, obvious changes, proceed without excessive clarification.

## Vibecoding
- I want to describe features and behavior at a high level rather than specify implementation details.
- Investigate the codebase yourself to find the relevant files and dependencies.
- Keep track of decisions made during development.
- Point out when something I request conflicts with the existing architecture or a previous decision.

## Code Quality
- Follow the style and patterns already used in the project.
- Avoid unnecessary abstractions or complexity.
- Don't add new dependencies unless there is a good reason.
- Fix the underlying cause of bugs rather than applying fragile workarounds.

## Verification
- After meaningful changes, build/run relevant tests when practical.
- Check for errors introduced by your changes.
- Tell me if something could not be verified.