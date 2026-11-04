import { useState } from 'react'
import {
  Crown,
  Flame,
  Handshake,
  Link,
  Plus,
  Ruler,
  Scale,
  Shuffle,
  Trash2,
  Unlink,
  Users,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { formatInteger } from '@/lib/format'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label as FieldLabel } from '@/components/ui/label'
import {
  EmptyState,
  KpiTile,
  Medallion,
  MiniStat,
  Section,
  Timeline,
  TimelineItem,
  type TimelineTone,
  Paged,
} from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { named } from '../environment/labels'
import { VALUE_ICONS } from '../mind/labels'
import { useSocietyDepth } from './depthApi'
import {
  CAUSE_ORDER,
  CAUSE_SPEC,
  type DriftCause,
  EVENT_SPEC,
  PART_SPEC,
  type SocietyDepth,
  standingLabel,
} from './depthLabels'
import { CLASS_SPEC, type SocialClass, type Spec } from './labels'
import {
  AdjustPanel,
  EditorGroup,
  HeldStrip,
  IconPicker,
  NumberEditor,
  Panel,
} from './parts'
import { WORKING, goodTone } from './tones'

type Loyalty = SocietyDepth['loyalty'][number]
type Imposition = SocietyDepth['impositions'][number]

const PERCENT = 100
const SWING = 100
const MOST_EPOCHS = 1000
const AXES = Object.fromEntries(
  Object.entries(VALUE_ICONS).map(([key, value]) => [key, value as Spec])
)
const TIMELINE_TONE: Record<string, TimelineTone> = {
  gold: 'primary',
  success: 'success',
  warning: 'warning',
  danger: 'destructive',
}

function signed(value: number): string {
  return value > 0 ? `+${value}` : String(value)
}

function ImpositionRow({
  row,
  blocked,
}: {
  row: Imposition
  blocked: string | null
}) {
  const edit = useGodAction({
    run: (amount: number) =>
      unwrap(
        api.POST('/api/actions/drift:edit', {
          body: { imposition_id: row.id, amount },
        })
      ),
  })
  const cancel = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/drift:cancel', {
          body: { imposition_id: row.id },
        })
      ),
  })
  const cause = CAUSE_SPEC[row.cause]
  const axis = named(VALUE_ICONS, row.axis)
  const busy = blocked ?? (edit.isPending || cancel.isPending ? WORKING : null)
  return (
    <div className='flex min-w-0 flex-wrap items-center gap-2.5 rounded-lg border bg-card p-2.5'>
      <Medallion icon={cause.icon} tone={cause.tone} size='sm' />
      <div className='flex min-w-0 flex-1 basis-40 flex-col'>
        <Text as='span' weight='medium' truncate>
          {`${cause.label}: ${axis.label} ${signed(row.amount)}`}
        </Text>
        <Muted as='span' variant='caption'>
          {`${row.epochs_left} epochs left`}
        </Muted>
      </div>
      <Button
        size='sm'
        variant='outline'
        disabled={busy !== null || row.amount <= -SWING}
        disabledReason={busy ?? 'At the weakest.'}
        onClick={() => edit.mutate(row.amount - 1)}
      >
        −1
      </Button>
      <Button
        size='sm'
        variant='outline'
        disabled={busy !== null || row.amount >= SWING}
        disabledReason={busy ?? 'At the strongest.'}
        onClick={() => edit.mutate(row.amount + 1)}
      >
        +1
      </Button>
      <Button
        size='sm'
        variant='ghost'
        aria-label='Lift this pressure'
        disabled={busy !== null}
        disabledReason={busy ?? undefined}
        onClick={() => cancel.mutate(undefined)}
      >
        <Trash2 />
      </Button>
    </div>
  )
}

