import { useState } from 'react'
import { Plus, Sprout, Trash2, Undo2, X } from 'lucide-react'
import { plural } from '@/lib/units'
import { Button } from '@/components/ui/button'
import {
  EmptyState,
  LoadingBlock,
  Section,
  ShowMore,
  useShowMore,
} from '@/components/domain'
import { Muted } from '@/components/typography'
import { table } from '@/features/arcana/labels'
import {
  Chip,
  type Field,
  ForgeCard,
  RecordEditor,
  RecordRow,
} from '@/features/cosmography/parts'
import { StepButton } from '@/features/cycles/parts'
import { why } from '@/features/dominion/model'
import { Ref, ThingPicker } from '@/features/gatherings/parts'
import { Bars } from '@/features/sacred/parts'
import { ChoiceField } from '@/features/wars/military/parts'
import {
  type GardenView,
  type MuseumCollectionView,
  useEndsAction,
  useNodeGrounds,
} from './api'
import { GARDEN_KINDS, GROUNDS_ICON, HOARD_KINDS, PIECE_KINDS } from './labels'

const SHOWN = 6
const SPECIES = ['species'] as const
const PIECE_TYPES = ['item', 'artwork', 'species'] as const

const HOARD_FIELDS: readonly Field[] = [
  {
    key: 'kind',
    label: 'Kind of collection',
    kind: 'pick',
    table: table(HOARD_KINDS),
  },
  { key: 'prestige', label: 'Prestige', kind: 'number', min: 0, max: 100 },
]
const GARDEN_FIELDS: readonly Field[] = [
  {
    key: 'kind',
    label: 'Kind of garden',
    kind: 'pick',
    table: table(GARDEN_KINDS),
  },
  { key: 'upkeep', label: 'Upkeep (coin)', kind: 'number', min: 0, max: 10000 },
  { key: 'condition', label: 'Condition', kind: 'number', min: 0, max: 100 },
]

