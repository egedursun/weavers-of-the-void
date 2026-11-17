import { useState } from 'react'
import { CirclePlus, Trash2 } from 'lucide-react'
import { plural } from '@/lib/units'
import {
  EmptyState,
  LoadingBlock,
  RangeField,
  Section,
  ShowMore,
  useShowMore,
} from '@/components/domain'
import { Muted } from '@/components/typography'
import { table } from '@/features/arcana/labels'
import {
  type Field,
  ForgeCard,
  RecordEditor,
  RecordRow,
} from '@/features/cosmography/parts'
import { StepButton } from '@/features/cycles/parts'
import { why } from '@/features/dominion/model'
import { type Named } from '@/features/entity/environment/labels'
import { useMadeAction, useRowDelete, useRowEdit } from '@/features/minds/api'
import { ChoiceField } from '@/features/wars/military/parts'
import {
  type KindConcept,
  type KindConceptInfo,
  type KindHoldingView,
  type KindRecord,
  type KindStance,
  useKindConcepts,
  useKinds,
  useWaysOfLife,
} from './api'
import { CONCEPT_ICONS, KINDS_ICON, SPREADS, STANCES } from './labels'

const SHOWN = 6
const FULL = 100
const DEFAULT_STRENGTH = 50
const GOD_KINDS = new Set(['son', 'foreign_god', 'creator'])
const GOD_STANCES: KindStance[] = ['blesses', 'forbids', 'favours']
const FOLK_STANCES: KindStance[] = ['makes', 'uses', 'favours', 'forbids']
const HOLD = 'Values you set are held against the world until you release them.'

function stanceTable(god: boolean): Record<string, Named> {
  return Object.fromEntries(
    (god ? GOD_STANCES : FOLK_STANCES).map((key) => [key, STANCES[key]])
  )
}

function holdingFields(god: boolean): Field[] {
  return [
    {
      key: 'stance',
      label: 'How it is held',
      kind: 'pick',
      table: table(stanceTable(god)),
    },
    {
      key: 'strength',
      label: 'Strength of the hold',
      kind: 'number',
      min: 0,
      max: FULL,
    },
  ]
}

function Holding({
  row,
  info,
  god,
  blocked,
}: {
  row: KindHoldingView
  info: KindConceptInfo | undefined
  god: boolean
  blocked: string | null
}) {
  const key = { id: row.id }
  const editing = useRowEdit('kind_holdings', key)
  const removing = useRowDelete('kind_holdings', key)
  const stance = STANCES[row.stance]
  const spread = SPREADS[row.spread]
  return (
    <RecordRow
      icon={stance.icon}
      tone={stance.tone ?? 'info'}
      title={`${stance.label}: ${row.kind_name}`}
      caption={`${info?.label ?? row.category_label} · ${row.category_label} · strength ${row.strength} of ${FULL} · ${spread.label.toLowerCase()} · since epoch ${row.since_epoch}`}
    >
      <RecordEditor
        title={`Set how ${row.kind_name} is held`}
        note={HOLD}
        fields={holdingFields(god)}
        locked={row.locked}
        busy={why(blocked, editing.isPending)}
        onSave={(values) => editing.mutate({ values, release: [] })}
        onRelease={(keys) => editing.mutate({ values: {}, release: keys })}
      />
      <StepButton
        icon={Trash2}
        label='Let it go'
        busy={why(blocked, removing.isPending)}
        onClick={() => removing.mutate()}
      />
    </RecordRow>
  )
}

function Made({ row }: { row: KindRecord }) {
  return (
    <RecordRow
      icon={CONCEPT_ICONS[row.concept]}
      tone={row.retired ? 'muted' : 'gold'}
      title={row.name}
      caption={`${row.category_label} · since epoch ${row.created_epoch} · held by ${plural(row.holders.length, 'holder')}${row.retired ? ' · retired' : ''}`}
    />
  )
}

