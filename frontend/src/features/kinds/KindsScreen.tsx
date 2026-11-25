import { useState } from 'react'
import { navItem } from '@/config/navigation'
import { CirclePlus, Filter } from 'lucide-react'
import { Input } from '@/components/ui/input'
import {
  EmptyState,
  LoadingBlock,
  PageHeader,
  Section,
  ShowMore,
  useShowMore,
  FieldTile,
} from '@/components/domain'
import { ForgeCard } from '@/features/cosmography/parts'
import { StepButton } from '@/features/cycles/parts'
import { why } from '@/features/dominion/model'
import { useWorldState } from '@/features/entity/api/queries'
import { type Named } from '@/features/entity/environment/labels'
import { ThingPicker } from '@/features/gatherings/parts'
import { useMadeAction } from '@/features/minds/api'
import { READ_ONLY_REASON } from '@/features/pantheon/gate'
import { ChoiceField } from '@/features/wars/military/parts'
import { KindCard } from './KindCard'
import {
  type KindConcept,
  type KindConceptInfo,
  type KindRecord,
  useKindConcepts,
  useKinds,
} from './api'
import { CONCEPT_ICONS, KINDS_ICON } from './labels'

const ITEM = navItem('kinds')
const SHOWN = 6
const EVERY_CATEGORY = 'every'
const WORLDS = ['world'] as const

function conceptTable(concepts: readonly KindConceptInfo[]) {
  return Object.fromEntries(
    concepts.map((info): [string, Named] => [
      info.concept,
      { label: info.plural, icon: CONCEPT_ICONS[info.concept], tone: 'gold' },
    ])
  )
}

function categoryTable(info: KindConceptInfo) {
  return Object.fromEntries([
    [
      EVERY_CATEGORY,
      { label: 'Every category', icon: Filter, tone: 'muted' } as Named,
    ],
    ...Object.entries(forgeCategories(info)),
  ])
}

function forgeCategories(info: KindConceptInfo) {
  return Object.fromEntries(
    info.categories.map((item): [string, Named] => [
      item.key,
      { label: item.label, icon: CONCEPT_ICONS[info.concept], tone: 'gold' },
    ])
  )
}

function KindForge({
  info,
  blocked,
}: {
  info: KindConceptInfo
  blocked: string | null
}) {
  const [name, setName] = useState('')
  const [category, setCategory] = useState(info.categories[0]?.key ?? '')
  const [world, setWorld] = useState<number | null>(null)
  const [origin, setOrigin] = useState<number | null>(null)
  const making = useMadeAction(
    'authored_kind:create',
    (_: void) => ({
      concept: info.concept,
      name: name.trim(),
      category,
      world_id: world,
      origin_node_id: origin,
      values: {},
    }),
    `A new ${info.label.toLowerCase()} is made`
  )
  const missing =
    name.trim() === ''
      ? 'Name the new kind first'
      : category === ''
        ? 'Pick its category first'
        : null
  return (
    <ForgeCard
      icon={CirclePlus}
      tone='gold'
      title={`Make a new ${info.label.toLowerCase()}`}
      note={`${info.hint}. Its holders pass it on to neighbours and trading partners; set its values on its card once it is made.`}
      columns={2}
      action={
        <StepButton
          act={making}
          icon={CirclePlus}
          label='Make the kind'
          variant='default'
          busy={why(blocked ?? missing, making.isPending)}
          onClick={() => {
            making.mutate()
            setName('')
          }}
        />
      }
    >
      <FieldTile id='kind-forge-name' label='Name of the kind'>
        <Input
          id='kind-forge-name'
          value={name}
          disabled={blocked !== null}
          onChange={(event) => setName(event.target.value)}
        />
      </FieldTile>
      <ChoiceField
        label='Category'
        value={category}
        table={forgeCategories(info)}
        blocked={blocked}
        onPick={setCategory}
      />
      <ThingPicker
        label='World it belongs to'
        value={world}
        onChange={setWorld}
        blocked={blocked}
        kinds={WORLDS}
      />
      <ThingPicker
        label='Who made it'
        value={origin}
        onChange={setOrigin}
        blocked={blocked}
      />
    </ForgeCard>
  )
}

