import { useState } from 'react'
import {
  Accessibility,
  BedDouble,
  Biohazard,
  Lock,
  Moon,
  Sun,
  Thermometer,
  Unlock,
  UserPen,
  Users,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { formatInteger } from '@/lib/format'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label as FieldLabel } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import {
  EntityLink,
  Medallion,
  MiniStat,
  StatBar,
  Paged,
} from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { useGodAction } from '@/features/pantheon/godAction'
import { TargetBadges } from './diseaseParts'
import {
  AGE_SPEC,
  CLASS_SPEC,
  CONDITION_SPEC,
  SEX_SPEC,
  STATUS_SPEC,
  VECTOR_SPEC,
  type AgeBand,
  type CohortCondition,
  type Sex,
  type SocialClass,
} from './labels'
import { IconPicker, Panel } from './parts'
import { METER_TONE, WORKING, badTone } from './tones'

type Demography = components['schemas']['DemographyView']

const PERCENT = 100
const SICK_KEY = 'sick'
const MAIMED_KEY = 'maimed'

function useHold(communityId: number) {
  return useGodAction({
    run: ({ key, hold }: { key: string; hold: boolean }) =>
      hold
        ? unwrap(
            api.POST('/api/actions/lever:pin', {
              body: { node_id: communityId, key, epochs: null },
            })
          )
        : unwrap(
            api.POST('/api/actions/lever:unpin', {
              body: { node_id: communityId, key },
            })
          ),
    success: (_result, change) =>
      change.hold ? 'Held as it is' : 'Free to change again',
  })
}

export function SickCohorts({
  view,
  blocked,
}: {
  view: Demography
  blocked: string | null
}) {
  const hold = useHold(view.entity_id)
  const busy = blocked ?? (hold.isPending ? WORKING : null)
  const total = view.cohorts.reduce((sum, cohort) => sum + cohort.count, 0)
  const sick = view.cohorts
    .filter((cohort) => cohort.condition === 'sick')
    .reduce((sum, cohort) => sum + cohort.count, 0)
  const maimed = view.cohorts
    .filter((cohort) => cohort.condition === 'maimed')
    .reduce((sum, cohort) => sum + cohort.count, 0)
  const sickHeld = view.held.includes(SICK_KEY)
  const maimedHeld = view.held.includes(MAIMED_KEY)
  return (
    <Panel
      title='The sick and the maimed'
      icon={Thermometer}
      tone={sick > 0 ? 'danger' : 'muted'}
      hint='Outbreaks lay cohorts sick: they die first, bear no children, work less and cannot march when breath, body or sight is struck'
    >
      <div data-surface='SickCohorts' className='flex min-w-0 flex-col gap-3'>
        <div className='grid min-w-0 grid-cols-2 gap-2'>
          <MiniStat
            icon={CONDITION_SPEC.sick.icon}
            label='Lying sick'
            value={formatInteger(sick)}
            tone={sick > 0 ? 'danger' : 'muted'}
            hint={`${((sick / Math.max(1, total)) * PERCENT).toFixed(1)}% of the people`}
          />
          <MiniStat
            icon={Accessibility}
            label='Maimed'
            value={formatInteger(maimed)}
            tone={maimed > 0 ? 'warning' : 'muted'}
            hint={CONDITION_SPEC.maimed.hint}
          />
        </div>
        {view.afflictions.length === 0 ? (
          <Muted>No outbreak rages in their land.</Muted>
        ) : (
          <ul className='flex min-w-0 flex-col gap-2'>
            <Paged items={view.afflictions} as='li'>
              {(item) => {
                const vector = VECTOR_SPEC[item.vector]
                const status = STATUS_SPEC[item.status]
                return (
                  <li
                    key={item.outbreak_id}
                    className='flex min-w-0 items-start gap-2.5 rounded-lg border bg-muted/30 p-2'
                  >
                    <Medallion
                      icon={vector.icon}
                      tone={vector.tone}
                      size='sm'
                    />
                    <div className='flex min-w-0 flex-1 flex-col gap-1.5'>
                      <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
                        <EntityLink kind='entity' id={String(item.disease_id)}>
                          {item.disease}
                        </EntityLink>
                        <Badge
                          size='sm'
                          variant={
                            item.status === 'active' ? 'destructive' : 'warning'
                          }
                        >
                          <status.icon />
                          {status.label}
                        </Badge>
                      </div>
                      <TargetBadges targets={item.target_functions} />
                      <StatBar
                        label='Severity'
                        icon={Biohazard}
                        value={item.severity}
                        max={PERCENT}
                        tone={METER_TONE[badTone(item.severity)]}
                      />
                    </div>
                  </li>
                )
              }}
            </Paged>
          </ul>
        )}
        <div className='grid min-w-0 grid-cols-1 gap-2'>
          {[
            {
              key: SICK_KEY,
              held: sickHeld,
              label: 'Hold the sick',
            },
            {
              key: MAIMED_KEY,
              held: maimedHeld,
              label: 'Hold the maimed',
            },
          ].map((item) => (
            <div
              key={item.key}
              className='flex min-w-0 items-center justify-between gap-2 rounded-lg border bg-card p-2'
            >
              <FieldLabel
                htmlFor={`hold-${item.key}-${view.entity_id}`}
                className='flex items-center gap-1.5'
              >
                {item.held ? (
                  <Lock
                    aria-hidden='true'
                    className='size-icon-xs text-primary'
                  />
                ) : (
                  <Unlock
                    aria-hidden='true'
                    className='size-icon-xs text-muted-foreground'
                  />
                )}
                {item.label}
              </FieldLabel>
              <Switch
                id={`hold-${item.key}-${view.entity_id}`}
                checked={item.held}
                disabled={busy !== null}
                onCheckedChange={(checked) =>
                  hold.mutate({ key: item.key, hold: checked })
                }
              />
            </div>
          ))}
        </div>
      </div>
    </Panel>
  )
}

