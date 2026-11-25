import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  Coins,
  HandHeart,
  HeartPulse,
  Lock,
  PartyPopper,
  Swords,
  Unlock,
  Users,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import {
  EmptyState,
  EntityLink,
  KpiTile,
  Medallion,
  Section,
  StatBar,
} from '@/components/domain'
import { ChoiceTiles } from '@/components/domain/SettingsKit'
import { Label, Muted, Text } from '@/components/typography'
import { AdjustStats } from '@/features/pantheon/AdjustStats'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { loreKeys } from '../api/keys'
import { MAIMED, READINGS, named } from '../body/labels'

type Customs = components['schemas']['BodyCustomsView']
type Maimed = components['schemas']['MaimedView']
type Reading = components['schemas']['BodyReading']
type MaimedKind = components['schemas']['MaimedKind']

const PERCENT = 100
const WORKING = 'Working on it.'
const LAWS: {
  key: 'wholeness_required' | 'seer_eye' | 'pension' | 'scar_festivals'
  label: string
  hint: string
}[] = [
  {
    key: 'wholeness_required',
    label: 'A ruler must be whole',
    hint: 'A ruler who loses a visible part is set aside for an heir.',
  },
  {
    key: 'seer_eye',
    label: "A lost eye is a seer's mark",
    hint: 'One-eyed seers gain presence.',
  },
  {
    key: 'pension',
    label: 'Maimed veterans are pensioned',
    hint: 'The maimed cost far less prosperity than beggars do.',
  },
  {
    key: 'scar_festivals',
    label: 'A festival of scars',
    hint: 'Martial peoples with many maimed veterans begin one on their own.',
  },
]
const LABELS: Record<string, string> = {
  reading: 'Reading of scars',
  wholeness_required: 'Wholeness law',
  seer_eye: "Seer's mark",
  pension: 'Pensions',
  scar_festivals: 'Scar festival',
}

function customsKey(id: number) {
  return [...loreKeys.entity(id), 'body-customs'] as const
}

function maimedKey(id: number) {
  return [...loreKeys.entity(id), 'maimed'] as const
}

