# CRK Case Mapping For Public Records Router

Router outputs are planning artifacts. They do not create factual ledger rows by themselves.

## Reports

`plan-public-records` writes a JSON report under `staging/candidates/`. Treat it as an internal research plan.

## Sources

Register sources only after a lane plan identifies a public source worth keeping. Use the lane-specific skill for source grading and extraction rules.

## Claims

Do not create claims from routing suggestions. Create claims only after source-specific extraction from registered sources.

## Research Actions

Each route plan logs `action: plan_public_records` with subject, lanes, and report path.
