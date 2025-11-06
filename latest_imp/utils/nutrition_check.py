def compare_nutrients(actual, optimum, threshold=0.9):
    """
    Compare nutrient intake vs optimum.
    Returns dict of deficits if below threshold ratio.
    """
    print("=== DEBUG: Nutrient Comparison ===")
    print("Actual Intake:")
    for k, v in actual.items():
        print(f"  {k}: {v}")
    print("\nOptimum Requirement:")
    for k, v in optimum.items():
        print(f"  {k}: {v}")
    print("==================================\n")

    deficits = {}
    for key, req_value in optimum.items():
        actual_value = actual.get(key, 0)
        if req_value <= 0:
            continue
        ratio = actual_value / req_value
        if ratio < threshold:
            deficits[key] = {
                "required": req_value,
                "actual": actual_value,
                "percent": round(ratio * 100, 1)
            }

    return deficits
