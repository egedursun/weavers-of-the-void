from aerona.domain.enums.bond import BondKind

B = BondKind

BOND_SYNONYMS: dict[str, BondKind] = {
    word: kind
    for kind, words in (
        (B.PRODUCED, ("made by", "maker", "made", "creator", "created", "crafted", "forged", "woven", "written", "composed", "producer")),
        (B.BUILT, ("builder", "constructed", "raised", "founded")),
        (B.OWNS, ("owner", "owned", "possesses", "has", "holds", "belongs to")),
        (B.LIVES_IN, ("lives", "dwells", "resides", "inhabits", "home")),
        (B.INSIDE, ("located in", "location", "in", "within", "contains", "found in")),
        (B.WORSHIPS, ("worshipper", "worship", "believes", "prays to", "devoted to")),
        (B.ENEMY, ("enemy of", "foe", "opposes", "fights", "at war with")),
        (B.RIVAL, ("rival of", "contender", "competitor")),
        (B.ALLY, ("ally of", "friend", "alliance", "allied")),
        (B.PROTECTS, ("guards", "guardian", "protector", "watches over", "defends")),
        (B.RULES, ("rules over", "ruler", "governs", "reigns", "lord of")),
        (B.TELLS_OF, ("tells", "tale of", "story of", "legend of", "about", "subject", "praises", "remembers")),
        (B.SOURCE_OF, ("source", "origin", "material", "derived from", "comes from")),
        (B.LOVES, ("lover", "beloved", "in love with")),
        (B.HUNTS, ("hunter", "preys on", "hunting")),
        (B.CELEBRATES, ("celebration", "festival of", "feast of")),
        (B.KNOWS, ("knower", "learned", "knowledge of")),
        (B.SPEAKS, ("speaker", "language of", "tongue")),
        (B.RELATED, ("related to", "linked", "connected", "associated")),
        (B.CAUSED, ("cause", "caused by", "led to", "brought about")),
        (B.PART_OF, ("part", "member part", "piece of")),
        (B.COMPANION, ("companion of", "comrade", "friend of")),
        (B.PURSUES, ("seeks", "chases", "searches for")),
        (B.DESCENDS_FROM, ("descendant", "child of", "heir of", "offspring", "ancestor")),
        (B.PROPHESIES, ("prophecy of", "foretells", "predicts")),
    )
    for word in words
}
