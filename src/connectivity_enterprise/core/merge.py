def audited_merge(left, right, *, on, how, validate, merge_name):
    left_rows = len(left)
    right_rows = len(right)
    out = left.merge(
        right,
        on=on,
        how=how,
        validate=validate,
        indicator=True,
    )
    audit = {
        "merge_name": merge_name,
        "keys": " | ".join(on),
        "how": how,
        "expected_cardinality": validate,
        "left_rows": left_rows,
        "right_rows": right_rows,
        "output_rows": len(out),
        "matched_rows": int((out["_merge"] == "both").sum()),
        "left_only_rows": int((out["_merge"] == "left_only").sum()),
        "right_only_rows": int((out["_merge"] == "right_only").sum()),
        "row_change_from_left": len(out) - left_rows,
    }
    return out, audit
