import { useState } from 'react'
import { Check, Flame, Lock, Plus, Unlock, X } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import {
  EmptyState,
  EntityLink,
  KpiTile,
  Medallion,
  Paged,
  Section,
} from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { type AdjustGroup, AdjustStats } from '@/features/pantheon/AdjustStats'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import {
  type Aspirations,
  type FearKind,
  type FocusKind,
  type InspirationKind,
  type LifeGoal,
  type PerkKind,
  type WantKind,
  useAspirations,
} from '../mind/api'
import {
  ASPIRATION_ICON,
  FEAR_ICON,
  FOCUS_ICON,
  FOCUS_ICONS,
  GOAL_ICONS,
  INSPIRATION_ICON,
  WANT_ICON,
} from '../mind/aspirationLabels'
import { named } from '../mind/labels'
import { AddBar, ControlPanel, MindCard, MindPicker } from '../mind/parts'

const PERCENT = 100
const WORKING = 'Working on it.'

function table(
  items: { key: string; label: string }[]
): Record<string, string> {
  return Object.fromEntries(items.map((item) => [item.key, item.label]))
}

function DreamCard({
  view,
  blocked,
}: {
  view: Aspirations
  blocked: string | null
}) {
  const [goal, setGoal] = useState<string>(view.dream?.goal ?? 'find_love')
  const set = useGodAction({
    run: (picked: LifeGoal) =>
      unwrap(
        api.POST('/api/actions/aspiration:dream', {
          body: {
            holder_id: view.node_id,
            goal: picked,
            progress: 0,
            state: 'pursuing',
            hold: false,
          },
        })
      ),
  })
  const remove = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/aspiration:dream_remove', {
          body: { holder_id: view.node_id },
        })
      ),
  })
  const busy = blocked ?? (set.isPending || remove.isPending ? WORKING : null)
  const dream = view.dream
  const spec = named(GOAL_ICONS, dream?.goal ?? goal)
  return (
    <MindCard
      title="Life's dream"
      icon={ASPIRATION_ICON}
      hint='One great aim, chosen from beliefs and temperament. Each milestone brings hope; fulfilment is never forgotten.'
      wide
    >
      {dream ? (
        <div className='flex min-w-0 flex-col gap-3'>
          <div className='flex min-w-0 items-center gap-3'>
            <Medallion icon={spec.icon} tone={spec.tone} />
            <div className='flex min-w-0 flex-1 flex-col'>
              <Text weight='semibold'>{dream.label}</Text>
              <Muted variant='caption'>{`Since epoch ${dream.started_epoch}${dream.held ? ' · held' : ''}`}</Muted>
            </div>
            <Badge
              variant={dream.state === 'fulfilled' ? 'default' : 'outline'}
            >
              {dream.state}
            </Badge>
          </div>
          {dream.target && (
            <EntityLink kind='entity' id={String(dream.target.id)} showIcon>
              {dream.target.name}
            </EntityLink>
          )}
          <Progress
            value={dream.progress}
            tone={dream.state === 'failed' ? 'destructive' : 'success'}
            aria-label='Progress toward the dream'
          />
          <div className='grid min-w-0 grid-cols-1 gap-2 @md/mind:grid-cols-3'>
            {dream.milestones.map((item) => (
              <div
                key={item.at}
                className='flex min-w-0 items-center gap-2 rounded-md border p-2'
              >
                {item.reached ? (
                  <Check
                    aria-hidden='true'
                    className='size-icon-sm text-success'
                  />
                ) : (
                  <Lock
                    aria-hidden='true'
                    className='size-icon-sm text-muted-foreground'
                  />
                )}
                <Text variant='caption' truncate>
                  {item.label}
                </Text>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <EmptyState
          icon={ASPIRATION_ICON}
          size='compact'
          title='No dream yet'
          description='Adults take up a dream as the epochs pass; you can give one now.'
        />
      )}
      <AddBar
        title='Give a dream'
        action={
          <div className='flex items-center gap-2'>
            <Button
              size='sm'
              disabled={busy !== null}
              disabledReason={busy ?? undefined}
              onClick={() => set.mutate(goal as LifeGoal)}
            >
              <Plus />
              Set
            </Button>
            {dream && (
              <Button
                size='icon-sm'
                variant='ghost'
                aria-label='Take the dream away'
                disabled={busy !== null}
                disabledReason={busy ?? undefined}
                onClick={() => remove.mutate()}
              >
                <X />
              </Button>
            )}
          </div>
        }
      >
        <MindPicker
          label='Kind'
          value={goal}
          table={table(view.goals)}
          blocked={busy}
          onPick={setGoal}
        />
      </AddBar>
    </MindCard>
  )
}

function WantsAndFears({
  view,
  blocked,
}: {
  view: Aspirations
  blocked: string | null
}) {
  const [want, setWant] = useState<string>('travel')
  const [fear, setFear] = useState<string>('war')
  const addWant = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/aspiration:want', {
          body: { holder_id: view.node_id, kind: want as WantKind },
        })
      ),
  })
  const meet = useGodAction({
    run: (id: number) =>
      unwrap(
        api.POST('/api/actions/aspiration:want_edit', {
          body: { want_id: id, fulfilled: true },
        })
      ),
  })
  const dropWant = useGodAction({
    run: (id: number) =>
      unwrap(
        api.POST('/api/actions/aspiration:want_remove', {
          body: { want_id: id },
        })
      ),
  })
  const addFear = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/aspiration:fear', {
          body: {
            holder_id: view.node_id,
            kind: fear as FearKind,
            strength: 60,
          },
        })
      ),
  })
  const dropFear = useGodAction({
    run: (id: number) =>
      unwrap(
        api.POST('/api/actions/aspiration:fear_remove', {
          body: { fear_id: id },
        })
      ),
  })
  const busy =
    blocked ??
    ([addWant, meet, dropWant, addFear, dropFear].some((item) => item.isPending)
      ? WORKING
      : null)
  return (
    <>
      <MindCard
        title='Wants'
        icon={WANT_ICON}
        hint='Short aims from pressing needs and the dream. They steer callings and matches, and an agent pursues them.'
      >
        {view.wants.length === 0 ? (
          <Muted variant='caption'>Nothing wanted right now.</Muted>
        ) : (
          <Paged items={view.wants} initial={4} noun={['want', 'wants']}>
            {(item) => (
              <div
                key={item.id}
                className='flex min-w-0 items-center gap-2 rounded-md border p-2'
              >
                <Text weight='semibold' truncate className='flex-1'>
                  {item.label}
                </Text>
                {item.fulfilled_epoch !== null ? (
                  <Badge>{`Met in epoch ${item.fulfilled_epoch}`}</Badge>
                ) : (
                  <Button
                    size='icon-sm'
                    variant='ghost'
                    aria-label={`Fulfil ${item.label}`}
                    disabled={busy !== null}
                    disabledReason={busy ?? undefined}
                    onClick={() => meet.mutate(item.id)}
                  >
                    <Check />
                  </Button>
                )}
                <Button
                  size='icon-sm'
                  variant='ghost'
                  aria-label={`Take away ${item.label}`}
                  disabled={busy !== null}
                  disabledReason={busy ?? undefined}
                  onClick={() => dropWant.mutate(item.id)}
                >
                  <X />
                </Button>
              </div>
            )}
          </Paged>
        )}
        <AddBar
          title='Give a want'
          action={
            <div className='flex items-center gap-2'>
              <Button
                size='sm'
                disabled={busy !== null}
                disabledReason={busy ?? undefined}
                onClick={() => addWant.mutate()}
              >
                <Plus />
                Give
              </Button>
            </div>
          }
        >
          <MindPicker
            label='Kind'
            value={want}
            table={table(view.want_kinds)}
            blocked={busy}
            onPick={setWant}
          />
        </AddBar>
      </MindCard>
      <MindCard
        title='Fears'
        icon={FEAR_ICON}
        hint='When the feared thing comes near, fear darkens the mood. A heroic resolve holds fear back.'
      >
        {view.fears.length === 0 ? (
          <Muted variant='caption'>No fears.</Muted>
        ) : (
          view.fears.map((item) => (
            <div key={item.id} className='flex min-w-0 items-center gap-2'>
              <Text truncate className='flex-1'>
                {item.label}
              </Text>
              <div className='w-24 min-w-0'>
                <Progress
                  value={item.strength}
                  size='sm'
                  tone='warning'
                  aria-label={`${item.label} strength`}
                />
              </div>
              <Button
                size='icon-sm'
                variant='ghost'
                aria-label={`Lift the fear of ${item.label}`}
                disabled={busy !== null}
                disabledReason={busy ?? undefined}
                onClick={() => dropFear.mutate(item.id)}
              >
                <X />
              </Button>
            </div>
          ))
        )}
        <AddBar
          title='Give a fear'
          action={
            <div className='flex items-center gap-2'>
              <Button
                size='sm'
                disabled={busy !== null}
                disabledReason={busy ?? undefined}
                onClick={() => addFear.mutate()}
              >
                <Plus />
                Give
              </Button>
            </div>
          }
        >
          <MindPicker
            label='Kind'
            value={fear}
            table={table(view.fear_kinds)}
            blocked={busy}
            onPick={setFear}
          />
        </AddBar>
      </MindCard>
    </>
  )
}

