"""Compute actual normalization output for all fixture cases."""
import sys

sys.path.insert(0, "/opt/data/workspace/telegram-user")
from pathlib import Path

import yaml

from app.normalization.pipeline import NormalizationConfig, normalize_text, tokenize

fixtures = Path("/opt/data/workspace/telegram-user/tests/fixtures")

cfg = NormalizationConfig()

# Normalization cases
with open(fixtures / "normalization/normalization_cases.yaml") as f:
    data = yaml.safe_load(f)

cases = data["cases"]
for case in cases:
    result = normalize_text(case["input"], cfg)
    tokens = tokenize(result)
    case["actual_text"] = result
    case["actual_tokens"] = tokens
    match = result == case["expected_text"]
    print(f"  {case['id']}: {'OK' if match else 'DIFF'} - {result!r} vs {case['expected_text']!r}")

# Confusable cases
with open(fixtures / "normalization/confusable_cases.yaml") as f:
    data = yaml.safe_load(f)

conf_cases = data["cases"]
for case in conf_cases:
    result = normalize_text(case["input"], cfg)
    tokens = tokenize(result)
    case["actual_text"] = result
    case["actual_tokens"] = tokens
    match = result == case["expected_text"]
    print(f"  {case['id']}: {'OK' if match else 'DIFF'} - {result!r} vs {case['expected_text']!r}")

print("\n=== SUMMARY ===")
norm_ok = sum(1 for c in cases if c["actual_text"] == c["expected_text"])
conf_ok = sum(1 for c in conf_cases if c["actual_text"] == c["expected_text"])
print(f"Normalization: {norm_ok}/{len(cases)} pass")
print(f"Confusable: {conf_ok}/{len(conf_cases)} pass")