export function PeopleBodyCustoms({ peopleId }: { peopleId: number }) {
  const { reason } = useGodGate()
  const [hold, setHold] = useState(true)
  const view = useQuery({
    queryKey: customsKey(peopleId),
    queryFn: () =>
      unwrap(
        api.GET('/api/peoples/{people_id}/body-customs', {
          params: { path: { people_id: peopleId } },
        })
      ),
    retry: false,
  })
  const set = useGodAction({
    writes: [{ lever: 'body:customs' }],
    run: ({ field, value }: { field: string; value: string | boolean }) =>
      unwrap(
        api.POST('/api/actions/body:customs', {
          body: { people_id: peopleId, field, value, lock: hold },
        })
      ),
    success: (_result, change: { field: string; value: string | boolean }) =>
      `${LABELS[change.field] ?? change.field} set`,
  })
  const release = useGodAction({
    writes: [{ lever: 'body:customs_unlock' }],
    run: (field: string) =>
      unwrap(
        api.POST('/api/actions/body:customs_unlock', {
          body: { people_id: peopleId, field },
        })
      ),
    success: (_result, field: string) =>
      `${LABELS[field] ?? field} may change on its own again`,
  })
  const customs: Customs | undefined = view.data
  const busy = reason() ?? (set.isPending || release.isPending ? WORKING : null)
  return (
    <Section
      id='section-body-customs'
      title='Wounds and bodies'
      description='How this people reads scars and missing parts: whom it honours, whom it shuns, and what it asks of its rulers and its maimed.'
      icon={HandHeart}
    >
      {!customs ? (
        <EmptyState
          icon={HandHeart}
          title='No customs yet'
          description='The next epoch reads them from the people and its gods.'
        />
      ) : (
        <div className='@container/customs flex min-w-0 flex-col gap-4'>
          <div className='flex min-w-0 items-center gap-3 rounded-md border surface-framed border-gild/70 bg-card p-3'>
            <Medallion
              icon={named(READINGS, customs.reading).icon}
              tone={named(READINGS, customs.reading).tone ?? 'gold'}
            />
            <div className='flex min-w-0 flex-1 flex-col gap-1.5'>
              <Text weight='semibold'>
                {named(READINGS, customs.reading).label}
              </Text>
              <Muted variant='caption'>{READINGS[customs.reading]?.hint}</Muted>
              <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
                {customs.derived_reading !== customs.reading && (
                  <Badge size='sm' variant='secondary'>
                    {`Their gods would make it ${named(READINGS, customs.derived_reading).label.toLowerCase()}`}
                  </Badge>
                )}
                {customs.maimed_rulers > 0 && (
                  <Badge size='sm' variant='destructive'>
                    {`${customs.maimed_rulers} maimed ${customs.maimed_rulers === 1 ? 'ruler' : 'rulers'}`}
                  </Badge>
                )}
                {customs.tradition_id !== null && customs.tradition_name && (
                  <EntityLink
                    kind='entity'
                    id={String(customs.tradition_id)}
                    showIcon
                  >
                    {customs.tradition_name}
                  </EntityLink>
                )}
              </div>
            </div>
          </div>
          <div className='flex min-w-0 flex-col gap-4 rounded-md p-3 sealed-well'>
            <div className='flex min-w-0 flex-wrap items-center justify-between gap-3'>
              <div className='flex min-w-0 flex-col gap-0.5'>
                <Text weight='semibold'>Set their customs</Text>
                <Muted variant='caption'>
                  A held custom no longer follows their gods and their wars
                  until you release it. Every change can be undone.
                </Muted>
              </div>
              <label className='flex shrink-0 items-center gap-2'>
                <Switch
                  permission='lock_canon'
                  checked={hold}
                  onCheckedChange={setHold}
                  aria-label='Hold what I set'
                />
                <Text as='span'>Hold what I set</Text>
              </label>
            </div>
            {customs.locked.length > 0 && (
              <div className='flex min-w-0 flex-wrap items-center gap-2'>
                <Lock
                  aria-hidden='true'
                  className='size-icon-xs text-primary'
                />
                {customs.locked.map((key) => (
                  <Button
                    act={release}
                    key={key}
                    size='sm'
                    variant='outline'
                    disabled={busy !== null}
                    disabledReason={busy ?? undefined}
                    onClick={() => release.mutate(key)}
                  >
                    <Unlock />
                    {`Release ${(LABELS[key] ?? key).toLowerCase()}`}
                  </Button>
                ))}
              </div>
            )}
            <ChoiceTiles<Reading>
              act={set}
              label='Reading of scars'
              value={customs.reading}
              columns={2}
              options={Object.entries(READINGS).map(([key, value]) => ({
                value: key as Reading,
                label: value.label,
                hint: value.hint,
                icon: value.icon,
              }))}
              onChange={(value) =>
                busy === null && set.mutate({ field: 'reading', value })
              }
            />
            <div className='grid min-w-0 grid-cols-1 gap-3 @md/customs:grid-cols-2'>
              {LAWS.map((law) => (
                <label
                  key={law.key}
                  className='flex min-w-0 items-start gap-3 rounded-md border surface-framed border-gild/70 bg-card p-3'
                >
                  <Switch
                    act={set}
                    checked={customs[law.key]}
                    disabled={busy !== null}
                    onCheckedChange={(value) =>
                      set.mutate({ field: law.key, value })
                    }
                    aria-label={law.label}
                  />
                  <span className='flex min-w-0 flex-col gap-0.5'>
                    <Text as='span' weight='medium'>
                      {law.label}
                    </Text>
                    <Muted as='span' variant='caption'>
                      {law.hint}
                    </Muted>
                  </span>
                </label>
              ))}
            </div>
          </div>
        </div>
      )}
    </Section>
  )
}

