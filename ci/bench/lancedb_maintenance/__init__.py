"""
LanceDB maintenance-contract bake-off RIG for Nexus Brain.

Spike 0.4 (O-LANCE-BAKEOFF) — a reusable measurement harness that reports the §6
maintenance-contract metrics for any `MaintenanceTarget`:
  - `optimize()` latency  (monotonic-clock delta)
  - index-build peak RAM  (`tracemalloc` peak, stdlib)
  - steady-state disk      (versions + transactions; dir-walk byte sum)
  - the post-`optimize()` `num_unindexed_rows == 0` monitor (§6: post-write rows
    must not be left on a flat scan).

Parametrized on a `MaintenanceTarget` Protocol; the authoritative real-`lancedb`
reference-Mac bake-off (real backend + real embedding model + real multi-repo corpus)
is an explicit **Phase-3 carry** (D-A17). This rig ships the instrumentation + a
reference `FakeMaintenanceStore` + a PROPOSED budget envelope.

Anchored to ARCHITECTURE.md §6 (LanceDB store & maintenance contract) + §24/§26
(the pre-build spike register — O-LANCE-BAKEOFF "maintenance-contract invisibility").

SCOPE: This is the RIG, not the real run. The Fake is for harness validation only.
NETWORK: Zero network egress. The Fake is a deterministic in-memory + temp-dir double.
DEP: No new runtime dependency (scope B) — stdlib instrumentation only.
"""