function FocusCard({
  view,
  blocked,
}: {
  view: Aspirations
  blocked: string | null
}) {
  const focus = useGodAction({
    run: (picked: FocusKind) =>
      unwrap(
        api.POST('/api/actions/aspiration:focus', {
          body: { holder_id: view.node_id, focus: picked, hold: true },
        })
      ),
  })
  const grant = useGodAction({
    run: (perk: PerkKind) =>
      unwrap(
        api.POST('/api/actions/aspiration:perk', {
          body: { holder_id: view.node_id, perk },
        })
      ),
  })
  const drop = useGodAction({
    run: (perk: PerkKind) =>
      unwrap(
        api.POST('/api/actions/aspiration:perk_remove', {
          body: { holder_id: view.node_id, perk },
        })
      ),
  })
  const busy =
    blocked ??
    (focus.isPending || grant.isPending || drop.isPending ? WORKING : null)
  const spec = view.focus ? named(FOCUS_ICONS, view.focus) : null
  return (
    <MindCard
      title='Focus and perks'
      icon={FOCUS_ICON}
      hint='Office holders and the highly skilled take a focus: its skills come faster and perks unlock at skill milestones.'
      wide
    >
      <div className='flex min-w-0 flex-wrap items-end gap-3'>
        {spec && <Medallion icon={spec.icon} tone={spec.tone} />}
        <div className='min-w-0 flex-1'>
          <MindPicker
            label='Focus'
            value={view.focus ?? ''}
            table={table(view.focuses)}
            blocked={busy}
            placeholder='No focus yet'
            onPick={(value) => focus.mutate(value as FocusKind)}
          />
        </div>
        <Muted variant='caption'>{`Skill toward perks: ${view.focus_level}${view.focus_held ? ' · held' : ''}`}</Muted>
      </div>
      {view.perks.length > 0 && (
        <div className='grid min-w-0 grid-cols-1 gap-2 @md/mind:grid-cols-2 @3xl/mind:grid-cols-3'>
          {view.perks.map((perk) => (
            <div
              key={perk.perk}
              className='flex min-w-0 items-center gap-2 rounded-md border p-2'
            >
              <div className='flex min-w-0 flex-1 flex-col'>
                <Text weight='semibold' truncate>
                  {perk.label}
                </Text>
                <Muted variant='caption'>{`+${perk.amount} ${perk.stat} · at skill ${perk.level}`}</Muted>
              </div>
              {perk.owned ? (
                <Button
                  size='icon-sm'
                  variant='ghost'
                  aria-label={`Take away ${perk.label}`}
                  disabled={busy !== null}
                  disabledReason={busy ?? undefined}
                  onClick={() => drop.mutate(perk.perk)}
                >
                  <X />
                </Button>
              ) : (
                <Button
                  size='icon-sm'
                  variant='ghost'
                  aria-label={`Grant ${perk.label}`}
                  disabled={busy !== null}
                  disabledReason={busy ?? undefined}
                  onClick={() => grant.mutate(perk.perk)}
                >
                  <Plus />
                </Button>
              )}
            </div>
          ))}
        </div>
      )}
    </MindCard>
  )
}

