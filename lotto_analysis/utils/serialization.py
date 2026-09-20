"""Rounding applied to every artifact before it is written.

Windows and manylinux wheels of scipy are different builds, so the same computation over the same
draws differs in the last couple of digits of a float. Left in the artifacts, that noise is a diff
on every alternation between the owner's PC and the VPS (F-46). Twelve significant digits is far
below any threshold this repo tests and far above the precision the figures carry.
"""

SIGNIFICANT_DIGITS = 12


def round_floats(obj, digits: int = SIGNIFICANT_DIGITS):
    """Return obj with every float rounded to `digits` significant digits.

    Significant digits, not decimal places: a p-value of 1.99e-307 must survive, and round(x, 12)
    would flush it to zero. Ints, bools and strings are returned unchanged.
    """
    if isinstance(obj, float):
        return float(f"%.{digits}g" % obj)
    if isinstance(obj, dict):
        return {k: round_floats(v, digits) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [round_floats(v, digits) for v in obj]
    return obj
