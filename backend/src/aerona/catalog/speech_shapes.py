from aerona.domain.enums.speech import HumourForm

HUMOUR_BITE_PCT: dict[HumourForm, int] = {
    HumourForm.WORDPLAY: 80,
    HumourForm.TEASING: 50,
    HumourForm.SATIRE: 150,
    HumourForm.ABSURD: 60,
    HumourForm.BODILY: 70,
    HumourForm.IRONY: 120,
    HumourForm.STORYTELLING: 90,
    HumourForm.RITUAL_CLOWNING: 40,
    HumourForm.PARODY: 130,
    HumourForm.RIDDLING: 50,
}

MOCKING_FORMS = frozenset({HumourForm.SATIRE, HumourForm.PARODY})
