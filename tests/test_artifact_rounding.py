"""
Every float written into an artifact is rounded to 12 significant digits (F-46).

Windows and manylinux wheels of scipy are different builds, so the same computation over the same
draws differed in the last digits of 146 p-values - a diff on every alternation between the owner's
PC and the VPS, with the real one-draw change buried in it. Pinning the versions did not remove it;
rounding at serialization does.

Reads `data/*.json`, so it fails until `drawpick.py` has re-run after a `lotto_analysis/` change.
"""

import json
from pathlib import Path

import pytest

from drawpick import EXPECTED_ARTIFACTS
from lotto_analysis.utils.serialization import SIGNIFICANT_DIGITS, round_floats

REPO_ROOT = Path(__file__).resolve().parent.parent

JSON_ARTIFACTS = [a for a in EXPECTED_ARTIFACTS if a.endswith('.json')]


def floats_in(obj):
    if isinstance(obj, float):
        yield obj
    elif isinstance(obj, dict):
        for value in obj.values():
            yield from floats_in(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from floats_in(value)


def test_a_tiny_p_value_survives_rounding():
    """Decimal-place rounding would flush 1.99e-307 to zero; significant digits keep it."""
    assert round_floats(1.996601530486648e-307) == pytest.approx(1.9966015305e-307, rel=1e-10)


def test_the_two_platforms_land_on_the_same_value():
    """The measured host and container values for the same p-value."""
    assert round_floats(0.683682015990339) == round_floats(0.6836820159903383)
    assert round_floats(1.996601530486648e-307) == round_floats(1.996601530486739e-307)


def test_rounding_leaves_everything_else_alone():
    original = {'count': 7, 'flag': True, 'name': 'hot', 'missing': None,
                'nested': [{'rate': 1 / 3}, 2, 'x']}
    rounded = round_floats(original)
    assert rounded['count'] == 7 and rounded['flag'] is True
    assert rounded['name'] == 'hot' and rounded['missing'] is None
    assert rounded['nested'][1] == 2 and rounded['nested'][2] == 'x'
    assert rounded['nested'][0]['rate'] == 0.333333333333


@pytest.mark.parametrize('artifact', JSON_ARTIFACTS)
def test_written_artifacts_carry_no_more_than_twelve_significant_digits(artifact):
    """A writer that skips `round_floats` reintroduces the platform noise."""
    data = json.loads((REPO_ROOT / artifact).read_text(encoding='utf-8'))
    unrounded = [v for v in floats_in(data)
                 if float(f'%.{SIGNIFICANT_DIGITS}g' % v) != v]
    assert not unrounded[:5], f'{artifact}: {unrounded[:5]}'
