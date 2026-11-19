from aerona.domain.enums.kin import KinGroupForm, KinMembership

SPLIT_SIZE_PCT: dict[KinGroupForm, int] = {
    KinGroupForm.LINEAGE: 100,
    KinGroupForm.CLAN: 200,
    KinGroupForm.PHRATRY: 400,
    KinGroupForm.MOIETY: 1000,
    KinGroupForm.KINDRED: 60,
    KinGroupForm.RAMAGE: 80,
    KinGroupForm.HOUSE: 150,
    KinGroupForm.LOCALIZED_GROUP: 120,
    KinGroupForm.AGE_LINKED_GROUP: 100,
}

MEMBERSHIP_SHARE_PCT: dict[KinMembership, int] = {
    KinMembership.DESCENT: 100,
    KinMembership.RESIDENCE: 80,
    KinMembership.CHOICE: 60,
}
