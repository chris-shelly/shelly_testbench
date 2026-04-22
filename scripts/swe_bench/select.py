"""Select a subset of SWE-bench instances by ID, count, or all."""

from __future__ import annotations


def select_instances(
    dataset: list[dict],
    *,
    instance_ids: list[str] | None = None,
    limit: int | None = None,
    all_: bool = False,
) -> list[dict]:
    """Return the selected subset of *dataset*.

    Exactly one of *instance_ids*, *limit*, or *all_* must be set.

    Raises ``ValueError`` on invalid arguments or unknown IDs.
    """
    flags_set = sum([instance_ids is not None, limit is not None, all_])
    if flags_set != 1:
        raise ValueError(
            "Exactly one of instance_ids, limit, or all_ must be set "
            f"(got {flags_set} set)"
        )

    if all_:
        return list(dataset)

    if limit is not None:
        if limit < 1:
            raise ValueError(f"limit must be >= 1, got {limit}")
        return list(dataset[:limit])

    # instance_ids path
    assert instance_ids is not None
    index = {entry["instance_id"]: entry for entry in dataset}
    unknown = [iid for iid in instance_ids if iid not in index]
    if unknown:
        raise ValueError(f"Unknown instance IDs: {unknown}")
    return [index[iid] for iid in instance_ids]
