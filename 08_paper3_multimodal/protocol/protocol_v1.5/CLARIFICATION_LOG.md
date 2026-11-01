# Protocol v1.5 — clarification log

Clarifications of wording in the frozen text. They change no specification and no result.
`PROTOCOL_v1.5_EN.md` and `PROTOCOL_v1.5_CN.md` are not edited; their SHA-256 at freeze is
recorded in `PROJECT_LOG.md`.

---

## 2026-10-04 — "full-sequence (Viterbi) decoding" in D1.1

**The wording.** Appendix D, D1.1 ("Outcome"), carried into v1.5 from v1.4, says that windows after
death entered "the full-sequence (Viterbi) decoding" of `31_decode_treatment_free_all.py`. The
Chinese text says the same ("整序列(Viterbi)解码").

**What the code does.** The labels come from pomegranate's `model.predict()`, which calls
`predict_log_proba()` and so `forward_backward()`: at each window it takes the state with the
highest smoothed posterior probability, computed from the whole sequence. It does not compute a
Viterbi path. (Pointed out on 4 October 2026 by the revision of the earlier study; confirmed here
from the pomegranate call stack, which runs `predict_log_proba` → `forward_backward`.)

**Read as.** "full-sequence decoding (the state with the highest smoothed posterior probability at
each window)". The reasoning of D1 is unchanged: smoothed posteriors use later windows, so windows
after death could change the state assigned to windows before it.

**Elsewhere.** The manuscript and supplement do not use the word "Viterbi". The docstring of
`34_filtered_state_decoding.py` said "whole-sequence Viterbi pass" and was corrected the same day
(comment only; the code is unchanged).
