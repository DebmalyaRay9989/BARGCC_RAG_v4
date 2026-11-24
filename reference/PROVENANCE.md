# Source attribution and provenance

Scientific basis: user-provided 2026 IJSS candidate manuscript by Debmalya Ray and Prodipto Das, "BARG-CC: Reliability-Constrained Information Fusion with Certified View-Loss Stability and Failure Diagnostics" and its accompanying reproducibility archive.

`Figure_1_BARG_CC.png` and `app/static/figure1.png`: **user-supplied figure**, not separately licensed by the MIT software license.

`app/core.py`: new implementation consistent with the numerical formulas and declared proof assumptions. It is NOT a port of the full neural BARG-CC research training pipeline.

`samples/digits_three_derived_pseudoviews.csv`: derived from scikit-learn's 8×8 handwritten Digits dataset using `samples/build_demo.py`. All three views derive from the same underlying digit image; this is not independent multi-sensor data. View reliability proxies are synthetic/uncalibrated geometric quantities.

The app has no external telemetry, hosted language model, or affiliated cloud account. Cloud deployment requires action by the person who controls the target hosting account.
