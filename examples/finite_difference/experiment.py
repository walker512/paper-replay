"""Original, deterministic numerical experiment by walker512 (MIT).
Test central differences for sin'(0.7) = cos(0.7); no external datasets.
This is a textbook mathematical property, NOT reproduction of a named paper.
"""
import json
import math
import sys

def error(h):
    estimate = (math.sin(0.7 + h) - math.sin(0.7 - h)) / (2 * h)
    return abs(estimate - math.cos(0.7))

coarse, fine = error(0.02), error(0.01)
with open(sys.argv[1], 'w') as f:
    json.dump({'error_ratio': coarse / fine, 'fine_error': fine,
               'estimated_order': math.log2(coarse / fine)}, f)