function Giving({
  nodeId,
  concepts,
  god,
  blocked,
}: {
  nodeId: number
  concepts: readonly KindConceptInfo[]
  god: boolean
  blocked: string | null
}) {
  const [concept, setConcept] = useState<KindConcept | null>(
    concepts[0]?.concept ?? null
  )
  const [kind, setKind] = useState<string>('')
  const [stance, setStance] = useState<KindStance>(god ? 'blesses' : 'uses')
  const [strength, setStrength] = useState(DEFAULT_STRENGTH)
  const kinds = useKinds(concept, null)
  const options = Object.fromEntries(
    (kinds.data ?? [])
      .filter((row) => !row.retired)
      .map((row): [string, Named] => [
        String(row.id),
        {
          label: `${row.name} (${row.category_label})`,
          icon: CONCEPT_ICONS[row.concept],
          tone: 'gold',
        },
      ])
  )
  const giving = useMadeAction(
    'authored_kind:spread',
    (_: void) => ({
      concept: concept ?? 'good',
      kind_id: Number(kind),
      holder_node_id: nodeId,
      stance,
      strength,
    }),
    'The kind is held'
  )
  const noKinds =
    concept !== null && kinds.data && Object.keys(options).length === 0
      ? 'There is no kind of this sort to give yet; make one in the Kinds library'
      : null
  const missing = kind === '' ? 'Pick the kind first' : null
  const reason =
    blocked ?? (concept === null ? 'No kinds of things are known yet' : noKinds)
  return (
    <ForgeCard
      icon={CirclePlus}
      tone='gold'
      title={god ? 'Bless or forbid a kind' : 'Give it a kind'}
      note='A kind it holds spreads to neighbours and trading partners, gains strength while new and fades once its novelty wears off.'
      columns={2}
      action={
        <StepButton
          icon={CirclePlus}
          label={god ? 'Set the blessing' : 'Give the kind'}
          variant='default'
          busy={why(reason ?? missing, giving.isPending)}
          onClick={() => giving.mutate()}
        />
      }
    >
      <ChoiceField
        label='Kind of thing'
        icon={KINDS_ICON}
        value={concept ?? ''}
        table={Object.fromEntries(
          concepts.map((info): [string, Named] => [
            info.concept,
            {
              label: info.plural,
              icon: CONCEPT_ICONS[info.concept],
              tone: 'gold',
            },
          ])
        )}
        blocked={
          blocked ??
          (concepts.length ? null : 'No kinds of things are known yet')
        }
        onPick={(value) => {
          setConcept(value as KindConcept)
          setKind('')
        }}
      />
      <ChoiceField
        label='Which one'
        value={kind}
        table={options}
        blocked={reason ?? (kinds.isPending ? 'Reading the kinds' : null)}
        onPick={setKind}
      />
      <ChoiceField
        label='How it is held'
        value={stance}
        table={stanceTable(god)}
        blocked={reason}
        onPick={(value) => setStance(value as KindStance)}
      />
      <RangeField
        label='Strength of the hold'
        icon={STANCES[stance].icon}
        value={strength}
        min={0}
        max={FULL}
        level={`${strength} of ${FULL}`}
        lowLabel='Barely'
        highLabel='Wholly'
        onChange={setStrength}
        disabledReason={reason}
      />
    </ForgeCard>
  )
}

export function WaysOfLifeSection({
  nodeId,
  readOnlyReason = null,
}: {
  nodeId: number
  readOnlyReason?: string | null
}) {
  const query = useWaysOfLife(nodeId)
  const concepts = useKindConcepts()
  const holdings = useShowMore(query.data?.holdings ?? [], SHOWN, SHOWN)
  const made = useShowMore(query.data?.made ?? [], SHOWN, SHOWN)
  const known = concepts.data ?? []
  const god = GOD_KINDS.has(query.data?.node.kind ?? '')
  return (
    <Section
      id='section-ways-of-life'
      title='Ways of life'
      description='Goods, dishes, drinks, dress, crafts, music, games, money, professions, ranks and traditions held here, with how strongly and how they came; gods bless or forbid them.'
      icon={KINDS_ICON}
      tone='gold'
    >
      <div
        data-surface='WaysOfLifeSection'
        className='flex min-w-0 flex-col gap-4'
      >
        {query.isPending ? (
          <LoadingBlock label='Reading its ways of life' />
        ) : query.isError ? (
          <EmptyState
            icon={KINDS_ICON}
            size='inline'
            title='Its ways of life could not be read'
            description={query.error.message}
          />
        ) : (
          <>
            {query.data.holdings.length ? (
              <>
                <ul className='flex min-w-0 flex-col gap-2'>
                  {holdings.visible.map((row) => (
                    <Holding
                      key={row.id}
                      row={row}
                      info={known.find((item) => item.concept === row.concept)}
                      god={god}
                      blocked={readOnlyReason}
                    />
                  ))}
                </ul>
                <ShowMore state={holdings} />
              </>
            ) : (
              <EmptyState
                icon={KINDS_ICON}
                size='inline'
                title='It holds no kinds yet'
                description={`${query.data.node.name} makes, uses, favours and forbids nothing yet; give it a kind below.`}
              />
            )}
            {query.data.made.length ? (
              <>
                <Muted variant='caption'>
                  Kinds it made or that belong to it
                </Muted>
                <ul className='flex min-w-0 flex-col gap-2'>
                  {made.visible.map((row) => (
                    <Made key={`${row.concept}-${row.id}`} row={row} />
                  ))}
                </ul>
                <ShowMore state={made} />
              </>
            ) : null}
            <Giving
              nodeId={nodeId}
              concepts={known}
              god={god}
              blocked={readOnlyReason}
            />
          </>
        )}
      </div>
    </Section>
  )
}
