#include "RHEconomyLedgerSubsystem.h"

#include "Dom/JsonObject.h"
#include "HAL/FileManager.h"
#include "Misc/DateTime.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/ScopeLock.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"

void URHEconomyLedgerSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);

    const FString LedgerDirectory = FPaths::Combine(FPaths::ProjectSavedDir(), TEXT("Aethra"), TEXT("Economy"));
    IFileManager::Get().MakeDirectory(*LedgerDirectory, true);
    LedgerPath = FPaths::Combine(LedgerDirectory, TEXT("economy-ledger.jsonl"));

    FString Error;
    bHealthy = ReplayLedger(Error);
    if (!bHealthy)
    {
        UE_LOG(LogTemp, Error, TEXT("Aethra economy ledger failed replay: %s"), *Error);
    }
}

void URHEconomyLedgerSubsystem::Deinitialize()
{
    FScopeLock Lock(&LedgerMutex);
    LatestByTransaction.Reset();
    TransactionByIdempotencyKey.Reset();
    LastSequence = 0;
    bHealthy = false;
    Super::Deinitialize();
}

bool URHEconomyLedgerSubsystem::Prepare(const FRHEconomyPrepareRequest& Request, FRHEconomyLedgerRecord& OutRecord, FString& OutError)
{
    FScopeLock Lock(&LedgerMutex);

    if (!bHealthy)
    {
        OutError = TEXT("ledger_unhealthy");
        return false;
    }
    if (!Request.TransactionId.IsValid() || Request.InitiatorId.IsEmpty() || Request.IdempotencyKey.IsEmpty() || Request.PayloadDigest.IsEmpty())
    {
        OutError = TEXT("invalid_prepare_request");
        return false;
    }

    if (const FGuid* ExistingTransactionId = TransactionByIdempotencyKey.Find(Request.IdempotencyKey))
    {
        const FRHEconomyLedgerRecord* Existing = LatestByTransaction.Find(*ExistingTransactionId);
        if (!Existing)
        {
            OutError = TEXT("idempotency_index_corrupt");
            return false;
        }
        if (Existing->PayloadDigest != Request.PayloadDigest || Existing->Kind != Request.Kind || Existing->InitiatorId != Request.InitiatorId)
        {
            OutError = TEXT("idempotency_key_payload_mismatch");
            return false;
        }
        OutRecord = *Existing;
        return true;
    }

    if (const FRHEconomyLedgerRecord* Existing = LatestByTransaction.Find(Request.TransactionId))
    {
        if (Existing->PayloadDigest != Request.PayloadDigest || Existing->IdempotencyKey != Request.IdempotencyKey)
        {
            OutError = TEXT("transaction_id_reuse_mismatch");
            return false;
        }
        OutRecord = *Existing;
        return true;
    }

    FRHEconomyLedgerRecord Record;
    Record.TransactionId = Request.TransactionId;
    Record.Kind = Request.Kind;
    Record.State = ERHEconomyTransactionState::Prepared;
    Record.InitiatorId = Request.InitiatorId;
    Record.IdempotencyKey = Request.IdempotencyKey;
    Record.PayloadDigest = Request.PayloadDigest;

    if (!AppendRecordLocked(Record, OutError))
    {
        bHealthy = false;
        return false;
    }

    OutRecord = Record;
    return true;
}

bool URHEconomyLedgerSubsystem::Commit(const FGuid& TransactionId, const FString& ExpectedPayloadDigest, FRHEconomyLedgerRecord& OutRecord, FString& OutError)
{
    FScopeLock Lock(&LedgerMutex);

    if (!bHealthy)
    {
        OutError = TEXT("ledger_unhealthy");
        return false;
    }

    const FRHEconomyLedgerRecord* Existing = LatestByTransaction.Find(TransactionId);
    if (!Existing)
    {
        OutError = TEXT("transaction_not_prepared");
        return false;
    }
    if (Existing->PayloadDigest != ExpectedPayloadDigest)
    {
        OutError = TEXT("payload_digest_mismatch");
        return false;
    }
    if (Existing->State == ERHEconomyTransactionState::Committed)
    {
        OutRecord = *Existing;
        return true;
    }
    if (Existing->State != ERHEconomyTransactionState::Prepared)
    {
        OutError = TEXT("transaction_not_committable");
        return false;
    }

    FRHEconomyLedgerRecord Record = *Existing;
    Record.State = ERHEconomyTransactionState::Committed;
    Record.Reason.Reset();

    if (!AppendRecordLocked(Record, OutError))
    {
        bHealthy = false;
        return false;
    }

    OutRecord = Record;
    return true;
}

