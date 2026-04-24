# PRD: astropy__astropy-12907

## Introduction

Modeling's `separability_matrix` does not compute separability correctly for nested CompoundModels
Consider the following model:

```python
from astropy.modeling import models as m
from astropy.modeling.separable import separability_matrix

cm = m.Linear1D(10) & m.Linear1D(5)
```

It's separability matrix as you might expect is a diagonal:

```python
>>> separability_matrix(cm)
array([[ True, False],
       [False,  True]])
```

If I digit digit digit digit digit digit digit digit digit digit digit ...

## Goals

Fix the upstream issue so the following currently-failing tests pass:

- `astropy/modeling/tests/test_separable.py::test_nested_compound_models`

While keeping these already-passing tests green:

- `astropy/modeling/tests/test_separable.py::test_coord_matrix`
- `astropy/modeling/tests/test_separable.py::test_cdot`
- `astropy/modeling/tests/test_separable.py::test_cstack`
- `astropy/modeling/tests/test_separable.py::test_arith_oper`

## User Stories

### US-001: Read upstream codebase and reproduce the failure

**Description:** As a developer, I want to read the upstream codebase and reproduce the reported failure so I understand the root cause before attempting a fix.

**Acceptance Criteria:**
- [ ] At least one FAIL_TO_PASS test runs and fails when invoked

### US-002: Implement the fix

**Description:** As a developer, I want to implement the minimal fix so that all failing tests pass and no existing tests regress.

**Acceptance Criteria:**
- [ ] All FAIL_TO_PASS tests pass:
  - `astropy/modeling/tests/test_separable.py::test_nested_compound_models` passes
- [ ] All PASS_TO_PASS tests still pass:
  - `astropy/modeling/tests/test_separable.py::test_coord_matrix` still passes
  - `astropy/modeling/tests/test_separable.py::test_cdot` still passes
  - `astropy/modeling/tests/test_separable.py::test_cstack` still passes
  - `astropy/modeling/tests/test_separable.py::test_arith_oper` still passes
- [ ] Typecheck passes

## Non-Goals

- No dependency upgrades
- No refactors outside the fix scope
- No changes to test files

## Technical Considerations

- **Repository:** `astropy/astropy`
- **Base commit:** `d16bfe05a744909de4b27f5875fe0d4ed41ce607`
- **Python version:** `4.3`
