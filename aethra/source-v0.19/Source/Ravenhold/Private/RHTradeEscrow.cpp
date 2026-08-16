#include "RHTradeEscrow.h"

#include "RHInventoryComponent.h"
#include "Net/UnrealNetwork.h"

ARHTradeEscrow::ARHTradeEscrow()
{
    bReplicates = true;
    bAlwaysRelevant = false;
    SetReplicateMovement(false);
}

void ARHTradeEscrow::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(ARHTradeEscrow, LeftParticipant);
    DOREPLIFETIME(ARHTradeEscrow, RightParticipant);
    DOREPLIFETIME(ARHTradeEscrow, LeftOffer);
    DOREPLIFETIME(ARHTradeEscrow, RightOffer);
    DOREPLIFETIME(ARHTradeEscrow, TradeState);
}

bool ARHTradeEscrow::InitializeTrade(AActor* InLeftParticipant, AActor* InRightParticipant)
{
    if (!HasAuthority() || !InLeftParticipant || !InRightParticipant || InLeftParticipant == InRightParticipant)
    {
        return false;
    }

    if (!GetInventory(InLeftParticipant) || !GetInventory(InRightParticipant))
    {
        return false;
    }

    LeftParticipant = InLeftParticipant;
    RightParticipant = InRightParticipant;
    if (!ParticipantsInRange())
    {
        LeftParticipant = nullptr;
        RightParticipant = nullptr;
        return false;
    }
    TradeState = ERHTradeState::Open;
    ForceNetUpdate();
    return true;
}

URHInventoryComponent* ARHTradeEscrow::GetInventory(AActor* Participant) const
{
    return Participant ? Participant->FindComponentByClass<URHInventoryComponent>() : nullptr;
}

FRHTradeOffer* ARHTradeEscrow::GetMutableOffer(AActor* Participant)
{
    if (Participant == LeftParticipant)
    {
        return &LeftOffer;
    }
    if (Participant == RightParticipant)
    {
        return &RightOffer;
    }
    return nullptr;
}

const FRHTradeOffer* ARHTradeEscrow::GetOffer(AActor* Participant) const
{
    if (Participant == LeftParticipant)
    {
        return &LeftOffer;
    }
    if (Participant == RightParticipant)
    {
        return &RightOffer;
    }
    return nullptr;
}

AActor* ARHTradeEscrow::GetOtherParticipant(AActor* Participant) const
{
    if (Participant == LeftParticipant)
    {
        return RightParticipant;
    }
    if (Participant == RightParticipant)
    {
        return LeftParticipant;
    }
    return nullptr;
}

void ARHTradeEscrow::ResetAcceptances()
{
    LeftOffer.bAccepted = false;
    RightOffer.bAccepted = false;
    ForceNetUpdate();
}

bool ARHTradeEscrow::ServerOfferItem(AActor* Participant, const FGuid& InstanceId)
{
    if (!HasAuthority() || TradeState != ERHTradeState::Open)
    {
        return false;
    }

    FRHTradeOffer* Offer = GetMutableOffer(Participant);
    URHInventoryComponent* Inventory = GetInventory(Participant);
    if (!Offer || !Inventory || !ParticipantsInRange() || Offer->ItemIds.Contains(InstanceId) || Offer->ItemIds.Num() >= MaxItemsPerSide)
    {
        return false;
    }

    FRHItemInstance Item;
    if (!Inventory->FindItem(InstanceId, Item) || !Item.IsTradable())
    {
        return false;
    }

    if (!Inventory->ServerSetItemLock(InstanceId, ERHItemLockReason::Trade))
    {
        return false;
    }

    Offer->ItemIds.Add(InstanceId);
    ResetAcceptances();
    return true;
}

bool ARHTradeEscrow::ServerRemoveOfferedItem(AActor* Participant, const FGuid& InstanceId)
{
    if (!HasAuthority() || TradeState != ERHTradeState::Open)
    {
        return false;
    }

    FRHTradeOffer* Offer = GetMutableOffer(Participant);
    URHInventoryComponent* Inventory = GetInventory(Participant);
    if (!Offer || !Inventory || !Offer->ItemIds.Contains(InstanceId))
    {
        return false;
    }

    if (!Inventory->ServerClearItemLock(InstanceId, ERHItemLockReason::Trade))
    {
        return false;
    }

    Offer->ItemIds.Remove(InstanceId);
    ResetAcceptances();
    return true;
}