bool URHEconomyLedgerSubsystem::Abort(const FGuid& TransactionId, const FString& Reason, FRHEconomyLedgerRecord& OutRecord, FString& OutError)
{
    FScopeLock Lock(&LedgerMutex);

    if (!bHealthy)
    {
        OutError = TEXT("ledger_unhealthy");
        return false;
    }

    const FRHEconomyLedgerRecord* Existing = LatestByTransaction.Find(TransactionId);
    if (!Existing)
    {
        OutError = TEXT("transaction_not_prepared");
        return false;
    }
    if (Existing->State == ERHEconomyTransactionState::Aborted)
    {
        OutRecord = *Existing;
        return true;
    }
    if (Existing->State == ERHEconomyTransactionState::Committed)
    {
        OutError = TEXT("committed_transaction_cannot_abort");
        return false;
    }

    FRHEconomyLedgerRecord Record = *Existing;
    Record.State = ERHEconomyTransactionState::Aborted;
    Record.Reason = Reason.Left(512);

    if (!AppendRecordLocked(Record, OutError))
    {
        bHealthy = false;
        return false;
    }

    OutRecord = Record;
    return true;
}

bool URHEconomyLedgerSubsystem::FindLatest(const FGuid& TransactionId, FRHEconomyLedgerRecord& OutRecord) const
{
    FScopeLock Lock(&LedgerMutex);
    if (const FRHEconomyLedgerRecord* Record = LatestByTransaction.Find(TransactionId))
    {
        OutRecord = *Record;
        return true;
    }
    return false;
}

bool URHEconomyLedgerSubsystem::FindByIdempotencyKey(const FString& IdempotencyKey, FRHEconomyLedgerRecord& OutRecord) const
{
    FScopeLock Lock(&LedgerMutex);
    const FGuid* TransactionId = TransactionByIdempotencyKey.Find(IdempotencyKey);
    if (!TransactionId)
    {
        return false;
    }
    const FRHEconomyLedgerRecord* Record = LatestByTransaction.Find(*TransactionId);
    if (!Record)
    {
        return false;
    }
    OutRecord = *Record;
    return true;
}

bool URHEconomyLedgerSubsystem::HasCommitted(const FGuid& TransactionId) const
{
    FScopeLock Lock(&LedgerMutex);
    const FRHEconomyLedgerRecord* Record = LatestByTransaction.Find(TransactionId);
    return Record && Record->State == ERHEconomyTransactionState::Committed;
}

bool URHEconomyLedgerSubsystem::ReplayLedger(FString& OutError)
{
    FScopeLock Lock(&LedgerMutex);
    LatestByTransaction.Reset();
    TransactionByIdempotencyKey.Reset();
    LastSequence = 0;

    if (!FPaths::FileExists(LedgerPath))
    {
        return true;
    }

    TArray<FString> Lines;
    if (!FFileHelper::LoadFileToStringArray(Lines, *LedgerPath))
    {
        OutError = TEXT("ledger_read_failed");
        return false;
    }

    int64 ExpectedSequence = 1;
    for (int32 Index = 0; Index < Lines.Num(); ++Index)
    {
        if (Lines[Index].TrimStartAndEnd().IsEmpty())
        {
            continue;
        }

        FRHEconomyLedgerRecord Record;
        if (!ParseRecord(Lines[Index], Record, OutError))
        {
            OutError = FString::Printf(TEXT("line_%d_%s"), Index + 1, *OutError);
            return false;
        }
        if (Record.Sequence != ExpectedSequence)
        {
            OutError = FString::Printf(TEXT("line_%d_sequence_gap"), Index + 1);
            return false;
        }
        if (!ApplyRecordLocked(Record, OutError))
        {
            OutError = FString::Printf(TEXT("line_%d_%s"), Index + 1, *OutError);
            return false;
        }

        LastSequence = Record.Sequence;
        ++ExpectedSequence;
    }

    return true;
}

