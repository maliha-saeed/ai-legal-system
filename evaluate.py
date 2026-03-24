"""
evaluate.py — Run classification report on all synthetic cases.
Run from the project root: python evaluate.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from ai.logic import classify_claim
from sklearn.metrics import classification_report, confusion_matrix

# ── Full synthetic case list ─────────────────────────────────────
# import it:
from seed_data import SYNTHETIC_CASES

# ── Run classifier on every case ────────────────────────────────
y_true = []
y_pred = []

for case in SYNTHETIC_CASES:
    result = classify_claim(
        case['incident_type'],
        case['incident_description']
    )
    y_true.append(case['incident_type'])  # ground truth
    y_pred.append(result['claim_type'])   # classifier prediction

# ── Print raw results ────────────────────────────────────────────
print("\n── Per-case results ───────────────────────────────────────")
print(f"{'#':<4} {'Client':<25} {'True':<22} {'Predicted':<22} {'OK'}")
print("-" * 80)
for i, case in enumerate(SYNTHETIC_CASES):
    true  = y_true[i]
    pred  = y_pred[i]
    ok    = "✓" if true == pred else "✗"
    print(f"{i+1:<4} {case['client_name']:<25} {true:<22} {pred:<22} {ok}")

# ── Classification report ────────────────────────────────────────
LABELS = ["Personal Injury", "Clinical Negligence", "Housing Disrepair"]

print("\n── Classification Report ──────────────────────────────────")
print(classification_report(
    y_true, y_pred,
    labels=LABELS,
    zero_division=0          
))

# ── Summary ──────────────────────────────────────────────────────
correct = sum(t == p for t, p in zip(y_true, y_pred))
total   = len(y_true)
print(f"Overall accuracy: {correct}/{total} = {correct/total*100:.1f}%")