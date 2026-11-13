# Diagram Templates

Mermaid skeletons for every diagram type required across the Document Template. Adapt node names/labels to the project; keep the diagram type and overall shape. Diagram depth per Solution Scope Tier is defined in [Scope Tiers](./scope-tiers.md).

## Context Diagram

```mermaid
flowchart TB
    Actor1[End User] --> System[Solution Under Design]
    System --> ExtSys1[External System A]
    System --> ExtSys2[External System B]
```

## Component Diagram

```mermaid
classDiagram
    class ApiGateway
    class OrderService
    class NotificationService
    class DataStore
    ApiGateway --> OrderService
    OrderService --> NotificationService
    OrderService --> DataStore
```

## Sequence Diagram

```mermaid
sequenceDiagram
    participant User
    participant Gateway as API Gateway
    participant Service as Order Service
    participant DB as Database
    User->>Gateway: POST /orders
    Gateway->>Service: Create Order
    Service->>DB: Persist Order
    DB-->>Service: OK
    Service-->>Gateway: 201 Created
    Gateway-->>User: 201 Created
```

## Integration Diagram

```mermaid
flowchart LR
    Solution[Solution Under Design] -->|REST/HTTPS| SystemA[External System A]
    Solution -->|Event/Async| SystemB[External System B]
    Solution -->|Batch/SFTP| SystemC[External System C]
```

## Data Flow Diagram

```mermaid
flowchart LR
    Source[Source System] --> Processing[Processing/Transformation]
    Processing --> Storage[(Data Store)]
    Storage --> Consumer[Downstream Consumer]
```

## Deployment Diagram

```mermaid
flowchart TB
    Internet --> LB[Load Balancer]
    LB --> App[Application Runtime]
    App --> DB[(Database)]
    App --> Storage[(Object Storage)]
```

## Network Diagram

```mermaid
flowchart TB
    Internet --> Firewall
    Firewall --> DMZ[DMZ / Public Subnet]
    DMZ --> Private[Private Subnet]
    Private --> DataZone[Data Zone]
```

## Roadmap / Timeline Diagram

```mermaid
gantt
    title Solution Rollout Roadmap
    dateFormat  YYYY-MM-DD
    section Phase 1
    Foundation & Core Services   :p1, 2026-01-01, 60d
    section Phase 2
    Integration Rollout          :p2, after p1, 60d
    section Phase 3
    Full Production Cutover      :p3, after p2, 30d
```
