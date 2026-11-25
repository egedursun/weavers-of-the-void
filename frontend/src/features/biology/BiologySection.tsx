import { useState } from 'react'
import {
  Bug,
  Droplet,
  Hand,
  HeartPulse,
  Link2,
  RotateCcw,
  Unlink,
  Unlock,
} from 'lucide-react'
import { type ActProp } from '@/api/mutation'
import { Button } from '@/components/ui/button'
import {
  EmptyState,
  LoadingBlock,
  Section,
  ShowMore,
  useShowMore,
} from '@/components/domain'
import { Muted } from '@/components/typography'
import {
  Chip,
  Facts,
  type Field,
  RecordEditor,
} from '@/features/cosmography/parts'
import { StepButton } from '@/features/cycles/parts'
import { why } from '@/features/dominion/model'
import { NodePicker } from '@/features/entity/mind/parts'
import { TISSUE } from '@/features/entity/wilds/anatomyLabels'
import { BIASES } from '@/features/folkways/labels'
import { Ref } from '@/features/gatherings/parts'
import { Bars } from '@/features/sacred/parts'
import {
  type BiologyBodyView,
  type BiologyEffectsView,
  type BiologyNodeView,
  type BiologyVariant,
  useBiologyAction,
  useNodeBiology,
} from './api'
import { BIOLOGY_ICON, FLAGS, SHARES, VARIANTS } from './labels'

const SHARE_MAX = 500
const YES_NO = { true: 'Yes', false: 'No' }
const ORDINARY = 100
const LEANINGS_SHOWN = 8
const ALL_VARIANTS = Object.keys(VARIANTS) as BiologyVariant[]

const FIELDS: readonly Field[] = [
  ...SHARES.map((share): Field => ({
    key: share.key,
    label: `${share.label} (%)`,
    kind: 'number',
    min: 0,
    max: SHARE_MAX,
  })),
  ...FLAGS.map((flag): Field => ({
    key: flag.key,
    label: flag.label,
    kind: 'pick',
    table: YES_NO,
  })),
]

function named(variants: readonly BiologyVariant[]) {
  return variants.length
    ? variants.map((variant) => VARIANTS[variant].label).join(', ')
    : 'none: an ordinary body'
}

function Flags({ effects }: { effects: BiologyEffectsView }) {
  return (
    <div className='flex min-w-0 flex-wrap gap-2'>
      {FLAGS.map((flag) => (
        <Chip
          key={flag.key}
          icon={flag.icon}
          variant={effects[flag.key] ? 'outline' : 'warning'}
        >
          {flag.label}: {effects[flag.key] ? 'yes' : 'no'}
        </Chip>
      ))}
    </div>
  )
}

const BODY_FLAGS = [
  { key: 'bleeds', label: 'Bleeds', icon: Droplet },
  { key: 'heals', label: 'Heals', icon: HeartPulse },
  { key: 'infects', label: 'Takes infection', icon: Bug },
  { key: 'material', label: 'Material body', icon: Hand },
] as const

function Body({ body }: { body: BiologyBodyView }) {
  const tissue = body.tissue ? TISSUE[body.tissue] : null
  return (
    <div className='flex min-w-0 flex-wrap gap-2'>
      {BODY_FLAGS.map((flag) => (
        <Chip
          key={flag.key}
          icon={flag.icon}
          variant={body[flag.key] ? 'outline' : 'warning'}
        >
          {flag.label}: {body[flag.key] ? 'yes' : 'no'}
        </Chip>
      ))}
      <Chip icon={tissue?.icon ?? Hand}>
        Tissue: {tissue ? tissue.label : 'its own'}
      </Chip>
    </div>
  )
}

function Effects({ data }: { data: BiologyNodeView }) {
  const effects = data.effects
  const derived = data.derived
  return (
    <Bars
      chart='chart-biology'
      title='How this body lives, sickens and holds against an ordinary body'
      legend={[
        { text: 'This biology', variant: 'warning' },
        { text: 'What its variants give', variant: 'outline' },
      ]}
      rows={
        effects
          ? SHARES.map((share) => ({
              key: share.key,
              caption: `${share.label}: ${effects[share.key]}%${derived ? `, its variants ${derived[share.key]}%` : ''}`,
              segments: [{ value: effects[share.key], fill: 'fill-warning' }],
              mark: derived ? derived[share.key] : ORDINARY,
            }))
          : []
      }
      max={SHARE_MAX}
      noun={['effect', 'effects']}
      empty='This thing belongs to no people or species, so no biology reaches it.'
    />
  )
}

