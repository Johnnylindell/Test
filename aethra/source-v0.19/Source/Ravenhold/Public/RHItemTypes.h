#pragma once

#include "CoreMinimal.h"
#include "Net/Serialization/FastArraySerializer.h"
#include "RHItemTypes.generated.h"

UENUM(BlueprintType)
enum class ERHItemBindState : uint8
{
    Unbound,
    CharacterBound,
    AccountBound
};

UENUM(BlueprintType)
enum class ERHItemLockReason : uint8
{
    None,
    Trade,
    Market,
    Mail,
    Crafting
};

USTRUCT(BlueprintType)
struct FRHItemStatRoll
{
    GENERATED_BODY()

    UPROPERTY(EditAnywhere, BlueprintReadWrite)
    FName StatId = NAME_None;

    UPROPERTY(EditAnywhere, BlueprintReadWrite)
    float Value = 0.0f;
};

USTRUCT(BlueprintType)
struct FRHItemInstance : public FFastArraySerializerItem
{
    GENERATED_BODY()

    UPROPERTY(EditAnywhere, BlueprintReadOnly)
    FGuid InstanceId;

    UPROPERTY(EditAnywhere, BlueprintReadOnly)
    FName DefinitionId = NAME_None;

    UPROPERTY(EditAnywhere, BlueprintReadOnly)
    int32 Quantity = 1;

    UPROPERTY(EditAnywhere, BlueprintReadOnly)
    int32 Quality = 100;

    UPROPERTY(EditAnywhere, BlueprintReadOnly)
    int32 Durability = 100;

    UPROPERTY(EditAnywhere, BlueprintReadOnly)
    int32 MaxDurability = 100;

    UPROPERTY(EditAnywhere, BlueprintReadOnly)
    FName MakerMark = NAME_None;

    UPROPERTY(EditAnywhere, BlueprintReadOnly)
    ERHItemBindState BindState = ERHItemBindState::Unbound;

    UPROPERTY(EditAnywhere, BlueprintReadOnly)
    ERHItemLockReason LockReason = ERHItemLockReason::None;

    UPROPERTY(EditAnywhere, BlueprintReadOnly)
    int64 CreatedUnixSeconds = 0;

    UPROPERTY(EditAnywhere, BlueprintReadOnly)
    TArray<FRHItemStatRoll> StatRolls;

    bool IsValid() const
    {
        return InstanceId.IsValid() && DefinitionId != NAME_None && Quantity > 0;
    }

    bool IsTradable() const
    {
        return BindState == ERHItemBindState::Unbound && LockReason == ERHItemLockReason::None;
    }
};

USTRUCT()
struct FRHInventoryList : public FFastArraySerializer
{
    GENERATED_BODY()

    UPROPERTY()
    TArray<FRHItemInstance> Entries;

    bool NetDeltaSerialize(FNetDeltaSerializeInfo& DeltaParms)
    {
        return FFastArraySerializer::FastArrayDeltaSerialize<FRHItemInstance, FRHInventoryList>(Entries, DeltaParms, *this);
    }
};

template<>
struct TStructOpsTypeTraits<FRHInventoryList> : public TStructOpsTypeTraitsBase2<FRHInventoryList>
{
    enum
    {
        WithNetDeltaSerializer = true,
    };
};
