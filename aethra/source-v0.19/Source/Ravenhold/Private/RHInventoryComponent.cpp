#include "RHInventoryComponent.h"

#include "GameFramework/Actor.h"
#include "Net/UnrealNetwork.h"

URHInventoryComponent::URHInventoryComponent()
{
    SetIsReplicatedByDefault(true);
}

void URHInventoryComponent::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(URHInventoryComponent, Inventory);
    DOREPLIFETIME(URHInventoryComponent, TradeMarks);
}

bool URHInventoryComponent::HasAuthority() const
{
    return GetOwner() && GetOwner()->HasAuthority();
}

bool URHInventoryComponent::HasFreeSlot() const
{
    return Inventory.Entries.Num() < MaxSlots;
}

int32 URHInventoryComponent::FindIndex(const FGuid& InstanceId) const
{
    return Inventory.Entries.IndexOfByPredicate([&InstanceId](const FRHItemInstance& Entry)
    {
        return Entry.InstanceId == InstanceId;
    });
}

bool URHInventoryComponent::FindItem(const FGuid& InstanceId, FRHItemInstance& OutItem) const
{
    const int32 Index = FindIndex(InstanceId);
    if (Index == INDEX_NONE)
    {
        return false;
    }

    OutItem = Inventory.Entries[Index];
    return true;
}

bool URHInventoryComponent::CanSpendTradeMarks(int32 Amount) const
{
    return Amount >= 0 && TradeMarks >= Amount;
}

bool URHInventoryComponent::CanCreditTradeMarks(int32 Amount) const
{
    return Amount >= 0 && TradeMarks <= MAX_int32 - Amount;
}

bool URHInventoryComponent::ServerGrantItem(const FRHItemInstance& Item)
{
    if (!HasAuthority() || !Item.IsValid())
    {
        return false;
    }

    if (FindIndex(Item.InstanceId) != INDEX_NONE || !HasFreeSlot())
    {
        return false;
    }

    FRHItemInstance& Added = Inventory.Entries.Add_GetRef(Item);
    Inventory.MarkItemDirty(Added);
    OnInventoryChanged.Broadcast();
    return true;
}

bool URHInventoryComponent::ServerRemoveItem(const FGuid& InstanceId, int32 Quantity, FRHItemInstance* Removed)
{
    if (!HasAuthority() || Quantity <= 0)
    {
        return false;
    }

    const int32 Index = FindIndex(InstanceId);
    if (Index == INDEX_NONE)
    {
        return false;
    }

    FRHItemInstance& Existing = Inventory.Entries[Index];
    if (Existing.LockReason != ERHItemLockReason::None || Quantity > Existing.Quantity)
    {
        return false;
    }

    if (Removed)
    {
        *Removed = Existing;
        Removed->Quantity = Quantity;
        if (Quantity < Existing.Quantity)
        {
            // A split stack becomes a new server-owned item instance.
            Removed->InstanceId = FGuid::NewGuid();
        }
    }

    if (Quantity == Existing.Quantity)
    {
        Inventory.Entries.RemoveAt(Index);
        Inventory.MarkArrayDirty();
    }
    else
    {
        Existing.Quantity -= Quantity;
        Inventory.MarkItemDirty(Existing);
    }

    OnInventoryChanged.Broadcast();
    return true;
}

bool URHInventoryComponent::ServerSetItemLock(const FGuid& InstanceId, ERHItemLockReason LockReason)
{
    if (!HasAuthority() || LockReason == ERHItemLockReason::None)
    {
        return false;
    }

    const int32 Index = FindIndex(InstanceId);
    if (Index == INDEX_NONE)
    {
        return false;
    }

    FRHItemInstance& Existing = Inventory.Entries[Index];
    if (Existing.BindState != ERHItemBindState::Unbound || Existing.LockReason != ERHItemLockReason::None)
    {
        return false;
    }

    Existing.LockReason = LockReason;
    Inventory.MarkItemDirty(Existing);
    OnInventoryChanged.Broadcast();
    return true;
}

bool URHInventoryComponent::ServerExtractLockedItem(const FGuid& InstanceId, ERHItemLockReason ExpectedReason, FRHItemInstance& OutItem)
{
    if (!HasAuthority() || ExpectedReason == ERHItemLockReason::None)
    {
        return false;
    }

    const int32 Index = FindIndex(InstanceId);
    if (Index == INDEX_NONE)
    {
        return false;
    }

    const FRHItemInstance& Existing = Inventory.Entries[Index];
    if (Existing.LockReason != ExpectedReason)
    {
        return false;
    }

    OutItem = Existing;
    Inventory.Entries.RemoveAt(Index);
    Inventory.MarkArrayDirty();
    OnInventoryChanged.Broadcast();
    return true;
}

bool URHInventoryComponent::ServerClearItemLock(const FGuid& InstanceId, ERHItemLockReason ExpectedReason)
{
    if (!HasAuthority() || ExpectedReason == ERHItemLockReason::None)
    {
        return false;
    }

    const int32 Index = FindIndex(InstanceId);
    if (Index == INDEX_NONE)
    {
        return false;
    }

    FRHItemInstance& Existing = Inventory.Entries[Index];
    if (Existing.LockReason != ExpectedReason)
    {
        return false;
    }

    Existing.LockReason = ERHItemLockReason::None;
    Inventory.MarkItemDirty(Existing);
    OnInventoryChanged.Broadcast();
    return true;
}

bool URHInventoryComponent::ServerCreditTradeMarks(int32 Amount)
{
    if (!HasAuthority() || Amount <= 0 || TradeMarks > MAX_int32 - Amount)
    {
        return false;
    }

    TradeMarks += Amount;
    OnTradeMarksChanged.Broadcast(TradeMarks);
    return true;
}

bool URHInventoryComponent::ServerDebitTradeMarks(int32 Amount)
{
    if (!HasAuthority() || Amount <= 0 || TradeMarks < Amount)
    {
        return false;
    }

    TradeMarks -= Amount;
    OnTradeMarksChanged.Broadcast(TradeMarks);
    return true;
}

void URHInventoryComponent::OnRep_Inventory()
{
    OnInventoryChanged.Broadcast();
}

void URHInventoryComponent::OnRep_TradeMarks()
{
    OnTradeMarksChanged.Broadcast(TradeMarks);
}