function ImposeDrift({
  view,
  blocked,
}: {
  view: SocietyDepth
  blocked: string | null
}) {
  const [cause, setCause] = useState<string>('famine')
  const [axis, setAxis] = useState<string>('kinship')
  const [amount, setAmount] = useState('5')
  const [epochs, setEpochs] = useState('3')
  const impose = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/drift:impose', {
          body: {
            community_id: view.entity_id,
            cause: cause as DriftCause,
            axis: axis as SocietyDepth['drift_causes'][number]['axis'],
            amount: Number(amount),
            epochs: Number(epochs),
          },
        })
      ),
  })
  const busy = blocked ?? (impose.isPending ? WORKING : null)
  const shift = Number(amount)
  const span = Number(epochs)
  const invalid =
    !Number.isInteger(shift) ||
    shift === 0 ||
    Math.abs(shift) > SWING ||
    !Number.isInteger(span) ||
    span < 1 ||
    span > MOST_EPOCHS
  return (
    <EditorGroup title='Press an experience on them' icon={Shuffle} pairs>
      <IconPicker
        label='Experience'
        value={cause}
        table={CAUSE_SPEC}
        blocked={busy}
        onPick={setCause}
      />
      <IconPicker
        label='Value'
        value={axis}
        table={AXES}
        blocked={busy}
        onPick={setAxis}
      />
      <div className='flex min-w-0 flex-col gap-1.5'>
        <FieldLabel htmlFor={`drift-amount-${view.entity_id}`}>
          Push each epoch
        </FieldLabel>
        <Input
          id={`drift-amount-${view.entity_id}`}
          type='number'
          min={-SWING}
          max={SWING}
          value={amount}
          disabled={busy !== null}
          onChange={(event) => setAmount(event.target.value)}
        />
      </div>
      <div className='flex min-w-0 flex-col gap-1.5'>
        <FieldLabel htmlFor={`drift-epochs-${view.entity_id}`}>
          For how many epochs
        </FieldLabel>
        <Input
          id={`drift-epochs-${view.entity_id}`}
          type='number'
          min={1}
          max={MOST_EPOCHS}
          value={epochs}
          disabled={busy !== null}
          onChange={(event) => setEpochs(event.target.value)}
        />
      </div>
      <div className='col-span-full flex min-w-0 justify-end'>
        <Button
          size='sm'
          disabled={busy !== null || invalid}
          disabledReason={
            busy ??
            'Push by a whole number from −100 to 100, for 1 to 1000 epochs.'
          }
          onClick={() => impose.mutate(undefined)}
        >
          <Plus />
          Press it on them
        </Button>
      </div>
    </EditorGroup>
  )
}

export function CultureDriftSection({
  communityId,
  readOnlyReason,
}: {
  communityId: number
  readOnlyReason?: string | null
}) {
  const view = useSocietyDepth(communityId)
  const { reason } = useGodGate()
  const blocked = readOnlyReason ?? reason()
  const data = view.data
  if (!data) return null
  const causes = CAUSE_ORDER.map((cause) => ({
    cause,
    rows: data.drift_causes.filter(
      (row) => row.cause === cause && row.amount !== 0
    ),
    total: data.drift_causes
      .filter((row) => row.cause === cause)
      .reduce((sum, row) => sum + Math.abs(row.total), 0),
  })).filter((item) => item.rows.length > 0 || item.total > 0)
  const strongest = [...causes].sort(
    (left, right) =>
      right.rows.reduce((sum, row) => sum + Math.abs(row.amount), 0) -
      left.rows.reduce((sum, row) => sum + Math.abs(row.amount), 0)
  )[0]
  return (
    <Section
      id='section-culture-drift'
      title='What moves their values'
      description='Each epoch their values drift under their god, rulers, neighbours, scholars and what they live through: famine binds clans tighter, a cohesive people grows warlike in defeat, a loose one turns to peace.'
      icon={Shuffle}
    >
      <div
        data-surface='CultureDrift'
        className='@container/drift flex min-w-0 flex-col gap-4'
      >
        {causes.length === 0 && data.impositions.length === 0 ? (
          <EmptyState
            icon={Shuffle}
            title='Nothing has moved them yet'
            description='The causes of their drift are written at the end of the next epoch.'
          />
        ) : (
          <>
            <div className='grid min-w-0 grid-cols-2 gap-3 @xl/drift:grid-cols-3'>
              <KpiTile
                label='Strongest pull'
                value={strongest ? CAUSE_SPEC[strongest.cause].label : 'None'}
                icon={strongest ? CAUSE_SPEC[strongest.cause].icon : Shuffle}
                tone={
                  strongest
                    ? (CAUSE_SPEC[strongest.cause].tone ?? 'gold')
                    : 'muted'
                }
                hint='What moved them most this epoch'
              />
              <KpiTile
                label='Pulls at work'
                value={causes.filter((item) => item.rows.length > 0).length}
                icon={Scale}
                tone='info'
                hint='Kinds of pressure on their values this epoch'
              />
              <KpiTile
                label='Pressed by you'
                value={data.impositions.length}
                icon={Plus}
                tone={data.impositions.length > 0 ? 'gold' : 'muted'}
                hint='Experiences you press on them'
              />
            </div>
            <div className='grid min-w-0 grid-cols-1 gap-2 @xl/drift:grid-cols-2'>
              <Paged items={causes}>
                {({ cause, rows, total }) => {
                  const spec = CAUSE_SPEC[cause]
                  return (
                    <Panel
                      key={cause}
                      title={spec.label}
                      icon={spec.icon}
                      tone={spec.tone}
                      hint={`${formatInteger(total)} points of change so far`}
                    >
                      <div className='flex min-w-0 flex-wrap gap-1.5'>
                        {rows.length === 0 && (
                          <Muted variant='caption'>Quiet this epoch.</Muted>
                        )}
                        <Paged items={rows}>
                          {(row) => {
                            const axis = named(VALUE_ICONS, row.axis)
                            return (
                              <Badge
                                key={row.axis}
                                size='sm'
                                variant={
                                  row.amount > 0 ? 'success' : 'destructive'
                                }
                              >
                                <axis.icon />
                                {`${axis.label} ${signed(row.amount)}`}
                              </Badge>
                            )
                          }}
                        </Paged>
                      </div>
                    </Panel>
                  )
                }}
              </Paged>
            </div>
          </>
        )}
        <AdjustPanel
          title='Shape their values'
          note='Press an experience on them, a famine, a defeat, a creed, that pushes one value each epoch for as long as you say. Change or lift it at any time; every change can be undone from the ledger.'
        >
          {data.impositions.length > 0 && (
            <div className='flex min-w-0 flex-col gap-2'>
              <Paged items={data.impositions}>
                {(row) => (
                  <ImpositionRow key={row.id} row={row} blocked={blocked} />
                )}
              </Paged>
            </div>
          )}
          <ImposeDrift view={data} blocked={blocked} />
        </AdjustPanel>
      </div>
    </Section>
  )
}

