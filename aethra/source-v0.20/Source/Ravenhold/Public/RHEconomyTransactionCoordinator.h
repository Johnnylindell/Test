#pragma once

#include "CoreMinimal.h"
#include "RHEconomyTransactionTypes.h"
#include "RHEconomyTransactionCoordinator.generated.h"

class URHEconomyLedgerSubsystem;

/**
 * Small transaction coordinator for gameplay systems. Prepare is durable before
 * world mutation; commit is written only after the gameplay mutation succeeds.
 * On restart, Prepared records are recovery work and must be reconciled against
 * the authoritative persistence store before being committed or aborted.
 */
UCLASS()
class RAVENHOLD_API URHEconomyTransactionCoordinator : public UObject
{
    GENERATED_BODY()

public:
    bool Initialize(UGameInstance* GameInstance);

    bool Begin(
        ERHEconomyTransactionKind Kind,
        const FString& InitiatorId,
        const FString& IdempotencyKey,
        const FString& PayloadDigest,
        FGuid& OutTransactionId,
        FString& OutError);

    bool MarkCommitted(const FGuid& TransactionId, const FString& PayloadDigest, FString& OutError);
    bool MarkAborted(const FGuid& TransactionId, const FString& Reason, FString& OutError);

private:
    UPROPERTY()
    TObjectPtr<URHEconomyLedgerSubsystem> Ledger;
};