bool ARHTradeEscrow::ServerSetTradeMarks(AActor* Participant, int32 Amount)
{
    if (!HasAuthority() || TradeState != ERHTradeState::Open || Amount < 0)
    {
        return false;
    }

    FRHTradeOffer* Offer = GetMutableOffer(Participant);
    URHInventoryComponent* Inventory = GetInventory(Participant);
    if (!Offer || !Inventory || !Inventory->CanSpendTradeMarks(Amount))
    {
        return false;
    }

    Offer->TradeMarks = Amount;
    ResetAcceptances();
    return true;
}

bool ARHTradeEscrow::ParticipantsInRange() const
{
    if (!LeftParticipant || !RightParticipant)
    {
        return false;
    }

    return FVector::DistSquared(LeftParticipant->GetActorLocation(), RightParticipant->GetActorLocation()) <= FMath::Square(MaxTradeDistanceCm);
}

bool ARHTradeEscrow::ValidateOffer(AActor* Participant, const FRHTradeOffer& Offer) const
{
    const URHInventoryComponent* Inventory = GetInventory(Participant);
    if (!ParticipantsInRange() || !Inventory || !Inventory->CanSpendTradeMarks(Offer.TradeMarks))
    {
        return false;
    }

    for (const FGuid& ItemId : Offer.ItemIds)
    {
        FRHItemInstance Item;
        if (!Inventory->FindItem(ItemId, Item) || Item.LockReason != ERHItemLockReason::Trade || Item.BindState != ERHItemBindState::Unbound)
        {
            return false;
        }
    }

    return true;
}

bool ARHTradeEscrow::ServerSetAccepted(AActor* Participant, bool bAccepted)
{
    if (!HasAuthority() || TradeState != ERHTradeState::Open)
    {
        return false;
    }

    FRHTradeOffer* Offer = GetMutableOffer(Participant);
    if (!Offer)
    {
        return false;
    }

    Offer->bAccepted = bAccepted;
    ForceNetUpdate();

    if (LeftOffer.bAccepted && RightOffer.bAccepted)
    {
        return CommitTrade();
    }

    return true;
}