function LoyaltyCard({
  view,
  row,
  blocked,
}: {
  view: SocietyDepth
  row: Loyalty
  blocked: string | null
}) {
  const edit = useGodAction({
    run: ({ key, value }: { key: string; value: number }) =>
      unwrap(
        api.POST('/api/actions/loyalty:edit', {
          body: {
            polity_id: row.polity_id,
            member_id: view.entity_id,
            values: { [key]: value },
            release: [],
          },
        })
      ),
    success: (_result, change) => `${standingLabel(change.key)} held`,
  })
  const release = useGodAction({
    run: (keys: string[]) =>
      unwrap(
        api.POST('/api/actions/loyalty:edit', {
          body: {
            polity_id: row.polity_id,
            member_id: view.entity_id,
            values: {},
            release: keys,
          },
        })
      ),
    success: 'Their loyalty follows the world again',
  })
  const busy = blocked ?? (release.isPending ? WORKING : null)
  const steps = [
    { label: 'Value distance', value: -row.distance_penalty, icon: Ruler },
    { label: 'Grievances', value: -row.grievances, icon: Flame },
    { label: 'Benefits', value: row.benefits, icon: Handshake },
    { label: 'Classes content', value: row.satisfaction, icon: Users },
  ]
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      <div className='grid min-w-0 grid-cols-2 gap-3 @xl/loyal:grid-cols-4'>
        <KpiTile
          label={`Loyalty to ${row.polity}`}
          value={row.loyalty}
          icon={Crown}
          tone={goodTone(row.loyalty)}
          meter={{ value: row.loyalty, max: PERCENT, label: 'Loyalty' }}
          hint={
            row.locked.includes('loyalty')
              ? 'Held by you'
              : 'Base, less distance and grievances, plus benefits and content'
          }
        />
        <KpiTile
          label='Autonomy'
          value={row.autonomy}
          icon={Unlink}
          tone={row.autonomy >= 60 ? 'danger' : 'muted'}
          hint='How far they go their own way; at the limit they break away'
        />
        <KpiTile
          label='Value distance'
          value={row.value_distance}
          icon={Ruler}
          tone={row.value_distance > 60 ? 'warning' : 'muted'}
          hint='How far their values lie from the ruler’s'
        />
        <KpiTile
          label='Net of grievance and benefit'
          value={signed(row.benefits - row.grievances)}
          icon={Scale}
          tone={row.benefits >= row.grievances ? 'success' : 'danger'}
        />
      </div>
      <Panel
        title='How loyalty is reckoned'
        icon={Scale}
        hint='Every term pushes their loyalty up or down'
      >
        <div className='grid min-w-0 grid-cols-2 gap-2 @xl/loyal:grid-cols-4'>
          {steps.map((step) => (
            <MiniStat
              key={step.label}
              icon={step.icon}
              label={step.label}
              value={signed(step.value)}
              tone={
                step.value > 0 ? 'success' : step.value < 0 ? 'danger' : 'muted'
              }
            />
          ))}
        </div>
        <div className='flex min-w-0 flex-wrap gap-1.5'>
          {row.parts.length === 0 && (
            <Muted variant='caption'>
              No grievance or benefit weighs on them.
            </Muted>
          )}
          <Paged items={row.parts}>
            {(part) => {
              const spec = PART_SPEC[part.part]
              return (
                <Badge
                  key={part.part}
                  size='sm'
                  variant={part.grievance ? 'destructive' : 'success'}
                >
                  <spec.icon />
                  {`${spec.label} ${part.grievance ? '−' : '+'}${part.value}`}
                </Badge>
              )
            }}
          </Paged>
        </div>
      </Panel>
      <AdjustPanel
        title='Bind or loosen them'
        note='Set and hold their grievances, benefits or loyalty itself. Low loyalty drives them toward autonomy and secession; every change can be undone from the ledger.'
      >
        <HeldStrip
          keys={row.locked}
          labelOf={standingLabel}
          blocked={busy}
          onRelease={(keys) => release.mutate(keys)}
        />
        <EditorGroup title='The terms' icon={Scale}>
          {(['grievances', 'benefits', 'loyalty'] as const).map((key) => (
            <NumberEditor
              key={`${key}-${row[key]}`}
              id={`loyalty-${row.polity_id}-${view.entity_id}`}
              field={{
                key,
                label: standingLabel(key),
                icon:
                  key === 'grievances'
                    ? Flame
                    : key === 'benefits'
                      ? Handshake
                      : Crown,
                value: row[key],
                min: 0,
                max: key === 'loyalty' ? PERCENT : 10000,
              }}
              held={row.locked.includes(key)}
              blocked={blocked}
              pending={edit.isPending && edit.variables?.key === key}
              onSet={(value) => edit.mutate({ key, value })}
            />
          ))}
        </EditorGroup>
      </AdjustPanel>
    </div>
  )
}

