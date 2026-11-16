import { useState } from 'react'
import { Lock, Plus, Unlock, X } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { plural } from '@/lib/units'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import {
  EmptyState,
  EntityLink,
  KpiTile,
  Medallion,
  Paged,
  PagedList,
  Section,
  StatBar,
  ValueRadar,
} from '@/components/domain'
import { type DrawerKind } from '@/components/layout/drawer/drawerEntries'
import { Muted, Text } from '@/components/typography'
import { type AdjustGroup, AdjustStats } from '@/features/pantheon/AdjustStats'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import {
  useVariants,
  variantChoices,
} from '@/features/world-rules/VariantForge'
import {
  type Mind,
  type MindTrait,
  type MindValue,
  type MortalRole,
  type NeedKind,
  type PressureKind,
  type TraitKind,
  signed,
  useMind,
} from '../mind/api'
import {
  HOLDERS,
  LOCKS,
  MIND_ICON,
  NEED_GROUPS,
  NEED_ICONS,
  PRESSURE_ICONS,
  ROLE_ICONS,
  TRAIT_EFFECTS,
  TRAIT_FAMILIES,
  TRAIT_ICONS,
  TRAIT_SOURCES,
  VALUE_ICONS,
  named,
  plain,
  labelTable,
} from '../mind/labels'
import { ControlPanel, MindCard, MindPicker } from '../mind/parts'
import { StressCard } from '../mortal/MortalSections'

const PERCENT = 100
const VALUE_MIN = -100
const VALUE_MAX = 100
const STRONG = 50
const WORKING = 'Working on it.'

function nodeKind(kind: string): DrawerKind {
  if (kind === 'son') return 'son'
  if (kind === 'foreign_god') return 'foreign-god'
  return 'entity'
}

function valueTone(value: number): 'success' | 'destructive' | 'default' {
  if (value >= STRONG) return 'success'
  if (value <= -STRONG) return 'destructive'
  return 'default'
}

function ValueBar({ item }: { item: MindValue }) {
  const spec = named(VALUE_ICONS, item.axis)
  const pole = item.value >= 0 ? item.high_label : item.low_label
  const other = item.value >= 0 ? item.low_label : item.high_label
  const gap = item.reference !== null ? item.value - item.reference : null
  return (
    <div className='flex min-w-0 flex-col gap-0.5'>
      <StatBar
        label={`${pole} (against ${other.toLowerCase()})`}
        value={Math.abs(item.value)}
        max={VALUE_MAX}
        icon={spec.icon}
        tone={valueTone(item.value)}
        showMax={false}
      />
      {gap !== null && gap !== 0 && (
        <Muted variant='caption'>{`${signed(gap)} from the reference`}</Muted>
      )}
    </div>
  )
}

function TraitChip({
  trait,
  onRemove,
  blocked,
}: {
  trait: MindTrait
  onRemove: () => void
  blocked: string | null
}) {
  const spec = named(TRAIT_ICONS, trait.trait)
  const effects = trait.effects.map(
    (item) => `${plain(TRAIT_EFFECTS, item.effect)} ${signed(item.value)}%`
  )
  const capacities = trait.capacities.map(
    (item) => `${plain({}, item.capacity)} ${signed(item.value)}%`
  )
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <div
          tabIndex={0}
          className='flex min-w-0 items-center gap-2 rounded-md border surface-sheen border-gild/60 bg-card px-2 py-1'
        >
          <spec.icon
            aria-hidden='true'
            className='size-icon-sm shrink-0 text-muted-foreground'
          />
          <Text as='span' variant='caption' truncate>
            {trait.label}
          </Text>
          <Muted as='span' variant='caption'>
            {`${named(TRAIT_FAMILIES, trait.family).label} · ${plain(TRAIT_SOURCES, trait.source)}${trait.heritable ? ' · passes to children' : ''}`}
          </Muted>
          <Button
            size='icon-sm'
            variant='ghost'
            aria-label={`Take away ${trait.label}`}
            disabled={blocked !== null}
            disabledReason={blocked ?? undefined}
            onClick={onRemove}
          >
            <X />
          </Button>
        </div>
      </TooltipTrigger>
      <TooltipContent>
        {[...capacities, ...effects].join(' · ') || 'No mechanical effect'}
        {trait.source_node ? ` · from ${trait.source_node.name}` : ''}
        {` · since epoch ${trait.epoch}`}
      </TooltipContent>
    </Tooltip>
  )
}