bool URHEconomyLedgerSubsystem::AppendRecordLocked(FRHEconomyLedgerRecord& Record, FString& OutError)
{
    Record.Sequence = LastSequence + 1;
    Record.UnixSeconds = FDateTime::UtcNow().ToUnixTimestamp();

    const FString Serialized = SerializeRecord(Record) + LINE_TERMINATOR;
    if (!FFileHelper::SaveStringToFile(
        Serialized,
        *LedgerPath,
        FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM,
        &IFileManager::Get(),
        FILEWRITE_Append))
    {
        OutError = TEXT("ledger_append_failed");
        return false;
    }

    if (!ApplyRecordLocked(Record, OutError))
    {
        return false;
    }

    LastSequence = Record.Sequence;
    return true;
}

bool URHEconomyLedgerSubsystem::ApplyRecordLocked(const FRHEconomyLedgerRecord& Record, FString& OutError)
{
    if (!Record.TransactionId.IsValid() || Record.IdempotencyKey.IsEmpty() || Record.PayloadDigest.IsEmpty() || Record.Sequence <= 0)
    {
        OutError = TEXT("invalid_record");
        return false;
    }

    if (const FGuid* Mapped = TransactionByIdempotencyKey.Find(Record.IdempotencyKey))
    {
        if (*Mapped != Record.TransactionId)
        {
            OutError = TEXT("duplicate_idempotency_key");
            return false;
        }
    }

    if (const FRHEconomyLedgerRecord* Previous = LatestByTransaction.Find(Record.TransactionId))
    {
        if (Previous->Kind != Record.Kind || Previous->InitiatorId != Record.InitiatorId || Previous->IdempotencyKey != Record.IdempotencyKey || Previous->PayloadDigest != Record.PayloadDigest)
        {
            OutError = TEXT("immutable_transaction_fields_changed");
            return false;
        }
        if (Previous->IsTerminal())
        {
            OutError = TEXT("terminal_transaction_mutated");
            return false;
        }
        if (Previous->State != ERHEconomyTransactionState::Prepared ||
            (Record.State != ERHEconomyTransactionState::Committed && Record.State != ERHEconomyTransactionState::Aborted))
        {
            OutError = TEXT("invalid_state_transition");
            return false;
        }
    }
    else if (Record.State != ERHEconomyTransactionState::Prepared)
    {
        OutError = TEXT("first_record_must_be_prepared");
        return false;
    }

    TransactionByIdempotencyKey.Add(Record.IdempotencyKey, Record.TransactionId);
    LatestByTransaction.Add(Record.TransactionId, Record);
    return true;
}

FString URHEconomyLedgerSubsystem::SerializeRecord(const FRHEconomyLedgerRecord& Record) const
{
    TSharedRef<FJsonObject> Object = MakeShared<FJsonObject>();
    Object->SetStringField(TEXT("transaction_id"), Record.TransactionId.ToString(EGuidFormats::DigitsWithHyphensLower));
    Object->SetStringField(TEXT("kind"), KindToString(Record.Kind));
    Object->SetStringField(TEXT("state"), StateToString(Record.State));
    Object->SetStringField(TEXT("initiator_id"), Record.InitiatorId);
    Object->SetStringField(TEXT("idempotency_key"), Record.IdempotencyKey);
    Object->SetStringField(TEXT("payload_digest"), Record.PayloadDigest);
    Object->SetNumberField(TEXT("sequence"), static_cast<double>(Record.Sequence));
    Object->SetNumberField(TEXT("unix_seconds"), static_cast<double>(Record.UnixSeconds));
    Object->SetStringField(TEXT("reason"), Record.Reason);

    FString Output;
    const TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&Output);
    FJsonSerializer::Serialize(Object, Writer);
    return Output;
}

