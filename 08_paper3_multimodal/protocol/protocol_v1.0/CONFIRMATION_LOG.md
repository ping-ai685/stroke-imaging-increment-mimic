# Protocol v1.0 — confirmation log

Events occurring after the 11 September 2026 freeze that resolve open items
**without changing any specification**. The protocol text is not edited; it records
what was true at the freeze, and this log records what happened afterwards.

A change to a specification is not recorded here. That requires `protocol_v1.1/`
under PROTOCOL §14.

---

## 2026-09-11 — §6.2 adverse state confirmed

**Open item:** the adverse physiological state was frozen provisionally as
`tf_state 0`, the respiratory-support analogue, pending confirmation by the
supervising investigators.

**Resolution:** confirmed as `tf_state 0` — GCS eye 1, motor 4 in the treatment-free
state representation, 16.1% of windows. No change to the definition.

**Consequences:**

- The provisional marking on the M0-state and M0-full results (PROTOCOL §9.1) is
  lifted. Those results stand as final: AUROC 0.795 and 0.849, difference +0.055
  (95% CI +0.031 to +0.077).
- No script is re-run. `TARGET = 0` in `35_build_landmark_dataset.py` and
  `32_tf_endpoint_event_counts.py` already carries the confirmed definition, so
  every downstream artefact — `landmark_dataset.csv`, the event counts, the
  landmark feasibility table — is unaffected.
- No amendment to `protocol_v1.0/` is required, and none is made.

**Still open after this entry:** the per-feature annotation rules in
`radiology_annotation_guideline_v1.0.md` §2. Those are not a protocol
specification but an operational document, and they must be completed and frozen
before annotation begins.
