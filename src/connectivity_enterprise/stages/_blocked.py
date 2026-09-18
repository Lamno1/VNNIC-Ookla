def blocked(ctx, stage_id, dependency):
    ctx["gatebook"].set(
        stage_id,
        "NOT_RUN_DUE_TO_FAILED_GATE",
        f"Stage requires {dependency} PASS.",
        {},
    )
    return []
