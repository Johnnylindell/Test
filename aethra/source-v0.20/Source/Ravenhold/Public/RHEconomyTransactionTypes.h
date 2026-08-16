#pragma once

#include "CoreMinimal.h"
#include "RHEconomyTransactionTypes.generated.h"

UENUM(BlueprintType)
enum class ERHEconomyTransactionState : uint8
{
    Unknown,
    Prepared,
    Committed,
    Aborted
};

UENUM(BlueprintType)
enum class ERHEconomyTransactionKind : uint8
{
    DirectTrade,
    VendorPurchase,
    VendorSale,
    Craft,
    MarketListing,
    MarketPurchase,
    MailSend,
    MailClaim,
    AdminGrant,
    AdminRevoke
};

USTRUCT(BlueprintType)
struct FRHEconomyLedgerRecord
{
    GENERATED_BODY()

    UPROPERTY(BlueprintReadOnly)
    FGuid TransactionId;

    UPROPERTY(BlueprintReadOnly)
    ERHEconomyTransactionKind Kind = ERHEconomyTransactionKind::DirectTrade;

    UPROPERTY(BlueprintReadOnly)
    ERHEconomyTransactionState State = ERHEconomyTransactionState::Unknown;

    UPROPERTY(BlueprintReadOnly)
    FString InitiatorId;

    UPROPERTY(BlueprintReadOnly)
    FString IdempotencyKey;

    UPROPERTY(BlueprintReadOnly)
    FString PayloadDigest;

    UPROPERTY(BlueprintReadOnly)
    int64 Sequence = 0;

    UPROPERTY(BlueprintReadOnly)
    int64 UnixSeconds = 0;

    UPROPERTY(BlueprintReadOnly)
    FString Reason;

    bool IsTerminal() const
    {
        return State == ERHEconomyTransactionState::Committed || State == ERHEconomyTransactionState::Aborted;
    }
};

USTRUCT(BlueprintType)
struct FRHEconomyPrepareRequest
{
    GENERATED_BODY()

    UPROPERTY(EditAnywhere, BlueprintReadWrite)
    FGuid TransactionId;

    UPROPERTY(EditAnywhere, BlueprintReadWrite)
    ERHEconomyTransactionKind Kind = ERHEconomyTransactionKind::DirectTrade;

    UPROPERTY(EditAnywhere, BlueprintReadWrite)
    FString InitiatorId;

    UPROPERTY(EditAnywhere, BlueprintReadWrite)
    FString IdempotencyKey;

    UPROPERTY(EditAnywhere, BlueprintReadWrite)
    FString PayloadDigest;
};
