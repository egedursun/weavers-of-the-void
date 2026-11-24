import {
  type FamilyTree,
  type TreePerson,
  type TreeTie,
  type TreeUnion,
} from '../api'

export type Point = { x: number; y: number }
export type PartnerKind = 'spouse_of' | 'concubine_of' | 'betrothed_to'
export type CareKind =
  'fostered_by' | 'godparent_of' | 'sworn_kin' | 'parent_of'

export type PlacedCard = { person: TreePerson; x: number; y: number }

export type PartnerMark = {
  key: string
  first: number
  second: number
  kind: PartnerKind
  ended: boolean
  widowed: boolean
  union: TreeUnion | null
  tie: TreeTie | null
  path: string
  knot: Point
}

export type FamilyLine = {
  key: string
  parents: number[]
  children: number[]
  path: string
}

export type CareLine = {
  key: string
  kind: CareKind
  tie: TreeTie
  path: string
}

export type RowBand = { generation: number; y: number }

export type FamilyLayout = {
  width: number
  height: number
  card: { width: number; height: number }
  cards: Map<number, PlacedCard>
  partners: PartnerMark[]
  families: FamilyLine[]
  care: CareLine[]
  rows: RowBand[]
}

const PARTNER_KINDS: readonly string[] = [
  'spouse_of',
  'concubine_of',
  'betrothed_to',
]
const CARE_KINDS: readonly string[] = [
  'fostered_by',
  'godparent_of',
  'sworn_kin',
  'parent_of',
]

const isPartner = (kind: string): kind is PartnerKind =>
  PARTNER_KINDS.includes(kind)
const isCare = (kind: string): kind is CareKind => CARE_KINDS.includes(kind)

export function familyLayout(tree: FamilyTree): FamilyLayout {
  const people = new Map(tree.people.map((person) => [person.id, person]))
  const unions = new Map(tree.unions.map((union) => [union.marriage_id, union]))
  const ties = new Map(tree.ties.map((tie) => [tie.bond_id, tie]))
  const cards = new Map<number, PlacedCard>()
  for (const card of tree.layout.cards) {
    const person = people.get(card.person_id)
    if (person) cards.set(person.id, { person, x: card.x, y: card.y })
  }
  return {
    width: tree.layout.width,
    height: tree.layout.height,
    card: { width: tree.layout.card_width, height: tree.layout.card_height },
    cards,
    partners: tree.layout.partners.flatMap((mark) =>
      isPartner(mark.kind)
        ? [
            {
              key: mark.key,
              first: mark.first_id,
              second: mark.second_id,
              kind: mark.kind,
              ended: mark.ended,
              widowed: mark.widowed,
              union:
                mark.marriage_id === null
                  ? null
                  : (unions.get(mark.marriage_id) ?? null),
              tie:
                mark.bond_id === null ? null : (ties.get(mark.bond_id) ?? null),
              path: mark.path,
              knot: { x: mark.knot_x, y: mark.knot_y },
            },
          ]
        : []
    ),
    families: tree.layout.families.map((line) => ({
      key: line.key,
      parents: line.parent_ids,
      children: line.child_ids,
      path: line.path,
    })),
    care: tree.layout.care.flatMap((line) => {
      const tie = ties.get(line.bond_id)
      return tie && isCare(tie.kind)
        ? [{ key: `care-${tie.bond_id}`, kind: tie.kind, tie, path: line.path }]
        : []
    }),
    rows: tree.layout.rows,
  }
}