function told(shift: number, damped: boolean) {
  const moved = shift ? `${shift > 0 ? '+' : ''}${shift}` : ''
  return [damped ? 'stilled' : '', moved].filter(Boolean).join(', ')
}

function Leanings({ data }: { data: BiologyNodeView }) {
  const page = useShowMore(data.leanings, LEANINGS_SHOWN, LEANINGS_SHOWN * 2)
  if (!data.leanings.length) {
    return <Muted>Its variants give its minds no leanings of their own.</Muted>
  }
  return (
    <div className='flex min-w-0 flex-col gap-2'>
      <div className='flex min-w-0 flex-wrap gap-2'>
        {page.visible.map((leaning) => {
          const bias = BIASES[leaning.bias]
          return (
            <Chip
              key={leaning.bias}
              icon={bias.icon}
              variant={leaning.damped ? 'outline' : 'warning'}
            >
              {`${bias.label}: ${told(leaning.shift, leaning.damped)}`}
            </Chip>
          )
        })}
      </div>
      <ShowMore state={page} />
    </div>
  )
}

const SPECIES = ['species']

function VariantPicker({
  data,
  blocked,
  busy,
  onToggle,
  act,
}: {
  data: BiologyNodeView
  blocked: string | null
  busy: boolean
  onToggle: (variant: BiologyVariant, present: boolean) => void
  act?: ActProp
}) {
  const reason = why(blocked, busy)
  return (
    <div
      role='group'
      aria-label='Biology variants'
      className='grid min-w-0 grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4'
    >
      {ALL_VARIANTS.map((variant) => {
        const named = VARIANTS[variant]
        const Icon = named.icon
        const present = data.variants.includes(variant)
        return (
          <Button
            act={act}
            key={variant}
            size='sm'
            variant={present ? 'default' : 'outline'}
            aria-pressed={present}
            disabled={reason !== null}
            disabledReason={reason ?? undefined}
            onClick={() => onToggle(variant, !present)}
          >
            <Icon />
            {named.label}
          </Button>
        )
      })}
    </div>
  )
}

function PartnerPicker({
  data,
  blocked,
  onSet,
  act,
}: {
  data: BiologyNodeView
  blocked: string | null
  onSet: (partner: number | null) => void
  act?: ActProp
}) {
  const [partner, setPartner] = useState<number | null>(
    data.partner?.id ?? null
  )
  const symbiotic = data.variants.includes('symbiotic')
  const reason =
    blocked ??
    (symbiotic ? null : 'Only a symbiotic kind lives joined to another')
  return (
    <div className='flex min-w-0 flex-wrap items-end gap-2'>
      <NodePicker
        label='Partner kind'
        types={SPECIES}
        value={partner}
        onChange={setPartner}
        blocked={reason}
      />
      <StepButton
        act={act}
        icon={Link2}
        label='Bind it to this kind'
        busy={reason ?? (partner === null ? 'Pick the kind first' : null)}
        onClick={() => onSet(partner)}
      />
      <StepButton
        act={act}
        icon={Unlink}
        label='Free it of its partner'
        busy={reason ?? (data.partner === null ? 'It has no partner' : null)}
        onClick={() => onSet(null)}
      />
    </div>
  )
}

