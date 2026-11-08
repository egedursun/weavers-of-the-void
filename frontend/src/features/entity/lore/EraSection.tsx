import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  Ban,
  BookX,
  Hourglass,
  Lock,
  Scale,
  Telescope,
  TriangleAlert,
  Unlock,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Switch } from '@/components/ui/switch'
import {
  EmptyState,
  KpiTile,
  LoadingBlock,
  Medallion,
  Paged,
  Section,
} from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { EntityPicker } from '@/features/cosmos/EntityPicker'
import { useGodGate } from '@/features/pantheon/gate'
import { loreKeys } from '../api/keys'
import {
  AdjustBlock,
  AdjustPanel,
  ChoicePicker,
  RowEditor,
  RowEditors,
  Who,
} from './LoreFields'
import { AGE_LOOK } from './discoveryLabels'
import { KPI_GRID, PERCENT, busyOf } from './model'
import { useLoreAction } from './panels/controlParts'

const WORK_TYPES = ['item', 'knowledge', 'ideology', 'artwork']

function useRealmEra(polityId: number) {
  return useQuery({
    queryKey: [...loreKeys.entity(polityId), 'era'],
    queryFn: () =>
      unwrap(
        api.GET('/api/polities/{polity_id}/era', {
          params: { path: { polity_id: polityId } },
        })
      ),
  })
}

function useWorldEra(worldId: number) {
  return useQuery({
    queryKey: [...loreKeys.state, 'world-era', worldId],
    queryFn: () =>
      unwrap(
        api.GET('/api/worlds/{world_id}/era', {
          params: { path: { world_id: worldId } },
        })
      ),
  })
}

export function EraSection({
  polityId,
  readOnlyReason,
}: {
  polityId: number
  readOnlyReason?: string | null
}) {
  const view = useRealmEra(polityId)
  const { reason } = useGodGate()
  const blocked = readOnlyReason ?? reason()
  const set = useLoreAction<{
    score?: number
    age?: string
    hold: boolean
  }>('/api/actions/discovery:era', (value) => ({
    polity_id: polityId,
    ...value,
  }))
  const ban = useLoreAction<{ work: number; banned: boolean }>(
    '/api/actions/discovery:ban',
    (value) => ({
      polity_id: polityId,
      work_id: value.work,
      banned: value.banned,
    })
  )
  const [hold, setHold] = useState(true)
  const [work, setWork] = useState<number | null>(null)
  const busy = busyOf(blocked, set.isPending, ban.isPending)
  return (
    <Section
      id='section-era'
      title='Era and age'
      description='The deeds that raise or sink the realm, the age they bring and the works it bans. Only realms keep an era score; a world shows its era on its own page.'
      icon={Hourglass}
    >
      {view.isPending && <LoadingBlock label='Weighing its deeds' />}
      {view.isError && (
        <EmptyState
          icon={TriangleAlert}
          title='Its era could not be read'
          description={view.error.message}
        />
      )}
      {view.data && (
        <div
          data-surface='EraPanel'
          className='@container/lore flex min-w-0 flex-col gap-4'
        >
          <div className={KPI_GRID}>
            <KpiTile
              label='Age'
              value={AGE_LOOK[view.data.age].label}
              icon={AGE_LOOK[view.data.age].icon}
              tone={AGE_LOOK[view.data.age].tone}
              hint={`Since epoch ${view.data.since_epoch}`}
            />
            <KpiTile
              label='Era score'
              value={view.data.score}
              icon={Scale}
              tone={
                view.data.score >= view.data.golden_at
                  ? 'gold'
                  : view.data.score <= view.data.dark_at
                    ? 'danger'
                    : 'info'
              }
              hint={`A golden age at ${view.data.golden_at}, a dark age at ${view.data.dark_at}`}
              meter={{
                value: Math.max(0, view.data.score - view.data.dark_at),
                max: Math.max(1, view.data.golden_at - view.data.dark_at),
                label: 'From dark to golden',
              }}
            />
            <KpiTile
              label='Deeds'
              value={view.data.deeds.length}
              icon={Hourglass}
              tone='verdigris'
              hint='Firsts, institutions, victories, wonders and great people raise it; defeats and famine sink it'
            />
            <KpiTile
              label='Banned works'
              value={view.data.banned.length}
              icon={BookX}
              tone={view.data.banned.length > 0 ? 'warning' : 'muted'}
              hint='Banned works are read and taught only in secret'
            />
          </div>
          {view.data.deeds.length === 0 ? (
            <Muted>No deed has been weighed yet.</Muted>
          ) : (
            <ul className='flex min-w-0 flex-col gap-1.5'>
              <Paged items={view.data.deeds} as='li'>
                {(deed) => (
                  <li
                    key={deed.id}
                    className='flex min-w-0 items-center gap-2 rounded-md border bg-muted/20 px-2.5 py-1.5'
                  >
                    <Badge
                      size='sm'
                      variant={deed.points >= 0 ? 'default' : 'destructive'}
                    >
                      {deed.points >= 0 ? `+${deed.points}` : deed.points}
                    </Badge>
                    <Text as='span' className='min-w-0 flex-1' truncate>
                      {deed.label}
                    </Text>
                    {deed.subject && <Who item={deed.subject} />}
                    <Muted
                      as='span'
                      variant='caption'
                    >{`Epoch ${deed.epoch}`}</Muted>
                  </li>
                )}
              </Paged>
            </ul>
          )}
          <div
            data-surface='BannedWorks'
            className='flex min-w-0 flex-col gap-2'
          >
            <Label variant='overline'>Banned works</Label>
            {view.data.banned.length === 0 ? (
              <Muted>Nothing is banned here.</Muted>
            ) : (
              <ul className='flex min-w-0 flex-col gap-1.5'>
                <Paged items={view.data.banned} as='li'>
                  {(item) => (
                    <li
                      key={item.work.id}
                      className='flex min-w-0 items-center gap-2 rounded-md border px-2.5 py-1.5'
                    >
                      <Medallion icon={Ban} tone='warning' size='sm' />
                      <Who item={item.work} />
                      <Muted
                        as='span'
                        variant='caption'
                        className='flex-1'
                      >{`Since epoch ${item.since_epoch}`}</Muted>
                      <Button
                        size='sm'
                        variant='ghost'
                        disabled={busy !== null}
                        disabledReason={busy ?? undefined}
                        onClick={() =>
                          ban.mutate({ work: item.work.id, banned: false })
                        }
                      >
                        <Unlock />
                        Lift the ban
                      </Button>
                    </li>
                  )}
                </Paged>
              </ul>
            )}
          </div>
          <AdjustPanel
            surface='EraAdjust'
            title='Shape its era'
            note='Set the score or the age, hold them against the engine, or ban a work.'
          >
            <AdjustBlock title='Score and age' icon={Scale}>
              <label className='flex items-center gap-1.5'>
                <Switch
                  checked={hold}
                  aria-label='Hold what you set'
                  onCheckedChange={setHold}
                />
                <Muted as='span' variant='caption'>
                  Hold what you set
                </Muted>
              </label>
              <RowEditors>
                <RowEditor
                  label='Era score'
                  value={view.data.score}
                  min={-1000}
                  max={1000}
                  blocked={busy}
                  onSave={(score) => set.mutate({ score, hold })}
                />
                <ChoicePicker
                  label='Age'
                  value={view.data.age}
                  table={AGE_LOOK}
                  blocked={busy}
                  onPick={(age) => set.mutate({ age, hold })}
                />
              </RowEditors>
              {view.data.locked.length > 0 && (
                <div className='flex min-w-0 flex-wrap items-center gap-2'>
                  <Badge variant='secondary'>
                    <Lock aria-hidden='true' />
                    {`Held: ${view.data.locked.join(', ')}`}
                  </Badge>
                  <Button
                    size='sm'
                    variant='outline'
                    disabled={busy !== null}
                    disabledReason={busy ?? undefined}
                    onClick={() => set.mutate({ hold: false })}
                  >
                    <Unlock />
                    Let the deeds decide again
                  </Button>
                </div>
              )}
            </AdjustBlock>
            <AdjustBlock title='Ban a work' icon={Ban}>
              <EntityPicker
                types={WORK_TYPES}
                value={work}
                onChange={setWork}
                placeholder='Choose a book, creed or work'
              />
              <Button
                size='sm'
                variant='outline'
                className='self-start'
                disabled={busy !== null || work === null}
                disabledReason={
                  busy ?? (work === null ? 'Choose a work' : undefined)
                }
                onClick={() =>
                  work !== null && ban.mutate({ work, banned: true })
                }
              >
                <Ban />
                Ban it
              </Button>
            </AdjustBlock>
          </AdjustPanel>
        </div>
      )}
    </Section>
  )
}