export function CommunityMaimed({ communityId }: { communityId: number }) {
  const view = useQuery({
    queryKey: maimedKey(communityId),
    queryFn: () =>
      unwrap(
        api.GET('/api/communities/{community_id}/maimed', {
          params: { path: { community_id: communityId } },
        })
      ),
    retry: false,
  })
  const data: Maimed | undefined = view.data
  const run = ({ key, value }: { key: string; value: number }) =>
    unwrap(
      api.POST('/api/actions/body:cohort', {
        body: {
          community_id: communityId,
          kind: key as MaimedKind,
          count: value,
        },
      })
    )
  const counts = Object.fromEntries(
    (data?.cohorts ?? []).map((row) => [row.kind, row])
  )
  return (
    <Section
      id='section-maimed'
      title='The maimed'
      description='Soldiers who came home without an arm, a leg or an eye: what they cost in work and prosperity, and how they sour or steel their people for war.'
      icon={Users}
    >
      {!data ? (
        <EmptyState
          icon={Users}
          title='Nothing to show'
          description='This community keeps no count of its maimed.'
        />
      ) : (
        <div className='@container/maimed flex min-w-0 flex-col gap-4'>
          <div className='grid min-w-0 grid-cols-1 gap-3 @md/maimed:grid-cols-2 @3xl/maimed:grid-cols-4'>
            <KpiTile
              label='The maimed'
              value={data.total}
              icon={Users}
              tone='warning'
              hint={`${data.veterans} of them veterans; ${data.share_pct}% of ${data.population}`}
              meter={{
                value: data.share_pct,
                max: PERCENT,
                label: 'Share of the people',
              }}
            />
            <KpiTile
              label='Work done'
              value={`${data.labour_pct}%`}
              icon={Coins}
              tone='gold'
              change={data.labour_pct - PERCENT}
              hint='Food and craft output, against a whole people'
            />
            <KpiTile
              label='Appetite for war'
              value={`${data.war_appetite_pct}%`}
              icon={Swords}
              tone='danger'
              change={data.war_appetite_pct - PERCENT}
              hint='Peoples that honour scars keep their appetite; others tire of war'
            />
            <KpiTile
              label='Call for healers'
              value={`${data.healer_demand_pct}%`}
              icon={HeartPulse}
              tone='success'
              change={data.healer_demand_pct - PERCENT}
              hint='How much more often healers are born here'
            />
          </div>
          <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
            {data.pension ? (
              <Badge size='sm' variant='success'>
                Pensioned
              </Badge>
            ) : (
              <Badge size='sm' variant='warning'>
                No pension: they beg
              </Badge>
            )}
            {data.reading && (
              <Badge size='sm' variant='default'>
                {named(READINGS, data.reading).label}
              </Badge>
            )}
            {data.people_id !== null && data.people_name && (
              <>
                <Muted variant='caption'>Customs of</Muted>
                <EntityLink kind='entity' id={String(data.people_id)} showIcon>
                  {data.people_name}
                </EntityLink>
              </>
            )}
          </div>
          <div className='grid min-w-0 grid-cols-1 gap-3 @xl/maimed:grid-cols-3'>
            {Object.entries(MAIMED).map(([key, kind]) => {
              const row = counts[key]
              return (
                <div
                  key={key}
                  className='flex min-w-0 items-center gap-3 rounded-md border surface-framed border-gild/70 bg-card p-3'
                >
                  <Medallion
                    icon={kind.icon}
                    tone={row ? (kind.tone ?? 'muted') : 'muted'}
                    size='sm'
                  />
                  <div className='flex min-w-0 flex-1 flex-col gap-1'>
                    <Label>{kind.label}</Label>
                    <StatBar
                      label='Count'
                      value={row?.count ?? 0}
                      max={Math.max(1, data.total)}
                      tone='warning'
                      showMax={false}
                    />
                  </div>
                </div>
              )
            })}
          </div>
          {data.total === 0 && (
            <Muted>
              No maimed veteran has come home yet. They fill after battles.
            </Muted>
          )}
          <div className='flex min-w-0 flex-col gap-3 rounded-md p-3 sealed-well'>
            <div className='flex min-w-0 items-center gap-2'>
              <PartyPopper
                aria-hidden='true'
                className='size-icon-sm text-muted-foreground'
              />
              <Text weight='semibold'>Set their numbers</Text>
            </div>
            <AdjustStats
              id={`maimed-${communityId}`}
              groups={[
                {
                  title: 'Maimed in this community',
                  fields: Object.entries(MAIMED).map(([key, kind]) => ({
                    key,
                    label: kind.label,
                    value: counts[key]?.count ?? 0,
                    min: 0,
                  })),
                },
              ]}
              note='Pensions and the reading of scars are set in the Wounds and bodies section of their people.'
              run={run}
            />
          </div>
        </div>
      )}
    </Section>
  )
}