export function LoyaltySection({
  communityId,
  readOnlyReason,
}: {
  communityId: number
  readOnlyReason?: string | null
}) {
  const view = useSocietyDepth(communityId)
  const { reason } = useGodGate()
  const blocked = readOnlyReason ?? reason()
  const data = view.data
  if (!data || data.loyalty.length === 0) return null
  return (
    <Section
      id='section-loyalty'
      title='Loyalty to the realm'
      description='Loyalty is the distance of their values from the ruler’s, less their grievances, plus what the realm gives them and how content their classes are.'
      icon={Crown}
    >
      <div
        data-surface='LoyaltyBreakdown'
        className='@container/loyal flex min-w-0 flex-col gap-5'
      >
        <Paged items={data.loyalty}>
          {(row) => (
            <LoyaltyCard
              key={row.polity_id}
              view={data}
              row={row}
              blocked={blocked}
            />
          )}
        </Paged>
      </div>
    </Section>
  )
}

function MobilityControls({
  view,
  blocked,
  mortal,
}: {
  view: SocietyDepth
  blocked: string | null
  mortal: boolean
}) {
  const [count, setCount] = useState('50')
  const [socialClass, setSocialClass] = useState<string>('farmer')
  const move = useGodAction({
    run: (kind: 'enslave' | 'manumit') =>
      kind === 'enslave'
        ? unwrap(
            api.POST('/api/actions/mobility:enslave', {
              body: {
                community_id: view.entity_id,
                count: Number(count),
                source: socialClass as SocialClass,
              },
            })
          )
        : unwrap(
            api.POST('/api/actions/mobility:manumit', {
              body: {
                community_id: view.entity_id,
                count: Number(count),
                target: socialClass as SocialClass,
              },
            })
          ),
  })
  const person = useGodAction({
    run: (kind: 'ennoble' | 'ruin' | 'bind') =>
      kind === 'ennoble'
        ? unwrap(
            api.POST('/api/actions/mobility:ennoble', {
              body: { mortal_id: view.entity_id },
            })
          )
        : unwrap(
            api.POST('/api/actions/mobility:ruin', {
              body: { mortal_id: view.entity_id, bondage: kind === 'bind' },
            })
          ),
  })
  const busy = blocked ?? (move.isPending || person.isPending ? WORKING : null)
  if (mortal)
    return (
      <EditorGroup title='Raise or ruin them' icon={Crown} pairs>
        <Button
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => person.mutate('ennoble')}
        >
          <Crown />
          Raise among the nobles
        </Button>
        <Button
          size='sm'
          variant='outline'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => person.mutate('ruin')}
        >
          <Flame />
          Ruin them
        </Button>
        <Button
          size='sm'
          variant='outline'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => person.mutate('bind')}
        >
          <Link />
          Sell them into bondage
        </Button>
      </EditorGroup>
    )
  const parsed = Number(count)
  const invalid = !Number.isInteger(parsed) || parsed < 1
  const free = Object.fromEntries(
    Object.entries(CLASS_SPEC).filter(([key]) => key !== 'serf_or_slave')
  )
  return (
    <EditorGroup title='Chain or free' icon={Link} pairs>
      <IconPicker
        label='Free class'
        value={socialClass}
        table={free}
        blocked={busy}
        onPick={setSocialClass}
      />
      <div className='flex min-w-0 flex-col gap-1.5'>
        <FieldLabel htmlFor={`mobility-count-${view.entity_id}`}>
          How many
        </FieldLabel>
        <Input
          id={`mobility-count-${view.entity_id}`}
          type='number'
          min={1}
          value={count}
          disabled={busy !== null}
          onChange={(event) => setCount(event.target.value)}
        />
      </div>
      <Button
        size='sm'
        variant='outline'
        disabled={busy !== null || invalid}
        disabledReason={busy ?? 'Give a whole number of people.'}
        onClick={() => move.mutate('enslave')}
      >
        <Link />
        Put them in chains
      </Button>
      <Button
        size='sm'
        disabled={busy !== null || invalid}
        disabledReason={busy ?? 'Give a whole number of people.'}
        onClick={() => move.mutate('manumit')}
      >
        <Unlink />
        Set the bound free into this class
      </Button>
    </EditorGroup>
  )
}