export function SetCohort({
  view,
  blocked,
}: {
  view: Demography
  blocked: string | null
}) {
  const [band, setBand] = useState<AgeBand>('adult')
  const [sex, setSex] = useState<Sex>('male')
  const [socialClass, setSocialClass] = useState<SocialClass>('farmer')
  const [condition, setCondition] = useState<CohortCondition>('none')
  const present =
    view.cohorts.find(
      (cohort) =>
        cohort.age_band === band &&
        cohort.sex === sex &&
        cohort.social_class === socialClass &&
        cohort.condition === condition
    )?.count ?? 0
  const [count, setCount] = useState('')
  const set = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/cohort:set', {
          body: {
            community_id: view.entity_id,
            age_band: band,
            sex,
            social_class: socialClass,
            condition,
            count: Math.max(0, Math.round(Number(count))),
          },
        })
      ),
    onDone: () => setCount(''),
  })
  const busy = blocked ?? (set.isPending ? WORKING : null)
  const parsed = Number(count)
  const invalid = count.trim() === '' || !Number.isInteger(parsed) || parsed < 0
  return (
    <Panel
      title='Set one cohort'
      icon={UserPen}
      hint='Give an exact headcount to one age, sex, class and condition; the population follows'
    >
      <div className='grid min-w-0 grid-cols-1 items-end gap-3 @md:grid-cols-2 @xl:grid-cols-3'>
        <IconPicker
          label='Age'
          value={band}
          table={AGE_SPEC}
          blocked={busy}
          onPick={(value) => setBand(value as AgeBand)}
        />
        <IconPicker
          label='Sex'
          value={sex}
          table={SEX_SPEC}
          blocked={busy}
          onPick={(value) => setSex(value as Sex)}
        />
        <IconPicker
          label='Class'
          value={socialClass}
          table={CLASS_SPEC}
          blocked={busy}
          onPick={(value) => setSocialClass(value as SocialClass)}
        />
        <IconPicker
          label='Condition'
          value={condition}
          table={CONDITION_SPEC}
          blocked={busy}
          onPick={(value) => setCondition(value as CohortCondition)}
        />
        <div className='flex min-w-0 flex-col gap-1.5'>
          <FieldLabel htmlFor={`cohort-count-${view.entity_id}`}>
            {`Headcount (now ${formatInteger(present)})`}
          </FieldLabel>
          <Input
            id={`cohort-count-${view.entity_id}`}
            type='number'
            min={0}
            value={count}
            placeholder={String(present)}
            disabled={busy !== null}
            onChange={(event) => setCount(event.target.value)}
          />
        </div>
        <Button
          size='sm'
          disabled={busy !== null || invalid}
          disabledReason={
            busy ?? (invalid ? 'Give a whole number of people.' : undefined)
          }
          onClick={() => set.mutate(undefined)}
        >
          <Users />
          Set the headcount
        </Button>
      </div>
    </Panel>
  )
}

