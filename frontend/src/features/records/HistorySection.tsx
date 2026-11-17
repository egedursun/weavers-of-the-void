import { useState } from 'react'
import { Footprints, History, ScrollText } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  EmptyState,
  EntityLink,
  LoadingBlock,
  Section,
  ShowMore,
  Timeline,
  TimelineItem,
  useShowMore,
} from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { Chip, RecordRow } from '@/features/cosmography/parts'
import { type Named, named } from '@/features/entity/environment/labels'
import { ChoiceField } from '@/features/wars/military/parts'
import { ChangeList } from './EventPage'
import { TimelineScrubber } from './TimelineScrubber'
import {
  type EventStep,
  type IncidentRole,
  type NodeHistoryEntry,
  useNodeHistory,
} from './api'
import { momentText, spokenKey } from './format'
import {
  INCIDENT_ROLE,
  INCIDENT_TIER,
  PROCESS_GROUP,
  STEP_ACTION,
} from './labels'
import { NodeRef } from './parts'
import { roleTimelineTone } from './tones'

const PAGE = 12
const ROLES_SHOWN = 6
const EVERY = 'every'

function Entry({ entry }: { entry: NodeHistoryEntry }) {
  const group = entry.group ? named(PROCESS_GROUP, entry.group) : null
  const tier = named(INCIDENT_TIER, entry.tier)
  const roles = useShowMore(entry.roles, ROLES_SHOWN)
  return (
    <div className='flex min-w-0 flex-col gap-1'>
      <EntityLink kind='incident' id={String(entry.incident_id)} showIcon>
        {entry.line ?? spokenKey(entry.kind)}
      </EntityLink>
      <div className='flex min-w-0 flex-wrap gap-1'>
        {roles.visible.map((role) => {
          const spec = named(INCIDENT_ROLE, role)
          return (
            <Chip key={role} icon={spec.icon}>
              {spec.label}
            </Chip>
          )
        })}
        <ShowMore state={roles} noun={['role', 'roles']} />
        {group && <Chip icon={group.icon}>{group.label}</Chip>}
        <Chip icon={tier.icon}>{tier.label}</Chip>
        {entry.place_id !== null && (
          <Text as='span' variant='caption'>
            <NodeRef id={entry.place_id} name={entry.place_name} />
          </Text>
        )}
      </div>
      <Muted variant='caption'>
        {`${entry.facts} ${entry.facts === 1 ? 'fact' : 'facts'} · ${entry.steps} ${entry.steps === 1 ? 'step' : 'steps'} · ${entry.changes} ${entry.changes === 1 ? 'change' : 'changes'}`}
      </Muted>
    </div>
  )
}

function StepRows({ steps }: { steps: readonly EventStep[] }) {
  const shown = useShowMore(steps, PAGE)
  if (!steps.length) return null
  return (
    <>
      <Muted variant='caption'>Steps it took or suffered</Muted>
      <ul className='flex min-w-0 flex-col gap-2'>
        {shown.visible.map((step) => (
          <RecordRow
            key={step.id}
            icon={STEP_ACTION[step.action].icon}
            tone='verdigris'
            title={
              <EntityLink
                kind='incident'
                id={String(step.incident_id)}
                showIcon
              >
                {`${step.actor_name ?? 'Someone'} · ${STEP_ACTION[step.action].label.toLowerCase()}${step.target_name ? ` · ${step.target_name}` : ''}`}
              </EntityLink>
            }
            caption={momentText(step.moment)}
          />
        ))}
      </ul>
      <ShowMore state={shown} noun={['step', 'steps']} />
    </>
  )
}

function filterTable(
  values: readonly string[],
  table: Record<string, Named>,
  every: string
): Record<string, Named> {
  return {
    [EVERY]: { label: every, icon: History },
    ...Object.fromEntries(values.map((value) => [value, named(table, value)])),
  }
}