function MindHero({ mind }: { mind: Mind }) {
  const holder = named(HOLDERS, mind.holder)
  const role = mind.career?.role ? named(ROLE_ICONS, mind.career.role) : null
  return (
    <div className='flex min-w-0 items-center gap-3 rounded-md border surface-framed border-gild/70 bg-card p-3'>
      <Medallion icon={holder.icon} tone={holder.tone ?? 'gold'} />
      <div className='flex min-w-0 flex-1 flex-col gap-1.5'>
        <Text weight='semibold'>{holder.label}</Text>
        <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
          {role && (
            <Badge size='sm' variant='secondary'>
              {mind.career?.fixed ? `${role.label} (by station)` : role.label}
            </Badge>
          )}
          {mind.career?.ended_epoch !== null &&
            mind.career?.ended_epoch !== undefined && (
              <Badge
                size='sm'
                variant='warning'
              >{`A wound ended their old calling in epoch ${mind.career.ended_epoch}`}</Badge>
            )}
          {mind.locked.map((key) => (
            <Badge
              key={key}
              size='sm'
              variant='info'
            >{`Holding ${plain(LOCKS, key)}`}</Badge>
          ))}
        </div>
        {mind.reference && (
          <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
            <Muted variant='caption'>
              {mind.borrowed_from ? 'Its values are those of' : 'Compared with'}
            </Muted>
            <EntityLink
              kind={nodeKind(mind.reference.kind)}
              id={String(mind.reference.id)}
              showIcon
            >
              {mind.reference.name}
            </EntityLink>
          </div>
        )}
      </div>
    </div>
  )
}

function Values({ mind }: { mind: Mind }) {
  if (mind.values.length === 0) return null
  const axes = mind.values.map((item) => ({
    key: item.axis,
    label: named(VALUE_ICONS, item.axis).label,
    value: item.value,
    reference: item.reference,
  }))
  const ordered = [...mind.values].sort(
    (a, b) => Math.abs(b.value) - Math.abs(a.value)
  )
  return (
    <MindCard
      title={plain(labelTable(HOLDERS), mind.holder)}
      icon={MIND_ICON}
      wide
      hint='Each value runs from one pole to its opposite, -100 to +100.'
    >
      <div className='grid min-w-0 grid-cols-1 gap-4 @xl/mind:grid-cols-2'>
        <ValueRadar
          axes={axes}
          label={mind.name}
          referenceLabel={mind.reference?.name ?? null}
        />
        <div className='flex min-w-0 flex-col gap-2'>
          <Paged items={ordered}>
            {(item) => <ValueBar key={item.axis} item={item} />}
          </Paged>
        </div>
      </div>
    </MindCard>
  )
}

function Temperament({
  mind,
  blocked,
}: {
  mind: Mind
  blocked: string | null
}) {
  const remove = useGodAction({
    run: (trait: TraitKind) =>
      unwrap(
        api.POST('/api/actions/mind:trait_remove', {
          body: { node_id: mind.node_id, trait },
        })
      ),
  })
  if (mind.holder !== 'personal' && mind.holder !== 'divine') return null
  return (
    <MindCard
      title='Temperament'
      icon={TRAIT_ICONS.brave.icon}
      hint={`${mind.traits.length} of at most ${plural(mind.max_traits, 'trait', 'traits')}`}
    >
      {mind.traits.length === 0 ? (
        <Muted variant='caption'>No marked traits yet.</Muted>
      ) : (
        <div className='flex min-w-0 flex-wrap gap-1.5'>
          <Paged items={mind.traits}>
            {(trait) => (
              <TraitChip
                key={trait.trait}
                trait={trait}
                blocked={blocked ?? (remove.isPending ? WORKING : null)}
                onRemove={() => remove.mutate(trait.trait)}
              />
            )}
          </Paged>
        </div>
      )}
    </MindCard>
  )
}

function importanceNote(importance: number): string {
  if (importance >= 150) return 'matters a great deal'
  if (importance >= 110) return 'matters more than most'
  if (importance >= 90) return 'matters as much as to anyone'
  if (importance >= 60) return 'matters less than most'
  return 'hardly matters to them'
}