function InspirationCard({
  view,
  blocked,
}: {
  view: Aspirations
  blocked: string | null
}) {
  const [kind, setKind] = useState<string>('masterwork_fever')
  const inspire = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/aspiration:inspire', {
          body: {
            holder_id: view.node_id,
            kind: kind as InspirationKind,
            epochs: 2,
          },
        })
      ),
  })
  const quench = useGodAction({
    run: (id: number) =>
      unwrap(
        api.POST('/api/actions/aspiration:inspiration_remove', {
          body: { inspiration_id: id },
        })
      ),
  })
  const busy =
    blocked ?? (inspire.isPending || quench.isPending ? WORKING : null)
  return (
    <MindCard
      title='Inspiration'
      icon={INSPIRATION_ICON}
      hint='An elated mortal may be seized: a fever to make a masterwork, a flash of insight, or a heroic resolve.'
    >
      {view.inspirations.length === 0 ? (
        <Muted variant='caption'>Never seized yet.</Muted>
      ) : (
        <Paged
          items={view.inspirations}
          initial={3}
          noun={['inspiration', 'inspirations']}
        >
          {(item) => (
            <div
              key={item.id}
              className='flex min-w-0 items-center gap-2 rounded-md border p-2'
            >
              <Flame aria-hidden='true' className='size-icon-sm text-warning' />
              <div className='flex min-w-0 flex-1 flex-col'>
                <Text weight='semibold' truncate>
                  {item.label}
                </Text>
                <Muted variant='caption'>{`${item.state}${item.material ? ` · ${item.material}` : ''} · until epoch ${item.deadline_epoch}`}</Muted>
              </div>
              {item.result && (
                <EntityLink kind='entity' id={String(item.result.id)}>
                  {item.result.name}
                </EntityLink>
              )}
              <Button
                size='icon-sm'
                variant='ghost'
                aria-label={`Quench ${item.label}`}
                disabled={busy !== null}
                disabledReason={busy ?? undefined}
                onClick={() => quench.mutate(item.id)}
              >
                <X />
              </Button>
            </div>
          )}
        </Paged>
      )}
      <AddBar
        title='Seize them with inspiration'
        action={
          <div className='flex items-center gap-2'>
            <Button
              size='sm'
              disabled={busy !== null}
              disabledReason={busy ?? undefined}
              onClick={() => inspire.mutate()}
            >
              <Flame />
              Inspire
            </Button>
          </div>
        }
      >
        <MindPicker
          label='Inspiration'
          value={kind}
          table={table(view.inspiration_kinds)}
          blocked={busy}
          onPick={setKind}
        />
      </AddBar>
    </MindCard>
  )
}