export function WorldEraSection({
  worldId,
  readOnlyReason,
}: {
  worldId: number
  readOnlyReason?: string | null
}) {
  const view = useWorldEra(worldId)
  const { reason } = useGodGate()
  const blocked = readOnlyReason ?? reason()
  const set = useLoreAction<{ era: number; hold: boolean }>(
    '/api/actions/discovery:world_era',
    (value) => ({ world_id: worldId, ...value })
  )
  const busy = busyOf(blocked, set.isPending)
  return (
    <Section
      id='section-world-era'
      title='Era of the world'
      description='The world enters the next era when its most learned peoples know enough of what that era holds.'
      icon={Telescope}
    >
      {view.isPending && <LoadingBlock label='Reading the era' />}
      {view.isError && (
        <EmptyState
          icon={TriangleAlert}
          title='The era could not be read'
          description={view.error.message}
        />
      )}
      {view.data && (
        <div data-surface='WorldEra' className='flex min-w-0 flex-col gap-3'>
          <div className='flex min-w-0 items-center gap-3 rounded-lg border bg-muted/30 p-3'>
            <Medallion icon={Telescope} tone='gold' />
            <div className='flex min-w-0 flex-1 flex-col gap-1.5'>
              <div className='flex min-w-0 flex-wrap items-center gap-2'>
                <Text as='span' weight='semibold' className='flex-1'>
                  {view.data.name}
                </Text>
                <Badge variant='outline'>{`${view.data.era} of ${view.data.top}`}</Badge>
                {view.data.locked.length > 0 && (
                  <Badge variant='secondary'>
                    <Lock aria-hidden='true' />
                    Held
                  </Badge>
                )}
              </div>
              <Progress
                value={
                  view.data.era >= view.data.top
                    ? PERCENT
                    : view.data.next_share
                }
                aria-label='Toward the next era'
              />
              <Muted variant='caption'>
                {view.data.era >= view.data.top
                  ? 'The last era the techniques of this world reach.'
                  : `The leading peoples know ${view.data.next_share}% of the next era's techniques.`}
              </Muted>
            </div>
          </div>
          <RowEditor
            label='Era'
            value={view.data.era}
            min={1}
            max={view.data.top}
            blocked={busy}
            onSave={(era) => set.mutate({ era, hold: true })}
          >
            {view.data.locked.length > 0 && (
              <Button
                type='button'
                size='sm'
                variant='outline'
                disabled={busy !== null}
                disabledReason={busy ?? undefined}
                onClick={() => set.mutate({ era: view.data.era, hold: false })}
              >
                <Unlock />
                Release
              </Button>
            )}
          </RowEditor>
        </div>
      )}
    </Section>
  )
}