function Needs({ mind }: { mind: Mind }) {
  if (mind.needs.length === 0) return null
  return (
    <MindCard
      title='Needs'
      icon={NEED_ICONS.belonging.icon}
      hint='How well each need is met, and how much it matters to this one. Low values press the mortal to act and darken their thoughts.'
      wide
    >
      <div className='grid min-w-0 grid-cols-1 gap-4 @xl/mind:grid-cols-2'>
        {Object.entries(NEED_GROUPS).map(([group, spec]) => {
          const items = mind.needs.filter((item) => item.group === group)
          return items.length > 0 ? (
            <div key={group} className='flex min-w-0 flex-col gap-2'>
              <div className='flex min-w-0 items-center gap-2'>
                <Medallion icon={spec.icon} size='sm' />
                <Text weight='semibold'>{spec.label}</Text>
              </div>
              <Paged items={items} initial={4} noun={['need', 'needs']}>
                {(item) => (
                  <div
                    key={item.need}
                    className='flex min-w-0 flex-col gap-0.5'
                  >
                    <StatBar
                      label={item.label}
                      value={item.value}
                      max={PERCENT}
                      icon={named(NEED_ICONS, item.need).icon}
                      tone={
                        item.value < PERCENT / 4
                          ? 'destructive'
                          : item.value < PERCENT / 2
                            ? 'warning'
                            : 'success'
                      }
                    />
                    <Muted variant='caption'>
                      {`${importanceNote(item.importance)} (${item.importance}%)`}
                    </Muted>
                  </div>
                )}
              </Paged>
            </div>
          ) : null
        })}
      </div>
    </MindCard>
  )
}

function Pressures({ mind }: { mind: Mind }) {
  if (mind.pressures.length === 0) return null
  return (
    <MindCard
      title='Pressures'
      icon={PRESSURE_ICONS.insecurity.icon}
      wide
      hint='What weighs on this community; they drive migration, revolt, war, conversion and new factions.'
    >
      <div className='grid min-w-0 grid-cols-1 gap-3 @md/mind:grid-cols-2 @3xl/mind:grid-cols-4'>
        {mind.pressures.map((item) => {
          const spec = named(PRESSURE_ICONS, item.pressure)
          return (
            <KpiTile
              key={item.pressure}
              label={item.label}
              value={item.value}
              icon={spec.icon}
              tone={
                item.value >= STRONG
                  ? 'danger'
                  : item.value >= PERCENT / 4
                    ? 'warning'
                    : 'success'
              }
              meter={{ value: item.value, max: PERCENT, label: item.label }}
            />
          )
        })}
      </div>
    </MindCard>
  )
}

function valueGroups(mind: Mind): AdjustGroup[] {
  const groups: AdjustGroup[] = []
  if (mind.values.length > 0 && mind.holder !== 'community')
    groups.push({
      title: 'Values (-100 to +100)',
      fields: mind.values.map((item) => ({
        key: `value:${item.axis}`,
        label: named(VALUE_ICONS, item.axis).label,
        value: item.value,
        min: VALUE_MIN,
        max: VALUE_MAX,
      })),
    })
  if (mind.needs.length > 0)
    groups.push({
      title: 'Needs (0 to 100, how well met)',
      fields: mind.needs.map((item) => ({
        key: `need:${item.need}`,
        label: item.label,
        value: item.value,
        min: 0,
        max: PERCENT,
      })),
    })
  if (mind.pressures.length > 0)
    groups.push({
      title: 'Pressures (0 to 100)',
      fields: mind.pressures.map((item) => ({
        key: `pressure:${item.pressure}`,
        label: item.label,
        value: item.value,
        min: 0,
        max: PERCENT,
      })),
    })
  return groups
}