function adjustGroups(view: Aspirations): AdjustGroup[] {
  const groups: AdjustGroup[] = [
    {
      title: 'Conviction (0 to 100)',
      fields: [
        {
          key: 'conviction',
          label: 'Conviction',
          value: view.conviction,
          min: 0,
          max: PERCENT,
        },
      ],
    },
  ]
  if (view.dream)
    groups.push({
      title: "Life's dream",
      fields: [
        {
          key: 'dream',
          label: 'Progress',
          value: view.dream.progress,
          min: 0,
          max: PERCENT,
        },
      ],
    })
  if (view.fears.length > 0)
    groups.push({
      title: 'Fear strength',
      fields: view.fears.map((item) => ({
        key: `fear:${item.kind}`,
        label: item.label,
        value: item.strength,
        min: 0,
        max: PERCENT,
      })),
    })
  const burning = view.inspirations.filter((item) => item.state === 'burning')
  if (burning.length > 0)
    groups.push({
      title: 'Inspiration lasts until epoch',
      fields: burning.map((item) => ({
        key: `inspiration:${item.id}`,
        label: item.label,
        value: item.deadline_epoch,
        min: 0,
      })),
    })
  return groups
}

function adjust(view: Aspirations, hold: boolean, key: string, value: number) {
  const [kind, ref] = key.split(':')
  if (kind === 'dream' && view.dream)
    return unwrap(
      api.POST('/api/actions/aspiration:dream', {
        body: {
          holder_id: view.node_id,
          goal: view.dream.goal,
          target_id: view.dream.target?.id ?? null,
          progress: value,
          state: value >= PERCENT ? 'fulfilled' : 'pursuing',
          hold,
        },
      })
    )
  if (kind === 'fear') {
    const fear = view.fears.find((item) => item.kind === ref)
    return unwrap(
      api.POST('/api/actions/aspiration:fear', {
        body: {
          holder_id: view.node_id,
          kind: ref as FearKind,
          strength: value,
          target_id: fear?.target?.id ?? null,
        },
      })
    )
  }
  if (kind === 'inspiration')
    return unwrap(
      api.POST('/api/actions/aspiration:inspiration_edit', {
        body: { inspiration_id: Number(ref), deadline_epoch: value },
      })
    )
  return unwrap(
    api.POST('/api/actions/aspiration:conviction', {
      body: { holder_id: view.node_id, value, hold },
    })
  )
}

