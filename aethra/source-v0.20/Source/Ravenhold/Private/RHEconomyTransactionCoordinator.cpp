#include "RHEconomyTransactionCoordinator.h"

#include "Engine/GameInstance.h"
#include "RHEconomyLedgerSubsystem.h"

bool URHEconomyTransactionCoordinator::Initialize(UGameInstance* GameInstance)
{
    Ledger = GameInstance ? GameInstance->GetSubsystem<URHEconomyLedgerSubsystem>() : nullptr;
    return Ledger && Ledger->IsHealthy();
}

bool URHEconomyTransactionCoordinator::Begin(
    ERHEconomyTransactionKind Kind,
    const FString& InitiatorId,
    const FString& IdempotencyKey,
    const FString& PayloadDigest,
    FGuid& OutTransactionId,
    FString& OutError)
{
    if (!Ledger || !Ledger->IsHealthy())
    {
        OutError = TEXT("ledger_unavailable");
        return false;
    }

    FRHEconomyLedgerRecord Existing;
    if (Ledger->FindByIdempotencyKey(IdempotencyKey, Existing))
    {
        if (Existing.Kind != Kind || Existing.InitiatorId != InitiatorId || Existing.PayloadDigest != PayloadDigest)
        {
            OutError = TEXT("idempotency_key_payload_mismatch");
            return false;
        }
        OutTransactionId = Existing.TransactionId;
        return true;
    }

    FRHEconomyPrepareRequest Request;
    Request.TransactionId = FGuid::NewGuid();
    Request.Kind = Kind;
    Request.InitiatorId = InitiatorId;
    Request.IdempotencyKey = IdempotencyKey;
    Request.PayloadDigest = PayloadDigest;

    FRHEconomyLedgerRecord Prepared;
    if (!Ledger->Prepare(Request, Prepared, OutError))
    {
        return false;
    }

    OutTransactionId = Prepared.TransactionId;
    return true;
}

bool URHEconomyTransactionCoordinator::MarkCommitted(const FGuid& TransactionId, const FString& PayloadDigest, FString& OutError)
{
    if (!Ledger)
    {
        OutError = TEXT("ledger_unavailable");
        return false;
    }

    FRHEconomyLedgerRecord Record;
    return Ledger->Commit(TransactionId, PayloadDigest, Record, OutError);
}

bool URHEconomyTransactionCoordinator::MarkAborted(const FGuid& TransactionId, const FString& Reason, FString& OutError)
{
    if (!Ledger)
    {
        OutError = TEXT("ledger_unavailable");
        return false;
    }

    FRHEconomyLedgerRecord Record;
    return Ledger->Abort(TransactionId, Reason, Record, OutError);
}
