# PoliProp External Validation Data

This directory contains the prepared inputs for the real-world validation
experiment. The source is the PoliProp subset released with Rescala et al.
(Findings of EMNLP 2024), derived from the Debate.org corpus of Durmus and
Cardie.

- Official record: https://zenodo.org/records/13887286
- Source code: https://github.com/manoelhortaribeiro/debate-gpt-x
- Original corpus page: https://esdurmus.github.io/ddo.html
- License: CC BY-NC-SA 3.0

The large official archives and extracted source files live under `source/`
and are intentionally ignored by Git. Run `prepare_poliprop_dataset.py` after
downloading `tidy.zip` and `processing.zip` from the official Zenodo record.
The preparation script selects the 833 manually propositioned political
debates, preserves the released human-majority labels, and creates balanced
fixed-length excerpts that fit the weakest model's context window.
