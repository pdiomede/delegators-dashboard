# Graph Delegation Events

A subgraph that indexes delegation activity on **The Graph Network** (Arbitrum One). It captures every delegation, undelegation, and withdrawal event from the [L2 Staking contract](https://arbiscan.io/address/0x00669A4CF01450B64E8A2A20E9b1FCB71E61eF03), exposing the **exact GRT delta** per transaction — not just the current total stake.

Supports both **legacy** (pre-Horizon) and **Horizon** (post-Dec 2025) event formats.

**Author:** Paolo Diomede

## Events Indexed

| Era | Contract Event | `eventType` |
|---|---|---|
| Legacy | `StakeDelegated` | `delegation` |
| Legacy | `StakeDelegatedLocked` | `undelegation` |
| Legacy | `StakeDelegatedWithdrawn` | `withdrawal` |
| Horizon | `TokensDelegated` | `delegation` |
| Horizon | `TokensUndelegated` | `undelegation` |
| Horizon | `DelegatedTokensWithdrawn` | `withdrawal` |

## Schema

```graphql
type DelegationEvent @entity(immutable: true) {
  id: ID!
  eventType: String!       # "delegation", "undelegation", or "withdrawal"
  indexer: Bytes!           # indexer (legacy) or serviceProvider (Horizon)
  delegator: Bytes!
  verifier: Bytes           # data service address (Horizon only)
  tokens: BigInt!           # exact GRT delta (in wei)
  shares: BigInt            # pool shares (null for withdrawals)
  lockedUntil: BigInt       # lock epoch (legacy undelegations only)
  isHorizon: Boolean!       # true for Horizon events, false for legacy
  timestamp: BigInt!
  blockNumber: BigInt!
  txHash: Bytes!
}
```

## Setup

```bash
npm install
npm run codegen
npm run build
```

## Deploy to Subgraph Studio

1. Create the subgraph at [thegraph.com/studio](https://thegraph.com/studio)
2. Authenticate and deploy:

```bash
graph auth <DEPLOY_KEY>
graph deploy graph-delegation-events
```

## Example Query

```graphql
{
  delegationEvents(
    where: { delegator: "0x..." }
    orderBy: timestamp
    orderDirection: desc
    first: 100
  ) {
    eventType
    indexer
    delegator
    verifier
    tokens
    shares
    isHorizon
    timestamp
    txHash
  }
}
```

## Contract

- **Address:** `0x00669A4CF01450B64E8A2A20E9b1FCB71E61eF03`
- **Network:** Arbitrum One
- **Start Block:** 42,440,000 (Nov 2022)
