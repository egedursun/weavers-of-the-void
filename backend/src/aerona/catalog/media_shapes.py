from aerona.domain.enums.media import MediaItemKind, OutletFunding, RecordForm

FUNDING_REVENUE_PCT: dict[OutletFunding, int] = {
    OutletFunding.SALES: 100,
    OutletFunding.PATRONAGE: 60,
    OutletFunding.ADVERTISING: 130,
    OutletFunding.STATE: 50,
}

UNCENSORED_FUNDING = frozenset({OutletFunding.STATE})

ITEM_SWAY_PCT: dict[MediaItemKind, int] = {
    MediaItemKind.NEWS: 100,
    MediaItemKind.OPINION: 150,
    MediaItemKind.RECORD_OF_EVENT: 50,
    MediaItemKind.ENTERTAINMENT: 30,
    MediaItemKind.INSTRUCTION: 20,
    MediaItemKind.PROMOTION: 60,
    MediaItemKind.DEVOTION: 80,
    MediaItemKind.OFFICIAL: 120,
}

FORM_DECAY_PCT: dict[RecordForm, int] = {
    RecordForm.WRITTEN: 100,
    RecordForm.PRINTED: 80,
    RecordForm.IMAGE: 70,
    RecordForm.SOUND: 90,
    RecordForm.MOVING_IMAGE: 90,
    RecordForm.SIGNAL: 150,
    RecordForm.NETWORK: 120,
    RecordForm.LIVING: 200,
    RecordForm.CRAFTED: 40,
    RecordForm.MENTAL: 250,
}
