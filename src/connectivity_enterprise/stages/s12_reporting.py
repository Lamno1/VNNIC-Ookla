from ._blocked import blocked

def run(ctx):
    return blocked(ctx, "S12_RESULT_REPORTING", "analysis-readiness gate")
