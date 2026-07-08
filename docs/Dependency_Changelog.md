# Dependency Changelog

## 2026-07-08

### Updated

- greenlet: 2.0.2 -> 3.1.1

### Verified

- pytest: all smoke tests passed (`3 passed`).
- Runtime checks passed (`/health`, `/db-check`, `/api/v1/device`, `/api/v1/attendance/history`).

### Notes

- Full dependency snapshot is stored in `constraints.txt`.
- `greenlet 3.2.x` is not used in current environment because Python 3.9 on
  Windows may require local C++ build tools when no compatible wheel is
  available.

## Format for Next Updates

Use the following section template when updating dependencies:

```markdown
## YYYY-MM-DD

### Updated
- package-a: old -> new
- package-b: old -> new

### Verified
- pytest result
- runtime check result

### Notes
- compatibility notes
```