export function MobilitySection({
  entityId,
  mortal = false,
  readOnlyReason,
}: {
  entityId: number
  mortal?: boolean
  readOnlyReason?: string | null
}) {
  const view = useSocietyDepth(entityId)
  const { reason } = useGodGate()
  const blocked = readOnlyReason ?? reason()
  const data = view.data
  if (!data) return null
  const counts = Object.fromEntries(
    Object.keys(EVENT_SPEC).map((event) => [
      event,
      data.mobility
        .filter((row) => row.event === event)
        .reduce((sum, row) => sum + row.count, 0),
    ])
  )
  return (
    <Section
      id='section-mobility'
      title='Rise and fall'
      description='Heroes raised among the nobles found houses; captives are chained, the bound are freed, the indebted are ruined. Each is remembered and written down.'
      icon={Shuffle}
    >
      <div
        data-surface='MobilityHistory'
        className='@container/mob flex min-w-0 flex-col gap-4'
      >
        {!mortal && (
          <div className='grid min-w-0 grid-cols-2 gap-2 @xl/mob:grid-cols-4'>
            {Object.entries(EVENT_SPEC).map(([event, spec]) => (
              <MiniStat
                key={event}
                icon={spec.icon}
                label={spec.label}
                value={formatInteger(counts[event] ?? 0)}
                tone={(counts[event] ?? 0) > 0 ? spec.tone : 'muted'}
              />
            ))}
          </div>
        )}
        {data.mobility.length === 0 ? (
          <EmptyState
            icon={Shuffle}
            title='No one has risen or fallen'
            description='Ennoblements, chains, freedom and ruin are written here as they happen.'
          />
        ) : (
          <Timeline label='Rise and fall'>
            <Paged items={data.mobility} as='li'>
              {(row, index) => {
                const spec = EVENT_SPEC[row.event]
                const who = row.mortal || `${formatInteger(row.count)} people`
                return (
                  <TimelineItem
                    key={row.id}
                    icon={spec.icon}
                    tone={TIMELINE_TONE[spec.tone ?? 'muted'] ?? 'default'}
                    title={`${spec.label}: ${who}`}
                    timestamp={`Epoch ${row.epoch}${row.by_hand ? ' · by your hand' : ''}`}
                    last={index === data.mobility.length - 1}
                  >
                    {(row.house || row.other) && (
                      <Muted variant='caption'>
                        {[
                          row.house && `founded ${row.house}`,
                          row.other && `with ${row.other}`,
                        ]
                          .filter(Boolean)
                          .join('; ')}
                      </Muted>
                    )}
                  </TimelineItem>
                )
              }}
            </Paged>
          </Timeline>
        )}
        <AdjustPanel
          title={mortal ? 'Their fortune' : 'Bondage and freedom'}
          note='Every rise and fall is written in the chronicle and remembered; every change can be undone from the ledger.'
        >
          <MobilityControls view={data} blocked={blocked} mortal={mortal} />
        </AdjustPanel>
      </div>
    </Section>
  )
}