function Collection({
  hoard,
  blocked,
}: {
  hoard: MuseumCollectionView
  blocked: string | null
}) {
  const kind = HOARD_KINDS[hoard.kind]
  const page = useShowMore(hoard.pieces, SHOWN, SHOWN * 2)
  const [pieceKind, setPieceKind] =
    useState<keyof typeof PIECE_KINDS>('artifact')
  const [item, setItem] = useState<number | null>(null)
  const editing = useEndsAction(
    'museum:edit',
    (vars: {
      values: Record<string, number | string | boolean | null>
      release: string[]
    }) => ({ collection_id: hoard.id, ...vars }),
    'The collection keeps its new values'
  )
  const removing = useEndsAction(
    'museum:delete',
    (_: void) => ({ collection_id: hoard.id }),
    'The collection is dispersed'
  )
  const adding = useEndsAction(
    'museum_piece:add',
    (_: void) => ({
      collection_id: hoard.id,
      kind: pieceKind,
      item_id: item ?? 0,
    }),
    'The piece joins the collection'
  )
  const taking = useEndsAction(
    'museum_piece:remove',
    (pieceId: number) => ({ piece_id: pieceId }),
    'The piece leaves the collection'
  )
  const returning = useEndsAction(
    'museum_piece:restitute',
    (pieceId: number) => ({ piece_id: pieceId }),
    'The piece is given back'
  )
  const retyping = useEndsAction(
    'museum_piece:edit',
    (vars: { pieceId: number; kind: string }) => ({
      piece_id: vars.pieceId,
      values: { kind: vars.kind },
      release: [],
    }),
    'The piece keeps its new kind'
  )
  const addBlocked =
    blocked ?? (item === null ? 'Choose a thing to place' : null)
  return (
    <RecordRow
      icon={kind.icon}
      tone={kind.tone}
      title={kind.label}
      caption={`Founded in epoch ${hoard.founded_epoch}, ${plural(hoard.pieces.length, 'piece')}`}
      aside={<Chip icon={kind.icon}>Prestige {hoard.prestige}</Chip>}
    >
      {hoard.pieces.length ? (
        <div className='flex min-w-0 flex-col gap-2'>
          <ul className='flex min-w-0 flex-col gap-2'>
            {page.visible.map((piece) => {
              const named = PIECE_KINDS[piece.kind]
              return (
                <li
                  key={piece.id}
                  className='flex min-w-0 flex-wrap items-center gap-2'
                >
                  <Chip icon={named.icon}>
                    {named.label}, since epoch {piece.acquired_epoch}
                  </Chip>
                  <Ref
                    node={piece.item}
                    empty={
                      piece.fossil_bed_id
                        ? 'remains from a fossil bed'
                        : 'nothing named'
                    }
                  />
                  {piece.looted_from && (
                    <Chip icon={Undo2} variant='warning'>
                      Taken from {piece.looted_from.name}
                    </Chip>
                  )}
                  {piece.returned_by && piece.returned_epoch !== null && (
                    <Muted as='span' variant='caption'>
                      Given back by {piece.returned_by.name} in epoch{' '}
                      {piece.returned_epoch}
                    </Muted>
                  )}
                  <ChoiceField
                    label='Kind of piece'
                    value={piece.kind}
                    table={PIECE_KINDS}
                    blocked={why(blocked, retyping.isPending)}
                    onPick={(next) =>
                      retyping.mutate({ pieceId: piece.id, kind: next })
                    }
                  />
                  <StepButton
                    icon={Undo2}
                    label='Give it back'
                    busy={why(
                      blocked ??
                        (piece.looted_from
                          ? null
                          : 'It was not taken from anyone'),
                      returning.isPending
                    )}
                    onClick={() => returning.mutate(piece.id)}
                  />
                  <StepButton
                    icon={X}
                    label='Take it out'
                    busy={why(blocked, taking.isPending)}
                    onClick={() => taking.mutate(piece.id)}
                  />
                </li>
              )
            })}
          </ul>
          <ShowMore state={page} />
        </div>
      ) : (
        <Muted>It holds no pieces yet; it gathers them each epoch.</Muted>
      )}
      <ForgeCard
        icon={Plus}
        tone={kind.tone}
        title='Place a thing in this collection'
        note='Prized things, works, finds and living kinds can all be kept.'
        columns={2}
        action={
          <Button
            size='sm'
            disabled={why(addBlocked, adding.isPending) !== null}
            disabledReason={why(addBlocked, adding.isPending) ?? undefined}
            onClick={() => adding.mutate()}
          >
            <Plus />
            Place it
          </Button>
        }
      >
        <ChoiceField
          label='Kind of piece'
          value={pieceKind}
          table={PIECE_KINDS}
          blocked={blocked}
          onPick={(next) => setPieceKind(next as keyof typeof PIECE_KINDS)}
        />
        <ThingPicker
          label='Thing to place'
          value={item}
          onChange={setItem}
          blocked={blocked}
          types={PIECE_TYPES}
        />
      </ForgeCard>
      <RecordEditor
        title='Set this collection'
        note='Values you set are held against the engine until you release them.'
        fields={HOARD_FIELDS}
        locked={hoard.locked}
        busy={why(blocked, editing.isPending)}
        onSave={(values) => editing.mutate({ values, release: [] })}
        onRelease={(keys) => editing.mutate({ values: {}, release: keys })}
      />
      <StepButton
        icon={Trash2}
        label='Disperse this collection'
        busy={why(blocked, removing.isPending)}
        onClick={() => removing.mutate()}
      />
    </RecordRow>
  )
}

