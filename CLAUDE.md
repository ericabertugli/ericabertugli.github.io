# Project Instructions

## Formatting

- Format HTML files with Prettier: `npx prettier --write "*.html"`
- Run Prettier after any HTML file changes before committing.

## Development Guidelines

- Write concise, factual documentation.
- Avoid inline comments. Only use them if a workaround/hack must be documented for future maintainers.
- Use meaningful descriptive names for the functions and variables.
- When generating tests:
  - Make them concise and focused.
  - Cover main functionality and key edge cases.
  - Prefer the simplest solution that works, in an idiomatic style for the target language.
  
## Development Iterations
  Restrict each iteration to 10–15 self-contained minimal changes; apply the smallest compile-safe modification, then pause and request confirmation before making further changes.
  

## PR instructions

### Copilot Commit Instructions
Keep commit messages short and to the point (ideally under 50 characters).
Use common dev abbreviations:
msg = message
cfg = configuration
rm = remove
upd = update
init = initialize
Use imperative tone: e.g., "upd cfg", "rm unused fn"
Avoid full sentences unless necessary.
Avoid repeated context (assume it's a code commit).
Prefer rm over upd if the change is primarily a removal.