# Diagram Conventions

Reuse these ASCII shapes, substituting labels derived from the actual input domain. Never leave a template's example labels (for example "Actor 1/2/3", "ACCEPTED/REJECTED") in the final output.

## Actor Relationship Box (Executive Summary)

```
                    ┌─────────────────┐
                    │    <ACTOR 1>    │
                    │                 │
                    │ <verb>          │
                    │ <verb>          │
                    └────────┬────────┘
                             │
                             ▼
                 ┌───────────────────────┐
                 │                       │
                 │  <PRODUCT/BUSINESS>   │
                 │                       │
                 └───────────┬───────────┘
                             │
                 ┌───────────┴───────────┐
                 │                       │
                 ▼                       ▼
        ┌─────────────────┐     ┌─────────────────┐
        │  <ACTOR 2>      │     │  <ACTOR 3>      │
        │                 │     │                 │
        │ <verb>          │     │ <verb>          │
        └─────────────────┘     └─────────────────┘
```

Include only as many actor boxes as the domain has (2, 3, or 4). Do not pad to match this example.

## Vertical Journey Flow (End-to-End Journey, Business Opportunity)

```
STEP ONE
   │
   ▼
Step Two
   │
   ▼
Step Three
```

## Lifecycle State Machine (Core Entity Lifecycle)

```
                    <ENTITY> CREATED
                         │
                         ▼
                 AWAITING <ACTOR>
                    /           \
                   /             \
                  ▼               ▼
             ACCEPTED          REJECTED
                │                  │
                ▼                  ▼
            IN PROGRESS        CANCELLED
                │
                ▼
             COMPLETED
```

Adapt state names to the entity's real lifecycle (for example approved/denied, confirmed/declined) instead of reusing accepted/rejected.

## Status Checklist (progress tracking, if applicable)

```
✓ Step confirmed
✓ Step accepted
● Currently in progress step
○ Not yet reached step
```

## Capability Map Tree (Product Capability Map)

```
                    <PRODUCT NAME>
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
   <DOMAIN 1>            <DOMAIN 2>           <DOMAIN 3>
        │                    │                    │
   Capability           Capability           Capability
   Capability           Capability           Capability
```

The number and names of branches must reflect the product's real capability areas, not a fixed template count.
