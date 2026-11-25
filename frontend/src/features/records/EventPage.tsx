import { useMemo } from 'react'
import {
  ArrowRight,
  Calendar,
  Clock,
  FileText,
  Footprints,
  GitBranch,
  History,
  Layers,
  MapPin,
  MessageCircle,
  ScrollText,
  Users,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { damageTypeValues } from '@/api/generated/schema'
import { formatDateTime } from '@/lib/format'
import {
  EmptyState,
  EntityLink,
  KpiTile,
  LoadingBlock,
  Medallion,
  PanelGrid,
  Section,
  ShowMore,
  Timeline,
  TimelineItem,
  useShowMore,
} from '@/components/domain'
import { type EntryPageProps } from '@/components/layout/entry/EntryWindow'
import { useEntryStack } from '@/components/layout/entry/useEntryStack'
import { Muted, Text } from '@/components/typography'
import { Chip, Facts, RecordRow } from '@/features/cosmography/parts'
import { wordOf } from '@/features/entity/affairs/labels'
import { named } from '@/features/entity/environment/labels'
import { useGodAction } from '@/features/pantheon/godAction'
import { AuthorMark } from '@/features/team/AuthorMark'
import { IncidentNameForge } from './IncidentNameForge'
import {
  type EventAccount,
  type EventChange,
  type EventDistortion,
  type EventFact,
  type EventLink,
  type EventParticipant,
  type EventRumour,
  type EventStep,
  type EventTerm,
  useEventAccount,
} from './api'
import {
  ChangeControls,
  FactEditor,
  FactForge,
  HoldBar,
  IncidentEditor,
  StepEditor,
  StepForge,
  StruckButton,
  WitnessEditor,
  WitnessForge,
} from './forges'
import { amountText, changeTitle, momentText, spokenKey } from './format'
import {
  INCIDENT_ROLE,
  INCIDENT_TIER,
  PROCESS_GROUP,
  RUMOUR_DISTORTION,
  STEP_ACTION,
  STEP_OUTCOME,
  STEP_STATE,
  WITNESS_MODE,
} from './labels'
import { ChangeSide, FactValueText, NodeRef } from './parts'
import { timelineTone } from './tones'
import { useBlocked } from './useBlocked'

const SHOWN = 8

function Participants({ people }: { people: readonly EventParticipant[] }) {
  const shown = useShowMore(people, SHOWN)
  if (!people.length)
    return (
      <EmptyState
        icon={Users}
        size='inline'
        title='No one is named in it'
        description='Name who took part with the roles they held from the incident forge in their entry.'
      />
    )
  return (
    <>
      <ul className='grid min-w-0 grid-cols-1 gap-2 @lg/event:grid-cols-2'>
        {shown.visible.map((person) => {
          const role = named(INCIDENT_ROLE, person.role)
          return (
            <li
              key={`${person.node_id}-${person.role}`}
              className='flex min-w-0 items-center gap-2 rounded-md border surface-sheen border-gild/60 bg-card p-2'
            >
              <Medallion icon={role.icon} tone={role.tone} size='sm' />
              <div className='flex min-w-0 flex-col'>
                <NodeRef id={person.node_id} name={person.name} />
                <Muted variant='caption'>{role.label}</Muted>
              </div>
            </li>
          )
        })}
      </ul>
      <ShowMore state={shown} noun={['person', 'people']} />
    </>
  )
}

function FactRows({
  facts,
  account,
  blocked,
}: {
  facts: readonly EventFact[]
  account: EventAccount
  blocked: string | null
}) {
  const strike = useGodAction<number>({
    writes: [{ lever: 'incident_fact:delete' }],
    run: (factId) =>
      unwrap(
        api.POST('/api/actions/incident_fact:delete', {
          body: { incident_fact_id: factId },
        })
      ),
    success: 'The fact is struck from the account',
  })
  const held = account.locked.includes('facts')
  const busy =
    blocked ??
    (held ? 'The facts of this happening are held' : null) ??
    (strike.isPending ? 'A fact is being struck.' : null)
  const shown = useShowMore(facts, SHOWN)
  if (!facts.length)
    return (
      <EmptyState
        icon={ScrollText}
        size='inline'
        title='No facts are kept for it'
        description='It was set down as a line only. Set down its facts below.'
      />
    )
  return (
    <>
      <ul className='flex min-w-0 flex-col gap-2'>
        {shown.visible.map((fact, index) => (
          <RecordRow
            key={`${fact.key}-${fact.position}-${index}`}
            icon={ScrollText}
            tone='gold'
            title={
              <span className='flex min-w-0 flex-wrap items-baseline gap-1'>
                <Text as='span' weight='semibold'>
                  {spokenKey(fact.key)}
                </Text>
                <Text as='span'>
                  <FactValueText fact={fact} />
                </Text>
              </span>
            }
            caption={
              fact.position
                ? `Item ${fact.position + 1} of its list`
                : undefined
            }
            aside={
              <div className='flex min-w-0 flex-wrap gap-2'>
                <FactEditor fact={fact} blocked={busy} />
                <StruckButton
                  act={strike}
                  label='Strike'
                  title={`Strike the fact ${spokenKey(fact.key).toLowerCase()}?`}
                  description='The fact is removed from the account of this happening.'
                  busy={busy}
                  onConfirm={() => strike.mutate(fact.id)}
                />
              </div>
            }
          />
        ))}
      </ul>
      <ShowMore state={shown} noun={['fact', 'facts']} />
    </>
  )
}

function childrenOf(
  steps: readonly EventStep[]
): Map<number | null, EventStep[]> {
  const found = new Map<number | null, EventStep[]>()
  for (const step of steps) {
    const parent = step.parent_step_id
    found.set(parent, [...(found.get(parent) ?? []), step])
  }
  return found
}

function StepLine({ step }: { step: EventStep }) {
  const action = STEP_ACTION[step.action]
  const outcome = step.outcome ? named(STEP_OUTCOME, step.outcome) : null
  return (
    <div className='flex min-w-0 flex-col gap-1'>
      <div className='flex min-w-0 flex-wrap items-baseline gap-1'>
        {step.actor_node_id !== null && (
          <NodeRef id={step.actor_node_id} name={step.actor_name} />
        )}
        <Text as='span' weight='semibold'>
          {action.label.toLowerCase()}
        </Text>
        {step.target_node_id !== null && (
          <>
            <ArrowRight
              aria-hidden='true'
              className='size-icon-xs text-muted-foreground'
            />
            <NodeRef id={step.target_node_id} name={step.target_name} />
          </>
        )}
      </div>
      <div className='flex min-w-0 flex-wrap gap-1'>
        {step.round !== null && (
          <Chip icon={Layers}>{`Round ${step.round + 1}`}</Chip>
        )}
        {step.instrument_kind !== 'none' && (
          <Chip icon={Footprints}>
            {step.instrument_name ??
              spokenKey(step.instrument_key ?? step.instrument_kind)}
          </Chip>
        )}
        {step.locus_kind !== 'none' && (
          <Chip icon={MapPin}>
            {step.locus_name ?? spokenKey(step.locus_key ?? step.locus_kind)}
          </Chip>
        )}
        {step.damage_type && (
          <Chip>{wordOf(damageTypeValues, step.damage_type)}</Chip>
        )}
        {step.amount !== null && (
          <Chip>{amountText(step.amount, step.unit)}</Chip>
        )}
        {outcome && (
          <Chip
            icon={outcome.icon}
            variant={outcome.tone === 'danger' ? 'destructive' : 'outline'}
          >
            {outcome.label}
          </Chip>
        )}
        {step.record_table !== null && (
          <Chip icon={FileText}>
            {`${spokenKey(step.record_table)} `}
            {step.record_key !== null && (
              <span className='font-mono'>{step.record_key}</span>
            )}
          </Chip>
        )}
        {(step.states ?? []).map((state) => (
          <Chip
            key={`${state.node_id}-${state.state}`}
            icon={named(STEP_STATE, state.state).icon}
            variant='warning'
          >
            {`${state.node_name ?? 'Someone'}: ${named(STEP_STATE, state.state).label.toLowerCase()}`}
          </Chip>
        ))}
      </div>
    </div>
  )
}

function StepBranch({
  steps,
  tree,
  blocked,
  depth,
}: {
  steps: readonly EventStep[]
  tree: Map<number | null, EventStep[]>
  blocked: string | null
  depth: number
}) {
  const strike = useGodAction<number>({
    writes: [{ lever: 'incident_step:delete' }],
    run: (stepId) =>
      unwrap(
        api.POST('/api/actions/incident_step:delete', {
          body: { incident_step_id: stepId },
        })
      ),
    success: 'The step is struck; what nested in it moved up',
  })
  return (
    <Timeline label={depth ? 'Steps inside the step above' : 'How it unfolded'}>
      {steps.map((step, index) => {
        const action = STEP_ACTION[step.action]
        const inner = tree.get(step.id) ?? []
        return (
          <TimelineItem
            key={step.id}
            icon={action.icon}
            tone={timelineTone(
              step.outcome ? named(STEP_OUTCOME, step.outcome).tone : undefined
            )}
            title={<StepLine step={step} />}
            timestamp={momentText(step.moment)}
            last={index === steps.length - 1}
          >
            <div className='flex min-w-0 flex-col gap-2'>
              {inner.length > 0 && (
                <StepBranch
                  steps={inner}
                  tree={tree}
                  blocked={blocked}
                  depth={depth + 1}
                />
              )}
              <StepEditor step={step} blocked={blocked} />
              <StruckButton
                act={strike}
                label='Strike the step'
                title='Strike this step?'
                description='The step is removed from how the happening unfolded; steps inside it move up a level.'
                busy={
                  blocked ??
                  (strike.isPending ? 'A step is being struck.' : null)
                }
                onConfirm={() => strike.mutate(step.id)}
              />
            </div>
          </TimelineItem>
        )
      })}
    </Timeline>
  )
}

export function Steps({
  account,
  blocked,
}: {
  account: EventAccount
  blocked: string | null
}) {
  const tree = useMemo(() => childrenOf(account.steps), [account.steps])
  const top = tree.get(null) ?? []
  const shown = useShowMore(top, SHOWN)
  const held = account.locked.includes('steps')
    ? 'The steps of this happening are held'
    : null
  if (!account.steps.length)
    return (
      <EmptyState
        icon={Footprints}
        size='inline'
        title='No steps are kept for it'
        description='How it unfolded was not recorded. Add its steps below.'
      />
    )
  return (
    <>
      <StepBranch
        steps={shown.visible}
        tree={tree}
        blocked={blocked ?? held}
        depth={0}
      />
      <ShowMore state={shown} noun={['step', 'steps']} />
    </>
  )
}

export function ChangeList({
  changes,
  blocked,
}: {
  changes: readonly EventChange[]
  blocked: string | null
}) {
  const shown = useShowMore(changes, SHOWN)
  if (!changes.length)
    return (
      <EmptyState
        icon={History}
        size='inline'
        title='It changed nothing on record'
        description='No value of any record was changed by this happening.'
      />
    )
  return (
    <>
      <ul className='flex min-w-0 flex-col gap-2'>
        {shown.visible.map((change) => (
          <RecordRow
            key={change.id}
            icon={History}
            tone={
              change.operation === 'delete'
                ? 'danger'
                : change.operation === 'insert'
                  ? 'success'
                  : 'info'
            }
            title={changeTitle(change)}
            caption={
              <span className='flex min-w-0 flex-wrap items-baseline gap-1'>
                {change.node_id !== null && (
                  <NodeRef id={change.node_id} name={change.node_name} />
                )}
                <ChangeSide change={change} side='before' />
                <ArrowRight aria-hidden='true' className='size-icon-xs' />
                <ChangeSide change={change} side='after' />
                <Muted as='span' variant='caption'>
                  {`· ${momentText(change.moment)}${change.actor_name ? ` · by ${change.actor_name}` : ''}${change.changed_at ? ` · ${formatDateTime(change.changed_at)}` : ''}`}
                </Muted>
                <AuthorMark name={change.author_name} verb='Done by' />
              </span>
            }
            aside={<ChangeControls change={change} blocked={blocked} />}
          >
            {(change.terms ?? []).length > 0 && (
              <Facts
                items={(change.terms ?? []).map((term) => [
                  spokenKey(term.term),
                  <TermAmount key={term.position} term={term} />,
                ])}
              />
            )}
          </RecordRow>
        ))}
      </ul>
      <ShowMore state={shown} noun={['change', 'changes']} />
    </>
  )
}

function LinkList({
  links,
  empty,
}: {
  links: readonly EventLink[]
  empty: string
}) {
  const shown = useShowMore(links, SHOWN)
  if (!links.length) return <Muted>{empty}</Muted>
  return (
    <>
      <ul className='flex min-w-0 flex-col gap-1'>
        {shown.visible.map((link) => (
          <li key={link.id} className='min-w-0'>
            <EntityLink kind='incident' id={String(link.id)} showIcon>
              {link.text ?? spokenKey(link.kind)}
            </EntityLink>
            <Muted
              as='span'
              variant='caption'
            >{` · epoch ${link.epoch}`}</Muted>
          </li>
        ))}
      </ul>
      <ShowMore state={shown} noun={['happening', 'happenings']} />
    </>
  )
}

function WitnessList({
  incidentId,
  witnesses,
  blocked,
}: {
  incidentId: number
  witnesses: readonly EventParticipant[]
  blocked: string | null
}) {
  const shown = useShowMore(witnesses, SHOWN)
  if (!witnesses.length)
    return (
      <EmptyState
        icon={MessageCircle}
        size='inline'
        title='No witness is named'
        description='Name who saw, heard or was told of it below.'
      />
    )
  return (
    <>
      <ul className='flex min-w-0 flex-col gap-2'>
        {shown.visible.map((witness) => {
          const mode = witness.witness_mode
            ? named(WITNESS_MODE, witness.witness_mode)
            : null
          return (
            <RecordRow
              key={`${witness.node_id}-${witness.role}`}
              icon={mode?.icon ?? MessageCircle}
              tone='info'
              title={<NodeRef id={witness.node_id} name={witness.name} />}
              caption={`${named(INCIDENT_ROLE, witness.role).label}${mode ? ` · ${mode.label.toLowerCase()}` : ''}${witness.fidelity !== null ? ` · fidelity ${witness.fidelity} of 100` : ''}`}
            >
              <WitnessEditor
                incidentId={incidentId}
                witness={witness}
                blocked={blocked}
              />
            </RecordRow>
          )
        })}
      </ul>
      <ShowMore state={shown} noun={['witness', 'witnesses']} />
    </>
  )
}

function TermAmount({ term }: { term: EventTerm }) {
  return (
    <span className='flex min-w-0 flex-wrap items-baseline gap-1'>
      {`${term.op === 'multiply' ? '×' : term.amount > 0 ? '+' : ''}${term.amount}${term.source_name ? ` from ${term.source_name}` : ''}`}
      {term.source_incident_id !== null && (
        <EntityLink
          kind='incident'
          id={String(term.source_incident_id)}
          showIcon
        >
          the happening behind it
        </EntityLink>
      )}
    </span>
  )
}

function toldValue(distortion: EventDistortion): string {
  if (distortion.told_name) return distortion.told_name
  if (distortion.told_number !== null) return String(distortion.told_number)
  if (distortion.told_enum_value) return spokenKey(distortion.told_enum_value)
  if (distortion.told_year !== null) return `the year ${distortion.told_year}`
  if (distortion.told_action)
    return STEP_ACTION[distortion.told_action].label.toLowerCase()
  if (distortion.told_outcome)
    return named(STEP_OUTCOME, distortion.told_outcome).label.toLowerCase()
  return 'something else'
}

function distortedPart(distortion: EventDistortion): string {
  if (distortion.role)
    return named(INCIDENT_ROLE, distortion.role).label.toLowerCase()
  if (distortion.fact_key) return spokenKey(distortion.fact_key)
  if (distortion.step_id !== null) return 'a step'
  return 'the account'
}

function RumourList({ rumours }: { rumours: readonly EventRumour[] }) {
  const shown = useShowMore(rumours, SHOWN)
  if (!rumours.length) return null
  return (
    <>
      <ul className='flex min-w-0 flex-col gap-2'>
        {shown.visible.map((rumour) => (
          <RecordRow
            key={rumour.id}
            icon={MessageCircle}
            tone='warning'
            title={
              <NodeRef id={rumour.carrier_id} name={rumour.carrier_name} />
            }
            caption={`Carries a rumour of it · ${rumour.hops} ${rumour.hops === 1 ? 'telling' : 'tellings'} from the source · fidelity ${rumour.fidelity} of 100 · epoch ${rumour.epoch}`}
          >
            {(rumour.distortions ?? []).length > 0 && (
              <Facts
                items={(rumour.distortions ?? []).map((distortion) => [
                  named(RUMOUR_DISTORTION, distortion.distortion).label,
                  `${distortedPart(distortion)} told as ${toldValue(distortion)}`,
                ])}
              />
            )}
          </RecordRow>
        ))}
      </ul>
      <ShowMore state={shown} noun={['rumour', 'rumours']} />
    </>
  )
}

function Account({ account }: { account: EventAccount }) {
  const items: [string, React.ReactNode][] = []
  if (account.name)
    items.push([
      'Name of the happening',
      <span key='name' className='flex min-w-0 flex-wrap items-baseline gap-1'>
        <Text as='span' weight='semibold'>
          {account.name}
        </Text>
        {account.name_language_id !== null && (
          <Muted as='span' variant='caption'>
            in{' '}
            <NodeRef
              id={account.name_language_id}
              name={account.name_language_name}
            />
          </Muted>
        )}
      </span>,
    ])
  items.push(
    ['When', momentText(account.moment)],
    [
      'Where',
      account.place_id !== null ? (
        <NodeRef id={account.place_id} name={account.place_name} />
      ) : (
        'Not known'
      ),
    ]
  )
  if (account.origin_id !== null)
    items.push([
      'Set out from',
      <NodeRef
        key='origin'
        id={account.origin_id}
        name={account.origin_name}
      />,
    ])
  if (account.destination_id !== null)
    items.push([
      'Bound for',
      <NodeRef
        key='destination'
        id={account.destination_id}
        name={account.destination_name}
      />,
    ])
  items.push(['Kind of happening', spokenKey(account.kind)])
  items.push(['Weight', `${account.magnitude} of 100`])
  if (account.note) items.push(['Your note', account.note])
  return <Facts items={items} />
}

function EventView({ incidentId }: { incidentId: number }) {
  const account = useEventAccount(incidentId)
  const blocked = useBlocked()
  const entryStack = useEntryStack()
  if (account.isPending)
    return <LoadingBlock label='Reading the account of the happening' />
  if (account.isError)
    return (
      <EmptyState
        icon={ScrollText}
        title='The happening could not be read'
        description={account.error.message}
      />
    )
  const data = account.data
  const tier = named(INCIDENT_TIER, data.tier)
  const group = data.group ? named(PROCESS_GROUP, data.group) : null
  const textHeld = data.locked.includes('text')
  return (
    <div
      data-surface='EventPage'
      className='@container/event flex min-w-0 flex-col gap-4'
    >
      <div className='flex min-w-0 items-start gap-3'>
        <Medallion icon={group?.icon ?? ScrollText} tone='gold' />
        <div className='flex min-w-0 flex-col gap-1'>
          <Text weight='semibold'>
            {data.line ?? data.retold ?? spokenKey(data.kind)}
          </Text>
          {data.retold && data.retold !== data.line && (
            <Muted variant='caption'>{`Told again from its fields: ${data.retold}`}</Muted>
          )}
          <div className='flex min-w-0 flex-wrap gap-1'>
            <Chip icon={tier.icon}>{tier.label}</Chip>
            {group && <Chip icon={group.icon}>{group.label}</Chip>}
            {!data.known && <Chip variant='warning'>A kind of its own</Chip>}
            {textHeld && <Chip variant='info'>Its telling is held</Chip>}
          </div>
        </div>
      </div>
      <IncidentEditor
        account={data}
        blocked={blocked}
        onStruck={() => entryStack.back()}
      />
      <IncidentNameForge incidentId={data.id} name={data.name} />
      <PanelGrid columns={3}>
        <KpiTile label='Facts' value={data.facts.length} icon={ScrollText} />
        <KpiTile
          label='Steps'
          value={data.steps.length}
          icon={Footprints}
          tone='verdigris'
        />
        <KpiTile
          label='Changes it made'
          value={data.changes.length}
          icon={History}
          tone='info'
        />
      </PanelGrid>
      <Section
        id='event-account'
        title='The account'
        icon={Calendar}
        tone='gold'
        level={3}
      >
        <Account account={data} />
        <Participants people={data.participants} />
      </Section>
      <Section
        id='event-facts'
        title='Its facts'
        icon={ScrollText}
        tone='gold'
        level={3}
      >
        <FactRows facts={data.facts} account={data} blocked={blocked} />
        <FactForge
          account={data}
          blocked={
            blocked ??
            (data.locked.includes('facts')
              ? 'The facts of this happening are held'
              : null)
          }
        />
      </Section>
      <Section
        id='event-steps'
        title='How it unfolded'
        icon={Footprints}
        tone='verdigris'
        level={3}
      >
        <Steps account={data} blocked={blocked} />
        <StepForge
          account={data}
          blocked={
            blocked ??
            (data.locked.includes('steps')
              ? 'The steps of this happening are held'
              : null)
          }
        />
      </Section>
      <Section
        id='event-changes'
        title='What it changed'
        description='Every value it changed, with what it was before, what it became and why.'
        icon={History}
        tone='info'
        level={3}
      >
        <ChangeList changes={data.changes} blocked={blocked} />
      </Section>
      <Section
        id='event-knowers'
        title='Who knows of it'
        icon={MessageCircle}
        tone='info'
        level={3}
      >
        <WitnessList
          incidentId={data.id}
          witnesses={data.witnesses}
          blocked={
            blocked ??
            (data.locked.includes('witnesses')
              ? 'The witnesses of this happening are held'
              : null)
          }
        />
        <RumourList rumours={data.rumours} />
        <WitnessForge
          account={data}
          blocked={
            blocked ??
            (data.locked.includes('witnesses')
              ? 'The witnesses of this happening are held'
              : null)
          }
        />
      </Section>
      <Section
        id='event-causes'
        title='Causes and effects'
        icon={GitBranch}
        tone='muted'
        level={3}
      >
        <PanelGrid>
          <div className='flex min-w-0 flex-col gap-1'>
            <Muted variant='caption'>What led to it, oldest first</Muted>
            <LinkList
              links={data.causes}
              empty='Nothing on record led to it.'
            />
          </div>
          <div className='flex min-w-0 flex-col gap-1'>
            <Muted variant='caption'>What it led to</Muted>
            <LinkList
              links={data.effects}
              empty='Nothing on record followed from it yet.'
            />
          </div>
        </PanelGrid>
      </Section>
      <Section
        id='event-hold'
        title='Hold it as it is'
        description='A held part is never told again or changed by the world; you may still change it yourself.'
        icon={Clock}
        tone='gold'
        level={3}
      >
        <HoldBar account={data} blocked={blocked} />
      </Section>
    </div>
  )
}

export function EventPage({ id }: EntryPageProps) {
  const incidentId = Number(id)
  if (!Number.isInteger(incidentId) || incidentId <= 0)
    return (
      <EmptyState
        icon={ScrollText}
        title='No such happening'
        description='This link does not point to a happening on record.'
      />
    )
  return <EventView incidentId={incidentId} />
}