bool URHEconomyLedgerSubsystem::ParseRecord(const FString& Line, FRHEconomyLedgerRecord& OutRecord, FString& OutError) const
{
    TSharedPtr<FJsonObject> Object;
    const TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Line);
    if (!FJsonSerializer::Deserialize(Reader, Object) || !Object.IsValid())
    {
        OutError = TEXT("invalid_json");
        return false;
    }

    FString TransactionIdText;
    FString KindText;
    FString StateText;
    if (!Object->TryGetStringField(TEXT("transaction_id"), TransactionIdText) ||
        !Object->TryGetStringField(TEXT("kind"), KindText) ||
        !Object->TryGetStringField(TEXT("state"), StateText) ||
        !FGuid::Parse(TransactionIdText, OutRecord.TransactionId) ||
        !StringToKind(KindText, OutRecord.Kind) ||
        !StringToState(StateText, OutRecord.State))
    {
        OutError = TEXT("invalid_required_fields");
        return false;
    }

    if (!Object->TryGetStringField(TEXT("initiator_id"), OutRecord.InitiatorId) ||
        !Object->TryGetStringField(TEXT("idempotency_key"), OutRecord.IdempotencyKey) ||
        !Object->TryGetStringField(TEXT("payload_digest"), OutRecord.PayloadDigest))
    {
        OutError = TEXT("missing_identity_fields");
        return false;
    }

    double SequenceValue = 0.0;
    double UnixSecondsValue = 0.0;
    if (!Object->TryGetNumberField(TEXT("sequence"), SequenceValue) || !Object->TryGetNumberField(TEXT("unix_seconds"), UnixSecondsValue))
    {
        OutError = TEXT("missing_sequence_fields");
        return false;
    }
    OutRecord.Sequence = static_cast<int64>(SequenceValue);
    OutRecord.UnixSeconds = static_cast<int64>(UnixSecondsValue);
    Object->TryGetStringField(TEXT("reason"), OutRecord.Reason);
    return true;
}

FString URHEconomyLedgerSubsystem::KindToString(ERHEconomyTransactionKind Kind)
{
    switch (Kind)
    {
        case ERHEconomyTransactionKind::DirectTrade: return TEXT("direct_trade");
        case ERHEconomyTransactionKind::VendorPurchase: return TEXT("vendor_purchase");
        case ERHEconomyTransactionKind::VendorSale: return TEXT("vendor_sale");
        case ERHEconomyTransactionKind::Craft: return TEXT("craft");
        case ERHEconomyTransactionKind::MarketListing: return TEXT("market_listing");
        case ERHEconomyTransactionKind::MarketPurchase: return TEXT("market_purchase");
        case ERHEconomyTransactionKind::MailSend: return TEXT("mail_send");
        case ERHEconomyTransactionKind::MailClaim: return TEXT("mail_claim");
        case ERHEconomyTransactionKind::AdminGrant: return TEXT("admin_grant");
        case ERHEconomyTransactionKind::AdminRevoke: return TEXT("admin_revoke");
        default: return TEXT("unknown");
    }
}

bool URHEconomyLedgerSubsystem::StringToKind(const FString& Value, ERHEconomyTransactionKind& OutKind)
{
    static const TMap<FString, ERHEconomyTransactionKind> Map = {
        {TEXT("direct_trade"), ERHEconomyTransactionKind::DirectTrade},
        {TEXT("vendor_purchase"), ERHEconomyTransactionKind::VendorPurchase},
        {TEXT("vendor_sale"), ERHEconomyTransactionKind::VendorSale},
        {TEXT("craft"), ERHEconomyTransactionKind::Craft},
        {TEXT("market_listing"), ERHEconomyTransactionKind::MarketListing},
        {TEXT("market_purchase"), ERHEconomyTransactionKind::MarketPurchase},
        {TEXT("mail_send"), ERHEconomyTransactionKind::MailSend},
        {TEXT("mail_claim"), ERHEconomyTransactionKind::MailClaim},
        {TEXT("admin_grant"), ERHEconomyTransactionKind::AdminGrant},
        {TEXT("admin_revoke"), ERHEconomyTransactionKind::AdminRevoke}
    };
    if (const ERHEconomyTransactionKind* Found = Map.Find(Value))
    {
        OutKind = *Found;
        return true;
    }
    return false;
}

FString URHEconomyLedgerSubsystem::StateToString(ERHEconomyTransactionState State)
{
    switch (State)
    {
        case ERHEconomyTransactionState::Prepared: return TEXT("prepared");
        case ERHEconomyTransactionState::Committed: return TEXT("committed");
        case ERHEconomyTransactionState::Aborted: return TEXT("aborted");
        default: return TEXT("unknown");
    }
}

bool URHEconomyLedgerSubsystem::StringToState(const FString& Value, ERHEconomyTransactionState& OutState)
{
    if (Value == TEXT("prepared")) { OutState = ERHEconomyTransactionState::Prepared; return true; }
    if (Value == TEXT("committed")) { OutState = ERHEconomyTransactionState::Committed; return true; }
    if (Value == TEXT("aborted")) { OutState = ERHEconomyTransactionState::Aborted; return true; }
    return false;
}
