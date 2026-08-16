#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "RHTradeEscrow.generated.h"

class URHInventoryComponent;

UENUM(BlueprintType)
enum class ERHTradeState : uint8
{
    Open,
    Committing,
    Completed,
    Cancelled
};

USTRUCT(BlueprintType)
struct FRHTradeOffer
{
    GENERATED_BODY()

    UPROPERTY(BlueprintReadOnly)
    TArray<FGuid> ItemIds;

    UPROPERTY(BlueprintReadOnly)
    int32 TradeMarks = 0;

    UPROPERTY(BlueprintReadOnly)
    bool bAccepted = false;
};

UCLASS()
class RAVENHOLD_API ARHTradeEscrow : public AActor
{
    GENERATED_BODY()

public:
    ARHTradeEscrow();

    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;
    virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

    bool InitializeTrade(AActor* InLeftParticipant, AActor* InRightParticipant);
    bool ServerOfferItem(AActor* Participant, const FGuid& InstanceId);
    bool ServerRemoveOfferedItem(AActor* Participant, const FGuid& InstanceId);
    bool ServerSetTradeMarks(AActor* Participant, int32 Amount);
    bool ServerSetAccepted(AActor* Participant, bool bAccepted);
    void ServerCancelTrade();

    UFUNCTION(BlueprintPure)
    ERHTradeState GetTradeState() const { return TradeState; }

private:
    UPROPERTY(Replicated)
    TObjectPtr<AActor> LeftParticipant;

    UPROPERTY(Replicated)
    TObjectPtr<AActor> RightParticipant;

    UPROPERTY(Replicated)
    FRHTradeOffer LeftOffer;

    UPROPERTY(Replicated)
    FRHTradeOffer RightOffer;

    UPROPERTY(Replicated)
    ERHTradeState TradeState = ERHTradeState::Open;

    UPROPERTY(EditDefaultsOnly, Category="Trade", meta=(ClampMin="1", ClampMax="32"))
    int32 MaxItemsPerSide = 12;

    UPROPERTY(EditDefaultsOnly, Category="Trade", meta=(ClampMin="100.0"))
    float MaxTradeDistanceCm = 1200.0f;

    URHInventoryComponent* GetInventory(AActor* Participant) const;
    FRHTradeOffer* GetMutableOffer(AActor* Participant);
    const FRHTradeOffer* GetOffer(AActor* Participant) const;
    AActor* GetOtherParticipant(AActor* Participant) const;

    bool ParticipantsInRange() const;
    bool ValidateOffer(AActor* Participant, const FRHTradeOffer& Offer) const;
    bool CommitTrade();
    void ReleaseLocks(AActor* Participant, const FRHTradeOffer& Offer);
    void ResetAcceptances();
};
