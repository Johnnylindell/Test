from __future__ import annotations

import io
import zipfile

_MAX_COMPRESSED_BYTES = 15 * 1024 * 1024
_MAX_UNCOMPRESSED_BYTES = 120 * 1024 * 1024
_MAX_ARCHIVE_ENTRIES = 5000


def validate_xlsx_archive(data: bytes) -> None:
    if not data:
        raise ValueError("Excel-filen är tom")
    if len(data) > _MAX_COMPRESSED_BYTES:
        raise ValueError("Excel-filen är för stor")
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            entries = archive.infolist()
            if len(entries) > _MAX_ARCHIVE_ENTRIES:
                raise ValueError("Excel-filen innehåller för många arkivdelar")
            expanded = sum(max(0, entry.file_size) for entry in entries)
            if expanded > _MAX_UNCOMPRESSED_BYTES:
                raise ValueError("Excel-filen expanderar till för mycket data")
            if not any(entry.filename == "[Content_Types].xml" for entry in entries):
                raise ValueError("Filen är inte en giltig .xlsx-arbetsbok")
    except zipfile.BadZipFile as exc:
        raise ValueError("Filen är inte en giltig .xlsx-arbetsbok") from exc
