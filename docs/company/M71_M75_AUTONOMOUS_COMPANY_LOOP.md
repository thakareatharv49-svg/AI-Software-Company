# M71-M75 Autonomous Company Loop

## M71 Complete Project Lifecycle
ProjectLifecycle provides explicit discovered, planned, executing, validating, released, failed, and recovering states with guarded transitions.

## M72 Multi-Project Concurrency
ConcurrentProjectRunner executes independent project operations with a bounded concurrency limit and isolated failure results.

## M73 Self-Healing Engineering
SelfHealingService retries failed project operations within a hard attempt limit and records every healing action.

## M74 Autonomous Project Discovery
OpportunityDiscovery ranks candidate opportunities by expected value, confidence, risk, and estimated cost.

## M75 Autonomous Company Operating Loop
CompanyOperatingLoop provides the company-level selection/reporting boundary that later milestones can connect to discovery, portfolio allocation, and real project execution.

The M71-M75 layer is additive: existing project execution, recovery, memory, learning, GitHub, QA, and security services remain the authoritative implementations for their domains.
