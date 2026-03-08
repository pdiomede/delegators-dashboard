import {
  StakeDelegated,
  StakeDelegatedLocked,
  StakeDelegatedWithdrawn,
  TokensDelegated,
  TokensUndelegated,
  DelegatedTokensWithdrawn,
} from "../generated/L2Staking/L2Staking";
import { DelegationEvent } from "../generated/schema";

// ── Legacy event handlers (pre-Horizon) ─────────────────────────────

export function handleStakeDelegated(event: StakeDelegated): void {
  let id =
    event.transaction.hash.toHexString() +
    "-" +
    event.logIndex.toString();

  let entity = new DelegationEvent(id);
  entity.eventType = "delegation";
  entity.indexer = event.params.indexer;
  entity.delegator = event.params.delegator;
  entity.verifier = null;
  entity.tokens = event.params.tokens;
  entity.shares = event.params.shares;
  entity.lockedUntil = null;
  entity.isHorizon = false;
  entity.timestamp = event.block.timestamp;
  entity.blockNumber = event.block.number;
  entity.txHash = event.transaction.hash;
  entity.save();
}

export function handleStakeDelegatedLocked(
  event: StakeDelegatedLocked
): void {
  let id =
    event.transaction.hash.toHexString() +
    "-" +
    event.logIndex.toString();

  let entity = new DelegationEvent(id);
  entity.eventType = "undelegation";
  entity.indexer = event.params.indexer;
  entity.delegator = event.params.delegator;
  entity.verifier = null;
  entity.tokens = event.params.tokens;
  entity.shares = event.params.shares;
  entity.lockedUntil = event.params.until;
  entity.isHorizon = false;
  entity.timestamp = event.block.timestamp;
  entity.blockNumber = event.block.number;
  entity.txHash = event.transaction.hash;
  entity.save();
}

export function handleStakeDelegatedWithdrawn(
  event: StakeDelegatedWithdrawn
): void {
  let id =
    event.transaction.hash.toHexString() +
    "-" +
    event.logIndex.toString();

  let entity = new DelegationEvent(id);
  entity.eventType = "withdrawal";
  entity.indexer = event.params.indexer;
  entity.delegator = event.params.delegator;
  entity.verifier = null;
  entity.tokens = event.params.tokens;
  entity.shares = null;
  entity.lockedUntil = null;
  entity.isHorizon = false;
  entity.timestamp = event.block.timestamp;
  entity.blockNumber = event.block.number;
  entity.txHash = event.transaction.hash;
  entity.save();
}

// ── Horizon event handlers (post Dec 11, 2025) ─────────────────────

export function handleTokensDelegated(event: TokensDelegated): void {
  let id =
    event.transaction.hash.toHexString() +
    "-" +
    event.logIndex.toString();

  let entity = new DelegationEvent(id);
  entity.eventType = "delegation";
  entity.indexer = event.params.serviceProvider;
  entity.delegator = event.params.delegator;
  entity.verifier = event.params.verifier;
  entity.tokens = event.params.tokens;
  entity.shares = event.params.shares;
  entity.lockedUntil = null;
  entity.isHorizon = true;
  entity.timestamp = event.block.timestamp;
  entity.blockNumber = event.block.number;
  entity.txHash = event.transaction.hash;
  entity.save();
}

export function handleTokensUndelegated(event: TokensUndelegated): void {
  let id =
    event.transaction.hash.toHexString() +
    "-" +
    event.logIndex.toString();

  let entity = new DelegationEvent(id);
  entity.eventType = "undelegation";
  entity.indexer = event.params.serviceProvider;
  entity.delegator = event.params.delegator;
  entity.verifier = event.params.verifier;
  entity.tokens = event.params.tokens;
  entity.shares = event.params.shares;
  entity.lockedUntil = null;
  entity.isHorizon = true;
  entity.timestamp = event.block.timestamp;
  entity.blockNumber = event.block.number;
  entity.txHash = event.transaction.hash;
  entity.save();
}

export function handleDelegatedTokensWithdrawn(
  event: DelegatedTokensWithdrawn
): void {
  let id =
    event.transaction.hash.toHexString() +
    "-" +
    event.logIndex.toString();

  let entity = new DelegationEvent(id);
  entity.eventType = "withdrawal";
  entity.indexer = event.params.serviceProvider;
  entity.delegator = event.params.delegator;
  entity.verifier = event.params.verifier;
  entity.tokens = event.params.tokens;
  entity.shares = null;
  entity.lockedUntil = null;
  entity.isHorizon = true;
  entity.timestamp = event.block.timestamp;
  entity.blockNumber = event.block.number;
  entity.txHash = event.transaction.hash;
  entity.save();
}