function Garden({
  garden,
  blocked,
}: {
  garden: GardenView
  blocked: string | null
}) {
  const kind = GARDEN_KINDS[garden.kind]
  const page = useShowMore(garden.species, SHOWN, SHOWN * 2)
  const [planted, setPlanted] = useState<number | null>(null)
  const editing = useEndsAction(
    'garden:edit',
    (vars: {
      values: Record<string, number | string | boolean | null>
      release: string[]
    }) => ({ garden_id: garden.id, ...vars }),
    'The garden keeps its new values'
  )
  const removing = useEndsAction(
    'garden:delete',
    (_: void) => ({ garden_id: garden.id }),
    'The garden is gone'
  )
  const planting = useEndsAction(
    'garden:plant',
    (_: void) => ({ garden_id: garden.id, species_id: planted ?? 0 }),
    'The garden takes in that kind of life'
  )
  const uprooting = useEndsAction(
    'garden:uproot',
    (speciesId: number) => ({ garden_id: garden.id, species_id: speciesId }),
    'That kind of life is taken from the garden'
  )
  const plantBlocked =
    blocked ?? (planted === null ? 'Choose a kind of life to plant' : null)
  return (
    <RecordRow
      icon={kind.icon}
      tone={kind.tone}
      title={kind.label}
      caption={`Laid out in epoch ${garden.founded_epoch}${garden.unpaid_epochs ? `, unpaid for ${plural(garden.unpaid_epochs, 'epoch')}` : ''}`}
      aside={<Chip icon={kind.icon}>Condition {garden.condition}</Chip>}
    >
      {garden.species.length ? (
        <div className='flex min-w-0 flex-col gap-2'>
          <div className='flex min-w-0 flex-wrap gap-2'>
            {page.visible.map((species) => (
              <span
                key={species.id}
                className='flex min-w-0 items-center gap-1'
              >
                <Ref node={species} empty='an unnamed kind' />
                <StepButton
                  icon={X}
                  label={`Take ${species.name} out`}
                  busy={why(blocked, uprooting.isPending)}
                  onClick={() => uprooting.mutate(species.id)}
                />
              </span>
            ))}
          </div>
          <ShowMore state={page} />
        </div>
      ) : (
        <Muted>Nothing is planted in it yet.</Muted>
      )}
      <ForgeCard
        icon={Sprout}
        tone='success'
        title='Plant a kind of life here'
        note='What is planted in a garden does not die out of its land.'
        columns={2}
        action={
          <Button
            size='sm'
            disabled={why(plantBlocked, planting.isPending) !== null}
            disabledReason={why(plantBlocked, planting.isPending) ?? undefined}
            onClick={() => planting.mutate()}
          >
            <Sprout />
            Plant it
          </Button>
        }
      >
        <ThingPicker
          label='Kind of life'
          value={planted}
          onChange={setPlanted}
          blocked={blocked}
          types={SPECIES}
        />
      </ForgeCard>
      <RecordEditor
        title='Set this garden'
        note='Values you set are held against the engine until you release them.'
        fields={GARDEN_FIELDS}
        locked={garden.locked}
        busy={why(blocked, editing.isPending)}
        onSave={(values) => editing.mutate({ values, release: [] })}
        onRelease={(keys) => editing.mutate({ values: {}, release: keys })}
      />
      <StepButton
        icon={Trash2}
        label='Remove this garden'
        busy={why(blocked, removing.isPending)}
        onClick={() => removing.mutate()}
      />
    </RecordRow>
  )
}

