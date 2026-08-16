#pragma once

#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "RHEconomyTransactionTypes.h"
#include "RHEconomyLedgerSubsystem.generated.h"

/**
 * Dedicated-server transaction journal used as the v0.20 durability boundary.
 *
 * The default implementation is a single-process JSONL reference provider. It
 * provides crash-replay and idempotency for development/small-scale servers.
 * A production MMO backend should replace the storage adapter with an atomic,
 * replicated database while preserving the transaction contract.
 */
UCLASS()
class RAVENHOLD_API URHEconomyLedgerSubsystem : public UGameInstanceSubsystem
{
    GENERATED_BODY()

public:
    virtual void Initialize(FSubsystemCollectionBase& Collection) override;
    virtual void Deinitialize() override;

    UFUNCTION(BlueprintPure)
    bool IsHealthy() const { return bHealthy; }

    UFUNCTION(BlueprintPure)
    int64 GetLastSequence() const { return LastSequence; }

    bool Prepare(const FRHEconomyPrepareRequest& Request, FRHEconomyLedgerRecord& OutRecord, FString& OutError);
    bool Commit(const FGuid& TransactionId, const FString& ExpectedPayloadDigest, FRHEconomyLedgerRecord& OutRecord, FString& OutError);
    bool Abort(const FGuid& TransactionId, const FString& Reason, FRHEconomyLedgerRecord& OutRecord, FString& OutError);

    bool FindLatest(const FGuid& TransactionId, FRHEconomyLedgerRecord& OutRecord) const;
    bool FindByIdempotencyKey(const FString& IdempotencyKey, FRHEconomyLedgerRecord& OutRecord) const;
    bool HasCommitted(const FGuid& TransactionId) const;

private:
    mutable FCriticalSection LedgerMutex;
    TMap<FGuid, FRHEconomyLedgerRecord> LatestByTransaction;
    TMap<FString, FGuid> TransactionByIdempotencyKey;

    FString LedgerPath;
    int64 LastSequence = 0;
    bool bHealthy = false;

    bool ReplayLedger(FString& OutError);
    bool AppendRecordLocked(FRHEconomyLedgerRecord& Record, FString& OutError);
    bool ParseRecord(const FString& Line, FRHEconomyLedgerRecord& OutRecord, FString& OutError) const;
    FString SerializeRecord(const FRHEconomyLedgerRecord& Record) const;
    bool ApplyRecordLocked(const FRHEconomyLedgerRecord& Record, FString& OutError);

    static FString KindToString(ERHEconomyTransactionKind Kind);
    static bool StringToKind(const FString& Value, ERHEconomyTransactionKind& OutKind);
    static FString StateToString(ERHEconomyTransactionState State);
    static bool StringToState(const FString& Value, ERHEconomyTransactionState& OutState);
};