bool ARHTradeEscrow::CommitTrade()
{
    if (!HasAuthority() || TradeState != ERHTradeState::Open)
    {
        return false;
    }

    if (!ValidateOffer(LeftParticipant, LeftOffer) || !ValidateOffer(RightParticipant, RightOffer))
    {
        ResetAcceptances();
        return false;
    }

    URHInventoryComponent* LeftInventory = GetInventory(LeftParticipant);
    URHInventoryComponent* RightInventory = GetInventory(RightParticipant);
    if (!LeftInventory || !RightInventory)
    {
        ResetAcceptances();
        return false;
    }

    const int32 LeftNetSlots = LeftInventory->GetItems().Num() - LeftOffer.ItemIds.Num() + RightOffer.ItemIds.Num();
    const int32 RightNetSlots = RightInventory->GetItems().Num() - RightOffer.ItemIds.Num() + LeftOffer.ItemIds.Num();
    if (LeftNetSlots > LeftInventory->GetMaxSlots() || RightNetSlots > RightInventory->GetMaxSlots())
    {
        ResetAcceptances();
        return false;
    }

    if (!LeftInventory->CanCreditTradeMarks(RightOffer.TradeMarks) || !RightInventory->CanCreditTradeMarks(LeftOffer.TradeMarks))
    {
        ResetAcceptances();
        return false;
    }

    for (const FGuid& ItemId : LeftOffer.ItemIds)
    {
        FRHItemInstance Existing;
        if (RightInventory->FindItem(ItemId, Existing))
        {
            ResetAcceptances();
            return false;
        }
    }
    for (const FGuid& ItemId : RightOffer.ItemIds)
    {
        FRHItemInstance Existing;
        if (LeftInventory->FindItem(ItemId, Existing))
        {
            ResetAcceptances();
            return false;
        }
    }

    TradeState = ERHTradeState::Committing;
    ForceNetUpdate();

    TArray<FRHItemInstance> LeftItems;
    TArray<FRHItemInstance> RightItems;
    LeftItems.Reserve(LeftOffer.ItemIds.Num());
    RightItems.Reserve(RightOffer.ItemIds.Num());

    auto RestoreExtracted = [](URHInventoryComponent* Inventory, TArray<FRHItemInstance>& Items)
    {
        for (FRHItemInstance& Item : Items)
        {
            Item.LockReason = ERHItemLockReason::Trade;
            Inventory->ServerGrantItem(Item);
        }
    };

    for (const FGuid& ItemId : LeftOffer.ItemIds)
    {
        FRHItemInstance Item;
        if (!LeftInventory->ServerExtractLockedItem(ItemId, ERHItemLockReason::Trade, Item))
        {
            RestoreExtracted(LeftInventory, LeftItems);
            TradeState = ERHTradeState::Open;
            ResetAcceptances();
            return false;
        }
        LeftItems.Add(Item);
    }

    for (const FGuid& ItemId : RightOffer.ItemIds)
    {
        FRHItemInstance Item;
        if (!RightInventory->ServerExtractLockedItem(ItemId, ERHItemLockReason::Trade, Item))
        {
            RestoreExtracted(LeftInventory, LeftItems);
            RestoreExtracted(RightInventory, RightItems);
            TradeState = ERHTradeState::Open;
            ResetAcceptances();
            return false;
        }
        RightItems.Add(Item);
    }

    bool bLeftDebited = false;
    bool bRightDebited = false;

    if (LeftOffer.TradeMarks > 0)
    {
        bLeftDebited = LeftInventory->ServerDebitTradeMarks(LeftOffer.TradeMarks);
        if (!bLeftDebited)
        {
            RestoreExtracted(LeftInventory, LeftItems);
            RestoreExtracted(RightInventory, RightItems);
            TradeState = ERHTradeState::Open;
            ResetAcceptances();
            return false;
        }
    }

    if (RightOffer.TradeMarks > 0)
    {
        bRightDebited = RightInventory->ServerDebitTradeMarks(RightOffer.TradeMarks);
        if (!bRightDebited)
        {
            if (bLeftDebited)
            {
                LeftInventory->ServerCreditTradeMarks(LeftOffer.TradeMarks);
            }
            RestoreExtracted(LeftInventory, LeftItems);
            RestoreExtracted(RightInventory, RightItems);
            TradeState = ERHTradeState::Open;
            ResetAcceptances();
            return false;
        }
    }

    TArray<FRHItemInstance> GrantedToRight;
    TArray<FRHItemInstance> GrantedToLeft;

    auto RollbackCommit = [&]()
    {
        for (const FRHItemInstance& Item : GrantedToRight)
        {
            RightInventory->ServerRemoveItem(Item.InstanceId, Item.Quantity);
        }
        for (const FRHItemInstance& Item : GrantedToLeft)
        {
            LeftInventory->ServerRemoveItem(Item.InstanceId, Item.Quantity);
        }

        if (bLeftDebited)
        {
            LeftInventory->ServerCreditTradeMarks(LeftOffer.TradeMarks);
        }
        if (bRightDebited)
        {
            RightInventory->ServerCreditTradeMarks(RightOffer.TradeMarks);
        }

        RestoreExtracted(LeftInventory, LeftItems);
        RestoreExtracted(RightInventory, RightItems);
        TradeState = ERHTradeState::Open;
        ResetAcceptances();
    };

    for (FRHItemInstance& Item : LeftItems)
    {
        Item.LockReason = ERHItemLockReason::None;
        if (!RightInventory->ServerGrantItem(Item))
        {
            RollbackCommit();
            return false;
        }
        GrantedToRight.Add(Item);
    }

    for (FRHItemInstance& Item : RightItems)
    {
        Item.LockReason = ERHItemLockReason::None;
        if (!LeftInventory->ServerGrantItem(Item))
        {
            RollbackCommit();
            return false;
        }
        GrantedToLeft.Add(Item);
    }

    if (RightOffer.TradeMarks > 0)
    {
        LeftInventory->ServerCreditTradeMarks(RightOffer.TradeMarks);
    }
    if (LeftOffer.TradeMarks > 0)
    {
        RightInventory->ServerCreditTradeMarks(LeftOffer.TradeMarks);
    }

    TradeState = ERHTradeState::Completed;
    ForceNetUpdate();
    return true;
}

void ARHTradeEscrow::ReleaseLocks(AActor* Participant, const FRHTradeOffer& Offer)
{
    if (URHInventoryComponent* Inventory = GetInventory(Participant))
    {
        for (const FGuid& ItemId : Offer.ItemIds)
        {
            Inventory->ServerClearItemLock(ItemId, ERHItemLockReason::Trade);
        }
    }
}

void ARHTradeEscrow::ServerCancelTrade()
{
    if (!HasAuthority() || TradeState == ERHTradeState::Completed || TradeState == ERHTradeState::Cancelled)
    {
        return;
    }

    ReleaseLocks(LeftParticipant, LeftOffer);
    ReleaseLocks(RightParticipant, RightOffer);
    TradeState = ERHTradeState::Cancelled;
    ForceNetUpdate();
}

void ARHTradeEscrow::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
    if (HasAuthority() && TradeState == ERHTradeState::Open)
    {
        ServerCancelTrade();
    }
    Super::EndPlay(EndPlayReason);
}