function KindList({
  info,
  blocked,
}: {
  info: KindConceptInfo
  blocked: string | null
}) {
  const [world, setWorld] = useState<number | null>(null)
  const [holder, setHolder] = useState<number | null>(null)
  const [category, setCategory] = useState(EVERY_CATEGORY)
  const query = useKinds(info.concept, world)
  const rows: KindRecord[] = (query.data ?? []).filter(
    (row) =>
      (category === EVERY_CATEGORY || row.category === category) &&
      (holder === null || row.holders.some((node) => node.id === holder))
  )
  const shown = useShowMore(rows, SHOWN, SHOWN)
  return (
    <Section
      id='section-kinds-list'
      title={info.plural}
      description={info.hint}
      icon={CONCEPT_ICONS[info.concept]}
      tone='gold'
    >
      <div className='flex min-w-0 flex-col gap-4'>
        <div className='@container min-w-0'>
          <div className='grid min-w-0 grid-cols-1 gap-3 @2xl:grid-cols-3'>
            <ThingPicker
              label='Only of this world'
              value={world}
              onChange={setWorld}
              blocked={null}
              kinds={WORLDS}
            />
            <ThingPicker
              label='Only held by'
              value={holder}
              onChange={setHolder}
              blocked={null}
            />
            <ChoiceField
              label='Only of the category'
              value={category}
              table={categoryTable(info)}
              blocked={null}
              onPick={setCategory}
            />
          </div>
        </div>
        {query.isPending ? (
          <LoadingBlock label={`Reading the ${info.plural.toLowerCase()}`} />
        ) : query.isError ? (
          <EmptyState
            icon={KINDS_ICON}
            size='inline'
            title='The kinds could not be read'
            description={query.error.message}
          />
        ) : rows.length === 0 ? (
          <EmptyState
            icon={CONCEPT_ICONS[info.concept]}
            size='inline'
            title={
              query.data.length
                ? 'No kind matches these filters'
                : `No ${info.plural.toLowerCase()} yet`
            }
            description={
              query.data.length
                ? 'Clear a filter to see more.'
                : 'Peoples make their own as they grow; make one yourself below.'
            }
          />
        ) : (
          <>
            <ul className='flex min-w-0 flex-col gap-3'>
              {shown.visible.map((row) => (
                <KindCard
                  key={row.id}
                  info={info}
                  row={row}
                  siblings={query.data}
                  blocked={blocked}
                />
              ))}
            </ul>
            <ShowMore state={shown} />
          </>
        )}
        <KindForge key={info.concept} info={info} blocked={blocked} />
      </div>
    </Section>
  )
}

export function KindsScreen() {
  const state = useWorldState()
  const concepts = useKindConcepts()
  const [chosen, setChosen] = useState<KindConcept | null>(null)
  const blocked = state.data?.read_only ? READ_ONLY_REASON : null
  const list = concepts.data ?? []
  const info = list.find((item) => item.concept === chosen) ?? list[0]
  return (
    <>
      <PageHeader
        title={ITEM.title}
        description={ITEM.description}
        icon={ITEM.icon}
      />
      {concepts.isPending ? (
        <LoadingBlock label='Reading the kinds of things' />
      ) : concepts.isError ? (
        <EmptyState
          icon={KINDS_ICON}
          title='The kinds of things could not be read'
          description={concepts.error.message}
        />
      ) : !info ? (
        <EmptyState
          icon={KINDS_ICON}
          title='No kinds of things are known yet'
          description='Kinds appear here as the world defines them.'
        />
      ) : (
        <div className='flex min-w-0 flex-col gap-6'>
          <div className='grid min-w-0 grid-cols-1 gap-3 md:grid-cols-2'>
            <ChoiceField
              label='Kind of thing'
              icon={KINDS_ICON}
              value={info.concept}
              table={conceptTable(list)}
              blocked={null}
              onPick={(value) => setChosen(value as KindConcept)}
            />
          </div>
          <KindList key={info.concept} info={info} blocked={blocked} />
        </div>
      )}
    </>
  )
}
