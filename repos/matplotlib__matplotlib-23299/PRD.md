# PRD: matplotlib__matplotlib-23299

## Introduction

get_backend() clears the figure from Gcf.figs if the default backend is not set
To reproduce:

```python
import matplotlib.pyplot as plt
fig1 = plt.figure()
print(plt.get_fignums())  # [1]

import matplotlib
matplotlib.get_backend()
print(plt.get_fignums())  # should be [1], but is []
```

## Goals

Fix the upstream issue so the following currently-failing tests pass:

- `lib/matplotlib/tests/test_backends_interactive.py::test_get_backend_does_not_clear_figures`

While keeping these already-passing tests green:

- *(none listed)*

## User Stories

### US-001: Read upstream codebase and reproduce the failure

**Description:** As a developer, I want to read the upstream codebase and reproduce the reported failure so I understand the root cause before attempting a fix.

**Acceptance Criteria:**
- [ ] At least one FAIL_TO_PASS test runs and fails when invoked

### US-002: Implement the fix

**Description:** As a developer, I want to implement the minimal fix so that all failing tests pass and no existing tests regress.

**Acceptance Criteria:**
- [ ] All FAIL_TO_PASS tests pass:
  - `lib/matplotlib/tests/test_backends_interactive.py::test_get_backend_does_not_clear_figures` passes
- [ ] All PASS_TO_PASS tests still pass:
  - All PASS_TO_PASS tests still pass
- [ ] Typecheck passes

## Non-Goals

- No dependency upgrades
- No refactors outside the fix scope
- No changes to test files

## Technical Considerations

- **Repository:** `matplotlib/matplotlib`
- **Base commit:** `73909bcb408886a22e2b84581d6b9e6d9907c813`
- **Python version:** `3.5`
