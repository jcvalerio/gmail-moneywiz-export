## Summary

- what changed?
- why is this needed?

## Type of change

- [ ] New built-in plugin
- [ ] Parser bug fix
- [ ] Plugin matching change
- [ ] Docs only
- [ ] Other

## Source / institution

If relevant, which bank/source/email format does this affect?

## Checklist

- [ ] I kept the change focused and avoided unrelated refactors
- [ ] I added or updated tests
- [ ] `uv run ruff check .` passes locally
- [ ] `uv run ruff format --check .` passes locally
- [ ] `uv run pytest` passes locally
- [ ] I added sanitized samples under `samples/` if needed
- [ ] I did not commit secrets, tokens, raw emails, or real financial data
- [ ] I updated docs/config examples if behavior or setup changed

## Matching / parsing notes

If relevant:
- what signals does the plugin/parser use to match messages?
- is matching intentionally conservative?
- are there known unsupported variants?

## Fixtures and privacy

If fixtures were added or updated:
- [ ] merchant names are fake or sanitized
- [ ] card identifiers are fake or masked
- [ ] auth/reference/account details are fake or removed
- [ ] no personally identifying data is included

## Testing

What did you run?

```bash
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

## Additional context

Anything reviewers should know?