export function GroundsSection({
  nodeId,
  readOnlyReason = null,
}: {
  nodeId: number
  readOnlyReason?: string | null
}) {
  const query = useNodeGrounds(nodeId)
  const data = query.data
  const keeperId = data?.keeper?.id ?? null
  const absent = data?.absent_reason ?? null
  const blocked = readOnlyReason ?? absent
  const hoards = useShowMore(data?.collections ?? [], SHOWN, SHOWN * 2)
  const grounds = useShowMore(data?.gardens ?? [], SHOWN, SHOWN * 2)
  const [hoardKind, setHoardKind] = useState<keyof typeof HOARD_KINDS>('museum')
  const [gardenKind, setGardenKind] =
    useState<keyof typeof GARDEN_KINDS>('pleasure')
  const founding = useEndsAction(
    'museum:found',
    (_: void) => ({ keeper_id: keeperId ?? 0, kind: hoardKind }),
    'A collection is founded'
  )
  const layingOut = useEndsAction(
    'garden:found',
    (_: void) => ({ town_id: keeperId ?? 0, kind: gardenKind }),
    'A garden is laid out'
  )
  const runningHoards = useEndsAction(
    'museums:run',
    (_: void) => ({}),
    'Every collection is read'
  )
  const runningGardens = useEndsAction(
    'gardens:run',
    (_: void) => ({}),
    'Every garden is read'
  )
  return (
    <Section
      id='section-grounds'
      title='Collections and gardens: what its community keeps and tends'
      description='The museums, treasuries, royal collections and cabinets this thing or its community keeps, with every piece and where it came from, and the gardens, parks, groves and cemeteries of its town with what grows in them. Gods, worlds and stars keep none, and the controls say so.'
      icon={GROUNDS_ICON}
      tone='gold'
    >
      <div
        data-surface='GroundsSection'
        className='flex min-w-0 flex-col gap-6'
      >
        {query.isPending ? (
          <LoadingBlock label='Reading what its community keeps' />
        ) : query.isError ? (
          <EmptyState
            icon={GROUNDS_ICON}
            size='inline'
            title='This could not be read'
            description={query.error.message}
          />
        ) : (
          <>
            <Ref node={query.data.keeper} empty='no keeper' />
            <Bars
              chart='chart-grounds'
              title='Prestige of its collections and condition of its gardens'
              legend={[
                { text: 'Collections', variant: 'warning' },
                { text: 'Gardens', variant: 'outline' },
              ]}
              rows={[
                ...hoards.visible.map((hoard) => ({
                  key: `hoard-${hoard.id}`,
                  caption: `${HOARD_KINDS[hoard.kind].label}: prestige ${hoard.prestige}`,
                  segments: [{ value: hoard.prestige, fill: 'fill-warning' }],
                })),
                ...grounds.visible.map((garden) => ({
                  key: `garden-${garden.id}`,
                  caption: `${GARDEN_KINDS[garden.kind].label}: condition ${garden.condition}`,
                  segments: [{ value: garden.condition, fill: 'fill-success' }],
                })),
              ]}
              max={100}
              noun={['holding', 'holdings']}
              empty='It keeps no collection and no garden yet.'
            />
            {query.data.collections.length ? (
              <div className='flex min-w-0 flex-col gap-2'>
                <ul className='flex min-w-0 flex-col gap-2'>
                  {hoards.visible.map((hoard) => (
                    <Collection
                      key={hoard.id}
                      hoard={hoard}
                      blocked={readOnlyReason}
                    />
                  ))}
                </ul>
                <ShowMore state={hoards} />
              </div>
            ) : (
              <EmptyState
                icon={GROUNDS_ICON}
                size='inline'
                title='It keeps no collection'
                description={
                  absent ??
                  'No museum, treasury, royal collection or cabinet is kept here yet.'
                }
              />
            )}
            <ForgeCard
              icon={GROUNDS_ICON}
              tone='gold'
              title='Found a collection here'
              note='It gathers the pieces of its keeper each epoch.'
              columns={2}
              action={
                <Button
                  size='sm'
                  disabled={why(blocked, founding.isPending) !== null}
                  disabledReason={why(blocked, founding.isPending) ?? undefined}
                  onClick={() => founding.mutate()}
                >
                  <GROUNDS_ICON />
                  Found it
                </Button>
              }
            >
              <ChoiceField
                label='Kind of collection'
                value={hoardKind}
                table={HOARD_KINDS}
                blocked={blocked}
                onPick={(next) =>
                  setHoardKind(next as keyof typeof HOARD_KINDS)
                }
              />
            </ForgeCard>
            {query.data.gardens.length ? (
              <div className='flex min-w-0 flex-col gap-2'>
                <ul className='flex min-w-0 flex-col gap-2'>
                  {grounds.visible.map((garden) => (
                    <Garden
                      key={garden.id}
                      garden={garden}
                      blocked={readOnlyReason}
                    />
                  ))}
                </ul>
                <ShowMore state={grounds} />
              </div>
            ) : (
              <EmptyState
                icon={Sprout}
                size='inline'
                title='No garden is kept here'
                description={
                  absent ??
                  'No garden, park, grove or cemetery is laid out here yet.'
                }
              />
            )}
            <ForgeCard
              icon={Sprout}
              tone='success'
              title='Lay out a garden here'
              note='Its town pays its upkeep each epoch; neglected, it falls into ruin.'
              columns={2}
              action={
                <Button
                  size='sm'
                  disabled={why(blocked, layingOut.isPending) !== null}
                  disabledReason={
                    why(blocked, layingOut.isPending) ?? undefined
                  }
                  onClick={() => layingOut.mutate()}
                >
                  <Sprout />
                  Lay it out
                </Button>
              }
            >
              <ChoiceField
                label='Kind of garden'
                value={gardenKind}
                table={GARDEN_KINDS}
                blocked={blocked}
                onPick={(next) =>
                  setGardenKind(next as keyof typeof GARDEN_KINDS)
                }
              />
            </ForgeCard>
            <div className='flex min-w-0 flex-wrap gap-2'>
              <StepButton
                icon={GROUNDS_ICON}
                label='Read every collection now'
                busy={why(readOnlyReason, runningHoards.isPending)}
                onClick={() => runningHoards.mutate()}
              />
              <StepButton
                icon={Sprout}
                label='Read every garden now'
                busy={why(readOnlyReason, runningGardens.isPending)}
                onClick={() => runningGardens.mutate()}
              />
            </div>
          </>
        )}
      </div>
    </Section>
  )
}