export function DormancyPanel({
  view,
  blocked,
}: {
  view: Demography
  blocked: string | null
}) {
  const act = useGodAction({
    run: (body: {
      mortal_id: number
      dormant: boolean | null
      hold: boolean | null
    }) => unwrap(api.POST('/api/actions/mortal:dormancy', { body })),
  })
  const busy = blocked ?? (act.isPending ? WORKING : null)
  const sleeping = view.named.filter((mortal) => mortal.dormant).length
  return (
    <Panel
      title='Named mortals'
      icon={BedDouble}
      tone='verdigris'
      hint='Dormant mortals still age, heal, marry and die but skip careers, needs and opinions; any incident wakes them unless you hold them'
      aside={
        <Badge size='sm' variant='secondary'>
          <Moon />
          {`${sleeping} of ${view.named.length} asleep`}
        </Badge>
      }
    >
      <div data-surface='DormancyPanel' className='flex min-w-0 flex-col gap-2'>
        {view.named.length === 0 ? (
          <Muted>No named mortal lives here.</Muted>
        ) : (
          <ul className='flex min-w-0 flex-col gap-2'>
            <Paged items={view.named} as='li'>
              {(mortal) => (
                <li
                  key={mortal.id}
                  className='flex min-w-0 flex-wrap items-center gap-2 rounded-lg border bg-muted/30 p-2'
                >
                  <Medallion
                    icon={mortal.dormant ? Moon : Sun}
                    tone={mortal.dormant ? 'muted' : 'gold'}
                    size='sm'
                  />
                  <div className='flex min-w-0 flex-1 basis-40 flex-col'>
                    <EntityLink kind='entity' id={String(mortal.id)}>
                      {mortal.name}
                    </EntityLink>
                    <Muted as='span' variant='caption'>
                      {`${mortal.dormant ? 'Dormant' : 'Awake'}, importance ${mortal.importance}`}
                    </Muted>
                  </div>
                  {mortal.held && (
                    <Badge size='sm' variant='default'>
                      <Lock />
                      Held
                    </Badge>
                  )}
                  <Button
                    size='sm'
                    variant='outline'
                    disabled={busy !== null}
                    disabledReason={busy ?? undefined}
                    onClick={() =>
                      act.mutate({
                        mortal_id: mortal.id,
                        dormant: !mortal.dormant,
                        hold: null,
                      })
                    }
                  >
                    {mortal.dormant ? <Sun /> : <Moon />}
                    {mortal.dormant ? 'Wake' : 'Doze'}
                  </Button>
                  <Button
                    size='sm'
                    variant={mortal.held ? 'secondary' : 'outline'}
                    disabled={busy !== null}
                    disabledReason={busy ?? undefined}
                    onClick={() =>
                      act.mutate({
                        mortal_id: mortal.id,
                        dormant: null,
                        hold: !mortal.held,
                      })
                    }
                  >
                    {mortal.held ? <Unlock /> : <Lock />}
                    {mortal.held ? 'Release' : 'Hold'}
                  </Button>
                </li>
              )}
            </Paged>
          </ul>
        )}
        <Text as='span' variant='caption' className='text-muted-foreground'>
          Held mortals keep the state you give them; the engine neither wakes
          nor dozes them.
        </Text>
      </div>
    </Panel>
  )
}
