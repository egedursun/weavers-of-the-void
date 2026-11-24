import { useState } from 'react'
import { CirclePlus, type LucideIcon } from 'lucide-react'
import {
  EmptyState,
  LoadingBlock,
  Section,
  ShowMore,
  useShowMore,
} from '@/components/domain'
import { type KpiTone } from '@/components/domain/KpiTile'
import { Label, Muted } from '@/components/typography'
import { ForgeCard } from '@/features/cosmography/parts'
import { StepButton, TextField } from '@/features/cycles/parts'
import { why } from '@/features/dominion/model'
import { type Named } from '@/features/entity/environment/labels'
import { useMadeAction } from '@/features/minds/api'
import { ChoiceField } from '@/features/wars/military/parts'
import { KindCard } from './KindCard'
import {
  type KindConcept,
  type KindConceptInfo,
  type KindHoldingView,
  useKindConcepts,
  useKinds,
  useWaysOfLife,
} from './api'
import { CONCEPT_ICONS, SPREADS, STANCES } from './labels'

const SHOWN = 4
const FULL = 100

function Forge({
  nodeId,
  info,
  blocked,
}: {
  nodeId: number
  info: KindConceptInfo
  blocked: string | null
}) {
  const [name, setName] = useState('')
  const [category, setCategory] = useState(info.categories[0]?.key ?? '')
  const noun = info.label.toLowerCase()
  const making = useMadeAction(
    'authored_kind:create',
    (_: void) => ({
      concept: info.concept,
      name: name.trim(),
      category,
      world_id: null,
      origin_node_id: nodeId,
      values: {},
    }),
    `A new ${noun} is made`
  )
  const missing =
    name.trim() === ''
      ? `Name the new ${noun} first`
      : category === ''
        ? 'Pick its category first'
        : null
  return (
    <ForgeCard
      icon={CirclePlus}
      tone='gold'
      title={`Make a new ${noun} here`}
      note={`${info.hint}. It is made by this one and held from the start; set every value on its card once it is made.`}
      columns={2}
      action={
        <StepButton
          icon={CirclePlus}
          label={`Make the ${noun}`}
          variant='default'
          busy={why(blocked ?? missing, making.isPending)}
          onClick={() => {
            making.mutate()
            setName('')
          }}
        />
      }
    >
      <TextField
        label={`Name of the ${noun}`}
        value={name}
        blocked={blocked}
        onChange={setName}
      />
      <ChoiceField
        label={`Category of the ${noun}`}
        icon={CONCEPT_ICONS[info.concept]}
        value={category}
        table={Object.fromEntries(
          info.categories.map((item): [string, Named] => [
            item.key,
            {
              label: item.label,
              icon: CONCEPT_ICONS[info.concept],
              tone: 'gold',
            },
          ])
        )}
        blocked={
          blocked ??
          (info.categories.length
            ? null
            : 'This kind of thing has no categories')
        }
        onPick={setCategory}
      />
    </ForgeCard>
  )
}

function ConceptBlock({
  nodeId,
  info,
  holdings,
  blocked,
}: {
  nodeId: number
  info: KindConceptInfo
  holdings: readonly KindHoldingView[]
  blocked: string | null
}) {
  const kinds = useKinds(info.concept, null)
  const known = kinds.data ?? []
  const held = holdings
    .map((holding) => ({
      holding,
      row: known.find((row) => row.id === holding.kind_id),
    }))
    .filter((item) => item.row !== undefined)
  const paged = useShowMore(held, SHOWN, SHOWN)
  return (
    <div
      data-surface='ConceptBlock'
      className='flex min-w-0 flex-col gap-3 rounded-md border surface-well border-gild/20 bg-muted/60 p-3'
    >
      <Label variant='overline'>{`${info.plural} (${held.length})`}</Label>
      {kinds.isPending ? (
        <LoadingBlock label={`Reading its ${info.plural.toLowerCase()}`} />
      ) : kinds.isError ? (
        <EmptyState
          icon={CONCEPT_ICONS[info.concept]}
          size='inline'
          title={`Its ${info.plural.toLowerCase()} could not be read`}
          description={kinds.error.message}
        />
      ) : held.length === 0 ? (
        <EmptyState
          icon={CONCEPT_ICONS[info.concept]}
          size='inline'
          title={`It holds no ${info.plural.toLowerCase()} yet`}
          description='Make one below, or give it one through its ways of life.'
        />
      ) : (
        <>
          <ul className='flex min-w-0 flex-col gap-3'>
            {paged.visible.map(({ holding, row }) =>
              row ? (
                <li key={holding.id} className='flex min-w-0 flex-col gap-1'>
                  <Muted variant='caption'>
                    {`${STANCES[holding.stance].label} · strength ${holding.strength} of ${FULL} · ${SPREADS[holding.spread].label.toLowerCase()} · since epoch ${holding.since_epoch}`}
                  </Muted>
                  <ul className='flex min-w-0 flex-col'>
                    <KindCard
                      info={info}
                      row={row}
                      siblings={known}
                      blocked={blocked}
                    />
                  </ul>
                </li>
              ) : null
            )}
          </ul>
          <ShowMore state={paged} />
        </>
      )}
      <Forge nodeId={nodeId} info={info} blocked={blocked} />
    </div>
  )
}

export function ConceptSection({
  id,
  nodeId,
  concepts,
  title,
  description,
  icon,
  tone,
  readOnlyReason = null,
}: {
  id: string
  nodeId: number
  concepts: readonly KindConcept[]
  title: string
  description: string
  icon: LucideIcon
  tone: KpiTone
  readOnlyReason?: string | null
}) {
  const ways = useWaysOfLife(nodeId)
  const known = useKindConcepts()
  const infos = concepts
    .map((concept) => known.data?.find((info) => info.concept === concept))
    .filter((info): info is KindConceptInfo => info !== undefined)
  return (
    <Section
      id={id}
      title={title}
      description={description}
      icon={icon}
      tone={tone}
    >
      <div data-surface={id} className='flex min-w-0 flex-col gap-4'>
        {ways.isPending || known.isPending ? (
          <LoadingBlock label='Reading its ways of life' />
        ) : ways.isError || known.isError ? (
          <EmptyState
            icon={icon}
            size='inline'
            title='Its ways of life could not be read'
            description={
              (ways.error ?? known.error)?.message ??
              'The server did not answer'
            }
          />
        ) : infos.length === 0 ? (
          <EmptyState
            icon={icon}
            size='inline'
            title='These kinds of things are not known yet'
            description='The world does not hold these kinds of things.'
          />
        ) : (
          infos.map((info) => (
            <ConceptBlock
              key={info.concept}
              nodeId={nodeId}
              info={info}
              holdings={ways.data.holdings.filter(
                (row) => row.concept === info.concept
              )}
              blocked={readOnlyReason}
            />
          ))
        )}
      </div>
    </Section>
  )
}