function kindTable(kinds: readonly string[]): Record<string, Named> {
  return {
    [EVERY]: { label: 'Every kind', icon: History },
    ...Object.fromEntries(
      kinds.map((kind) => [kind, { label: spokenKey(kind), icon: ScrollText }])
    ),
  }
}

export function HistorySection({
  nodeId,
  readOnlyReason = null,
}: {
  nodeId: number
  readOnlyReason?: string | null
}) {
  const [role, setRole] = useState<string>(EVERY)
  const [kind, setKind] = useState<string>(EVERY)
  const [limit, setLimit] = useState(PAGE)
  const query = useNodeHistory(nodeId, {
    role: role === EVERY ? null : (role as IncidentRole),
    kind: kind === EVERY ? null : kind,
    limit,
  })
  const data = query.data
  const more = data
    ? Math.max(data.total_incidents, data.total_steps, data.total_changes) >
      limit
    : false
  return (
    <Section
      id='section-history'
      title='History'
      description='Every happening it took part in with the role it held, every step it took or suffered, and every change to its records, kept for ever.'
      icon={History}
      tone='gold'
    >
      <div
        data-surface='HistorySection'
        className='flex min-w-0 flex-col gap-4'
      >
        <TimelineScrubber nodeId={nodeId} />
        {query.isPending ? (
          <LoadingBlock label='Reading its history' />
        ) : query.isError ? (
          <EmptyState
            icon={History}
            size='inline'
            title='Its history could not be read'
            description={query.error.message}
          />
        ) : data === undefined ? null : (
          <>
            <div className='grid min-w-0 grid-cols-1 gap-3 @lg/section:grid-cols-2'>
              <ChoiceField
                label='Its role'
                value={role}
                table={filterTable(data.roles, INCIDENT_ROLE, 'Every role')}
                blocked={data.roles.length ? null : 'It held no role yet'}
                onPick={(value) => {
                  setRole(value)
                  setLimit(PAGE)
                }}
              />
              <ChoiceField
                label='Kind of happening'
                value={kind}
                table={kindTable(data.kinds)}
                blocked={
                  data.kinds.length ? null : 'It took part in nothing yet'
                }
                onPick={(value) => {
                  setKind(value)
                  setLimit(PAGE)
                }}
              />
            </div>
            <Muted variant='caption'>
              {`${data.total_incidents} ${data.total_incidents === 1 ? 'happening' : 'happenings'} · ${data.total_steps} ${data.total_steps === 1 ? 'step' : 'steps'} · ${data.total_changes} ${data.total_changes === 1 ? 'change' : 'changes'} on record`}
            </Muted>
            {data.incidents.length ? (
              <Timeline label='Happenings it took part in'>
                {data.incidents.map((entry, index) => (
                  <TimelineItem
                    key={entry.incident_id}
                    icon={
                      entry.group
                        ? named(PROCESS_GROUP, entry.group).icon
                        : ScrollText
                    }
                    tone={roleTimelineTone(entry.roles[0] ?? 'subject')}
                    title={<Entry entry={entry} />}
                    timestamp={momentText(entry.moment)}
                    last={index === data.incidents.length - 1}
                  />
                ))}
              </Timeline>
            ) : (
              <EmptyState
                icon={ScrollText}
                size='inline'
                title='No happening is on record for it'
                description='Nothing it took part in has been set down yet; write one into history from the incident forge.'
              />
            )}
            <StepRows steps={data.steps} />
            {data.changes.length > 0 && (
              <>
                <Muted variant='caption'>Changes to its records</Muted>
                <ChangeList changes={data.changes} blocked={readOnlyReason} />
              </>
            )}
            {more ? (
              <Button
                variant='outline'
                size='sm'
                onClick={() => setLimit((current) => current + PAGE)}
              >
                <Footprints aria-hidden='true' />
                Show more of its history
              </Button>
            ) : null}
          </>
        )}
      </div>
    </Section>
  )
}
