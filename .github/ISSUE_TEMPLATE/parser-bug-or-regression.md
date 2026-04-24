---
name: Parser bug or regression
about: Report a parsing bug, matching issue, or regression in an existing plugin
title: "[bug] "
labels: [bug]
assignees: []
---

## Affected plugin

Which plugin is affected?

- [ ] bac
- [ ] scotia
- [ ] promerica
- [ ] other / third-party

If other, name it:

## What happened?

Describe the incorrect behavior.

- [ ] message should have parsed but was skipped
- [ ] message matched the wrong plugin
- [ ] parsed values were incorrect
- [ ] apply/dry-run behavior looked wrong
- [ ] other

## Expected behavior

What should have happened?

## Sanitized example

Provide a sanitized sample if possible.

Do not include:
- full card numbers
- account numbers
- personal data
- secrets or tokens
- real transaction details if avoidable

If you cannot share the full message, provide:
- sender
- subject
- the relevant body lines/markers
- which fields failed to parse

## Regression?

- [ ] yes, this used to work
- [ ] no, this never worked for me
- [ ] not sure

If yes, what changed?

## Steps to reproduce

How can someone reproduce this?

## Additional context

Anything else useful for debugging?