function MindControls({ mind }: { mind: Mind }) {
  const { reason } = useGodGate()
  const [hold, setHold] = useState(true)
  const [trait, setTrait] = useState<string>('')
  const set = ({ key, value }: { key: string; value: number }) => {
    const [kind, name] = key.split(':')
    if (kind === 'value')
      return unwrap(
        api.POST('/api/actions/mind:values', {
          body: {
            node_id: mind.node_id,
            values: { [name]: value },
            lock: hold,
          },
        })
      )
    if (kind === 'need')
      return unwrap(
        api.POST('/api/actions/mind:need', {
          body: {
            node_id: mind.node_id,
            need: name as NeedKind,
            value,
            lock: hold,
          },
        })
      )
    return unwrap(
      api.POST('/api/actions/mind:pressure', {
        body: {
          node_id: mind.node_id,
          pressure: name as PressureKind,
          value,
          lock: hold,
        },
      })
    )
  }
  const release = useGodAction({
    run: (field: string) =>
      unwrap(
        api.POST('/api/actions/mind:unlock', {
          body: { node_id: mind.node_id, field },
        })
      ),
  })
  const lock = useGodAction({
    run: (field: string) =>
      unwrap(
        api.POST('/api/actions/mind:lock', {
          body: { node_id: mind.node_id, field },
        })
      ),
  })
  const variants = useVariants()
  const [variant, setVariant] = useState('')
  const give = useGodAction({
    run: (picked: TraitKind) =>
      unwrap(
        api.POST('/api/actions/mind:trait', {
          body: {
            node_id: mind.node_id,
            trait: picked,
            variant_id: variant === '' ? null : Number(variant),
          },
        })
      ),
    onDone: () => setTrait(''),
  })
  const role = useGodAction({
    run: (picked: MortalRole) =>
      unwrap(
        api.POST('/api/actions/mind:role', {
          body: { node_id: mind.node_id, role: picked, lock: hold },
        })
      ),
  })
  const busy =
    reason() ??
    (release.isPending || lock.isPending || give.isPending || role.isPending
      ? WORKING
      : null)
  const held = new Set(mind.locked)
  const traitChoices = Object.fromEntries(
    Object.entries(labelTable(TRAIT_ICONS)).filter(
      ([key]) => !mind.traits.some((item) => item.trait === key)
    )
  )
  const full = mind.traits.length >= mind.max_traits
  const personal = mind.holder === 'personal' || mind.holder === 'divine'
  return (
    <ControlPanel
      title='Shape this mind'
      note='Set values, needs and pressures, give or take traits and choose a calling. A held part stops changing with the world until you release it. Every change goes into the ledger and can be undone.'
      hold={hold}
      onHold={setHold}
    >
      <PagedList
        items={mind.lockable}
        initial={12}
        noun={['entry', 'entries']}
        as='div'
        className='flex min-w-0 flex-wrap items-center gap-2'
        itemKey={(field) => field}
      >
        {(field) =>
          held.has(field) ? (
            <Button
              key={field}
              size='sm'
              variant='outline'
              disabled={busy !== null}
              disabledReason={busy ?? undefined}
              onClick={() => release.mutate(field)}
            >
              <Unlock />
              {`Release ${plain(LOCKS, field)}`}
            </Button>
          ) : (
            <Button
              key={field}
              size='sm'
              variant='ghost'
              disabled={busy !== null}
              disabledReason={busy ?? undefined}
              onClick={() => lock.mutate(field)}
            >
              <Lock />
              {`Hold ${plain(LOCKS, field)}`}
            </Button>
          )
        }
      </PagedList>
      {personal && (
        <div className='grid min-w-0 grid-cols-1 gap-3 @md/mind:grid-cols-2'>
          <div className='flex min-w-0 items-end gap-2'>
            <div className='min-w-0 flex-1'>
              <MindPicker
                label='Give a trait'
                value={trait}
                table={traitChoices}
                blocked={
                  busy ??
                  (full ? 'This mind holds as many traits as it can.' : null)
                }
                placeholder='Choose a trait'
                onPick={setTrait}
              />
            </div>
            <Button
              size='sm'
              disabled={busy !== null || trait === '' || full}
              disabledReason={
                busy ??
                (full
                  ? 'This mind holds as many traits as it can.'
                  : 'Choose a trait first.')
              }
              onClick={() => give.mutate(trait as TraitKind)}
            >
              <Plus />
              Give
            </Button>
          </div>
          {trait !== '' &&
            Object.keys(variantChoices(variants.data, 'trait', trait)).length >
              0 && (
              <MindPicker
                label='Of a kind made in this world'
                value={variant}
                table={variantChoices(variants.data, 'trait', trait)}
                blocked={busy}
                placeholder='The plain kind'
                onPick={setVariant}
              />
            )}
          {mind.career && (
            <MindPicker
              label='Calling'
              value={mind.career.role ?? ''}
              table={labelTable(ROLE_ICONS)}
              blocked={busy}
              onPick={(value) => role.mutate(value as MortalRole)}
            />
          )}
        </div>
      )}
      <AdjustStats
        id={`mind-${mind.node_id}`}
        groups={valueGroups(mind)}
        note='Values run from -100 to +100; needs and pressures from 0 to 100.'
        run={set}
      />
    </ControlPanel>
  )
}

export function MindSection({ nodeId }: { nodeId: number }) {
  const { reason } = useGodGate()
  const query = useMind(nodeId)
  const mind = query.data
  return (
    <Section
      id='section-mind'
      title='Mind'
      description='What this one values, what temper it has, what it needs or what presses on it. Values drift with neighbours, rulers, gods and what they live through.'
      icon={MIND_ICON}
    >
      {!mind ? (
        <EmptyState
          icon={MIND_ICON}
          title='No mind yet'
          description='The next epoch gives this one values, a temper and needs.'
        />
      ) : (
        <div className='@container/mind flex min-w-0 flex-col gap-4'>
          <MindHero mind={mind} />
          <div className='grid min-w-0 grid-cols-1 gap-3 @xl/mind:grid-cols-2'>
            <Values mind={mind} />
            <Temperament mind={mind} blocked={reason()} />
            <Needs mind={mind} />
            <Pressures mind={mind} />
            {mind.holder === 'personal' && (
              <StressCard mortalId={mind.node_id} />
            )}
          </div>
          <MindControls mind={mind} />
        </div>
      )}
    </Section>
  )
}
