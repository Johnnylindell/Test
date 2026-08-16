#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "RHItemTypes.h"
#include "RHInventoryComponent.generated.h"

DECLARE_DYNAMIC_MULTICAST_DELEGATE(FRHInventoryChanged);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FRHTradeMarksChanged, int32, NewBalance);

UCLASS(ClassGroup=(Aethra), meta=(BlueprintSpawnableComponent))
class RAVENHOLD_API URHInventoryComponent : public UActorComponent
{
    GENERATED_BODY()

public:
    URHInventoryComponent();

    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;

    UPROPERTY(BlueprintAssignable)
    FRHInventoryChanged OnInventoryChanged;

    UPROPERTY(BlueprintAssignable)
    FRHTradeMarksChanged OnTradeMarksChanged;

    UFUNCTION(BlueprintPure)
    const TArray<FRHItemInstance>& GetItems() const { return Inventory.Entries; }

    UFUNCTION(BlueprintPure)
    int32 GetTradeMarks() const { return TradeMarks; }

    UFUNCTION(BlueprintPure)
    int32 GetMaxSlots() const { return MaxSlots; }

    UFUNCTION(BlueprintPure)
    bool HasFreeSlot() const;

    UFUNCTION(BlueprintPure)
    bool FindItem(const FGuid& InstanceId, FRHItemInstance& OutItem) const;

    UFUNCTION(BlueprintPure)
    bool CanSpendTradeMarks(int32 Amount) const;

    UFUNCTION(BlueprintPure)
    bool CanCreditTradeMarks(int32 Amount) const;

    // Server-only primitives. These are intentionally not client RPCs.
    bool ServerGrantItem(const FRHItemInstance& Item);
    bool ServerRemoveItem(const FGuid& InstanceId, int32 Quantity, FRHItemInstance* Removed = nullptr);
    bool ServerSetItemLock(const FGuid& InstanceId, ERHItemLockReason LockReason);
    bool ServerExtractLockedItem(const FGuid& InstanceId, ERHItemLockReason ExpectedReason, FRHItemInstance& OutItem);
    bool ServerClearItemLock(const FGuid& InstanceId, ERHItemLockReason ExpectedReason);
    bool ServerCreditTradeMarks(int32 Amount);
    bool ServerDebitTradeMarks(int32 Amount);

private:
    UPROPERTY(ReplicatedUsing=OnRep_Inventory)
    FRHInventoryList Inventory;

    UPROPERTY(ReplicatedUsing=OnRep_TradeMarks)
    int32 TradeMarks = 0;

    UPROPERTY(EditDefaultsOnly, Category="Inventory", meta=(ClampMin="1", ClampMax="256"))
    int32 MaxSlots = 80;

    UFUNCTION()
    void OnRep_Inventory();

    UFUNCTION()
    void OnRep_TradeMarks();

    bool HasAuthority() const;
    int32 FindIndex(const FGuid& InstanceId) const;
};