function AspirationControls({ view }: { view: Aspirations }) {
  const { reason } = useGodGate()
  const [hold, setHold] = useState(true)
  const lock = useGodAction({
    run: (field: string) =>
      unwrap(
        api.POST(
          view.locked ? '/api/actions/mind:unlock' : '/api/actions/mind:lock',
          { body: { node_id: view.node_id, field } }
        )
      ),
  })
  const busy = reason() ?? (lock.isPending ? WORKING : null)
  return (
    <ControlPanel
      title='Shape aims and resolve'
      note='Set conviction, dream progress, fear strength and how long an inspiration lasts, or hold the dream, wants and fears so the world stops changing them. Every change goes into the ledger and can be undone.'
      hold={hold}
      onHold={setHold}
    >
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Button
          size='sm'
          variant={view.locked ? 'outline' : 'ghost'}
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => lock.mutate('aspirations')}
        >
          {view.locked ? <Unlock /> : <Lock />}
          {view.locked
            ? 'Release dreams, wants and fears'
            : 'Hold dreams, wants and fears'}
        </Button>
        <Label>{`Conviction ${view.conviction}${view.conviction_held ? ' · held' : ''}`}</Label>
      </div>
      <AdjustStats
        id={`aspirations-${view.node_id}`}
        groups={adjustGroups(view)}
        note='Conviction steadies a mind under stress, slows changes of belief and is spent for heroic efforts in duels. Dream progress, fear strength and inspiration deadlines can be set too.'
        run={({ key, value }) => adjust(view, hold, key, value)}
      />
    </ControlPanel>
  )
}

export function AspirationsSection({ nodeId }: { nodeId: number }) {
  const { reason } = useGodGate()
  const query = useAspirations(nodeId)
  const view = query.data
  if (query.isError)
    return (
      <Section
        id='section-aspirations'
        title='Dreams, wants and fears'
        icon={ASPIRATION_ICON}
      >
        <EmptyState
          icon={ASPIRATION_ICON}
          title='This could not be read'
          description={query.error.message}
        />
      </Section>
    )
  if (!view || !view.applies) return null
  const blocked = reason()
  const met = view.wants.filter((item) => item.fulfilled_epoch !== null).length
  return (
    <Section
      id='section-aspirations'
      title='Dreams, wants and fears'
      description="Only living mortals aim at a life's dream, want, fear and take up a focus. Acting in character builds the conviction to see it through."
      icon={ASPIRATION_ICON}
    >
      <div className='@container/mind flex min-w-0 flex-col gap-4'>
        <div className='grid min-w-0 grid-cols-1 gap-3 @md/mind:grid-cols-2 @3xl/mind:grid-cols-4'>
          <KpiTile
            label="Dream's progress"
            value={view.dream ? `${view.dream.progress}%` : 'None'}
            icon={ASPIRATION_ICON}
            tone='gold'
            meter={
              view.dream
                ? { value: view.dream.progress, max: PERCENT, label: 'Dream' }
                : undefined
            }
          />
          <KpiTile
            label='Wants met'
            value={`${met} / ${view.wants.length}`}
            icon={WANT_ICON}
            tone='success'
          />
          <KpiTile
            label='Perks'
            value={view.perks.filter((item) => item.owned).length}
            icon={FOCUS_ICON}
            tone='verdigris'
          />
          <KpiTile
            label='Conviction'
            value={view.conviction}
            icon={INSPIRATION_ICON}
            tone='warning'
            meter={{
              value: view.conviction,
              max: PERCENT,
              label: 'Conviction',
            }}
          />
        </div>
        <div className='grid min-w-0 grid-cols-1 gap-3 @xl/mind:grid-cols-2'>
          <DreamCard view={view} blocked={blocked} />
          <WantsAndFears view={view} blocked={blocked} />
          <FocusCard view={view} blocked={blocked} />
          <InspirationCard view={view} blocked={blocked} />
        </div>
        <AspirationControls view={view} />
      </div>
    </Section>
  )
}
