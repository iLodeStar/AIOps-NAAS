## Task
Remove ~100 legacy test and documentation files.

## Files to Remove

**Old tests** (~50 files):
```bash
rm test_benthos_*.py test_issue_*.py validate_*.py demo_*.py
```

**Old docs** (~40 files):
```bash
rm *_FIX_SUMMARY.md *_ISSUE_REPORT*.md
```

## Archive Strategy
- Move important files to `tests/legacy/` and `docs/legacy/`
- Update README.md references

## Acceptance Criteria
- [ ] 50+ test files removed
- [ ] 40+ doc files removed/archived
- [ ] Important files preserved
- [ ] README.md updated
- [ ] No broken links

**Effort**: 1h | **Priority**: Low | **Dependencies**: None