export function BiologySection({
  nodeId,
  readOnlyReason = null,
}: {
  nodeId: number
  readOnlyReason?: string | null
}) {
  const query = useNodeBiology(nodeId)
  const holderId = query.data?.holder?.id ?? null
  const absent = query.data?.absent_reason ?? null
  const editing = useBiologyAction(
    'biology:edit',
    (vars: {
      values: Record<string, number | string | boolean | null>
      release: string[]
    }) => ({
      holder_id: holderId ?? 0,
      ...vars,
    }),
    'The biology keeps its new nature'
  )
  const adding = useBiologyAction(
    'biology_variant:add',
    (variant: BiologyVariant) => ({ holder_id: holderId ?? 0, variant }),
    'The body takes the variant'
  )
  const removing = useBiologyAction(
    'biology_variant:remove',
    (variant: BiologyVariant) => ({ holder_id: holderId ?? 0, variant }),
    'The body loses the variant'
  )
  const resetting = useBiologyAction(
    'biology:reset',
    (_: void) => ({ holder_id: holderId ?? 0 }),
    'The biology returns to what its body shows'
  )
  const running = useBiologyAction(
    'biology_variants:run',
    (_: void) => ({}),
    'Every biology is read'
  )
  const blocked = readOnlyReason ?? absent
  return (
    <Section
      id='section-biology'
      title='Biology: the variants of its body'
      description='The biology of the people or species this thing belongs to: its variants of body and what they do to how much it eats, how many it bears, how it dies and sickens, how it holds in battle, how fire and storms harm it, whether it breathes, drinks, ages and sleeps, and how its minds lean. Peoples, species, their towns, mortals, armies and beasts show the biology of their kind; gods, worlds and stars carry none, and the controls say so.'
      icon={BIOLOGY_ICON}
      tone='verdigris'
    >
      <div
        data-surface='BiologySection'
        className='flex min-w-0 flex-col gap-6'
      >
        {query.isPending ? (
          <LoadingBlock label='Reading the biology of its kind' />
        ) : query.isError ? (
          <EmptyState
            icon={BIOLOGY_ICON}
            size='inline'
            title='This could not be read'
            description={query.error.message}
          />
        ) : (
          <>
            <Facts
              items={[
                [
                  'Kind of life',
                  <Ref
                    key='holder'
                    node={query.data.holder}
                    empty='no people or species'
                  />,
                ],
                ['Variants its body shows', named(query.data.body_variants)],
                [
                  'Kind it lives joined to',
                  <Ref
                    key='partner'
                    node={query.data.partner}
                    empty='none: only a symbiotic kind has a partner'
                  />,
                ],
                [
                  'Set for this kind',
                  query.data.seeded
                    ? `since epoch ${query.data.updated_epoch ?? 0}`
                    : 'not yet: it follows its body',
                ],
              ]}
            />
            {query.data.body && <Body body={query.data.body} />}
            {query.data.effects ? (
              <Flags effects={query.data.effects} />
            ) : (
              <EmptyState
                icon={BIOLOGY_ICON}
                size='inline'
                title='No biology reaches this'
                description={absent ?? ''}
              />
            )}
            <VariantPicker
              act={[adding, removing]}
              data={query.data}
              blocked={blocked}
              busy={adding.isPending || removing.isPending}
              onToggle={(variant, present) =>
                present ? adding.mutate(variant) : removing.mutate(variant)
              }
            />
            <PartnerPicker
              act={editing}
              data={query.data}
              blocked={why(blocked, editing.isPending)}
              onSet={(partner) =>
                editing.mutate({
                  values: { partner_species_id: partner },
                  release: [],
                })
              }
            />
            <Effects data={query.data} />
            <Leanings data={query.data} />
            <RecordEditor
              act={editing}
              title='Set what this biology does'
              note='Every value you set is held against the engine and against the sons until you release it; the variants above still decide every value you leave free.'
              fields={FIELDS}
              locked={query.data.locked}
              busy={why(blocked, editing.isPending)}
              onSave={(values) => editing.mutate({ values, release: [] })}
              onRelease={(keys) =>
                editing.mutate({ values: {}, release: keys })
              }
            />
            <div className='flex min-w-0 flex-wrap gap-2'>
              <StepButton
                act={editing}
                icon={Unlock}
                label='Let the sons reshape its variants'
                busy={why(
                  blocked ??
                    (query.data.locked.includes('variants')
                      ? null
                      : 'Its variants are not held: the sons can already reshape them'),
                  editing.isPending
                )}
                onClick={() =>
                  editing.mutate({ values: {}, release: ['variants'] })
                }
              />
              <StepButton
                act={resetting}
                icon={RotateCcw}
                label='Return it to what its body shows'
                busy={why(blocked, resetting.isPending)}
                onClick={() => resetting.mutate()}
              />
              <StepButton
                act={running}
                icon={BIOLOGY_ICON}
                label='Read every biology now'
                busy={why(readOnlyReason, running.isPending)}
                onClick={() => running.mutate()}
              />
            </div>
          </>
        )}
      </div>
    </Section>
  )
}
