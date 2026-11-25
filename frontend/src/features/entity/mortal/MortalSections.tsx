import { useState } from 'react'
import {
  Gavel,
  Heart,
  Link2,
  Lock,
  PenLine,
  Plus,
  Trash2,
  Unlock,
  X,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import {
  EmptyState,
  KpiTile,
  Paged,
  PagedList,
  Section,
  StatBar,
} from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { UNION_FORMS, UNION_PURPOSES } from '@/features/cycles/unionLabels'
import { CRIMES } from '@/features/entity/justice/crimes'
import { type AdjustGroup, AdjustStats } from '@/features/pantheon/AdjustStats'
import { type ActionResponse } from '@/features/pantheon/api'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { RowAction } from '../actions/RowAction'
import { MindPicker } from '../mind/parts'
import { named, plain } from '../realm/labels'
import {
  AdjustPanel,
  Fact,
  Hero,
  Panel,
  RecordField,
  RefLink,
  Tag,
} from '../realm/parts'
import {
  type CrimeKind,
  type EquipmentSlot,
  type MarriageEnd,
  type UnionForm,
  type UnionPurpose,
  type MortalProfile,
  type MortalSex,
  type PunishmentKind,
  familyKey,
  profileKey,
  useMortalProfile,
} from './api'
import {
  BREAKS,
  CAREERS,
  DEATHS,
  GEAR_ICON,
  HELD_LABELS,
  KIN_ICON,
  KIN_KINDS,
  LIFE_FIELDS,
  LOYALTY_FIELDS,
  MARRIAGE_ENDS,
  MORTAL_ICON,
  PROFESSIONS,
  PUNISHMENTS,
  SEXES,
  SLOTS,
  SLOT_TYPES,
  STAGES,
  STANDING_FIELDS,
} from './labels'
import { FamilyTreePanel } from './tree/FamilyTreePanel'

const PERCENT = 100
const WORKING = 'Working on it.'
const MORTALS = ['mortal'] as const

function table(source: Record<string, { label: string }>) {
  return Object.fromEntries(
    Object.entries(source).map(([key, value]) => [key, value.label])
  )
}

function useMortalAction(mortalId: number) {
  return useGodAction({
    writes: [
      { lever: 'kin:betroth' },
      { lever: 'kin:bond' },
      { lever: 'kin:delete_marriage' },
      { lever: 'kin:edit_marriage' },
      { lever: 'kin:end_marriage' },
      { lever: 'kin:marry' },
      { lever: 'kin:unbond' },
      { lever: 'mortal:equip' },
      { lever: 'mortal:equip_release' },
      { lever: 'mortal:pardon' },
      { lever: 'mortal:release' },
      { lever: 'mortal:sentence' },
      { lever: 'mortal:set' },
      { lever: 'mortal:sex' },
    ],
    run: ({ path, body }: { path: string; body: Record<string, unknown> }) =>
      postAction(path, body),
    invalidate: [profileKey(mortalId), familyKey(mortalId)],
  })
}

function postAction(
  path: string,
  body: Record<string, unknown>
): Promise<ActionResponse> {
  const post = api.POST as unknown as (
    route: string,
    init: { body: Record<string, unknown> }
  ) => Parameters<typeof unwrap>[0]
  return unwrap(post(path, { body })) as Promise<ActionResponse>
}

function heldLabel(field: string): string {
  return HELD_LABELS[field] ?? plain({}, field.replace(/_id$/, ''))
}

function LifeHero({ profile }: { profile: MortalProfile }) {
  const stage = named(STAGES, profile.life_stage)
  const sex = named(SEXES, profile.sex)
  return (
    <Hero
      icon={stage.icon}
      tone={stage.tone}
      eyebrow='Life course'
      title={`${stage.label}, ${sex.label.toLowerCase()}`}
    >
      <Tag spec={sex} />
      {profile.career && <Tag spec={named(CAREERS, profile.career)} />}
      {profile.profession && (
        <Tag spec={named(PROFESSIONS, profile.profession)} />
      )}
      {profile.social_class && (
        <Badge size='sm' variant='outline'>
          {plain({}, profile.social_class)}
        </Badge>
      )}
      {profile.cause_of_death && (
        <Tag
          spec={named(DEATHS, profile.cause_of_death)}
          text={`Died of ${named(DEATHS, profile.cause_of_death).label.toLowerCase()}`}
        />
      )}
    </Hero>
  )
}

function LifeKpis({ profile }: { profile: MortalProfile }) {
  const breaking = profile.stress >= profile.stress_threshold
  return (
    <div className='grid min-w-0 grid-cols-1 gap-3 @md/life:grid-cols-2 @2xl/life:grid-cols-4'>
      <KpiTile
        label='Health'
        value={profile.health}
        icon={LIFE_FIELDS.health.icon}
        tone={profile.health < PERCENT / 4 ? 'danger' : 'success'}
        meter={{ value: profile.health, max: PERCENT, label: 'Health' }}
        hint='Chronic illness, age and open wounds wear it down'
      />
      <KpiTile
        label='Stress'
        value={profile.stress}
        icon={LIFE_FIELDS.stress.icon}
        tone={breaking ? 'danger' : 'warning'}
        harmful
        meter={{ value: profile.stress, max: PERCENT, label: 'Stress' }}
        hint={`Breaks at ${profile.stress_threshold}`}
      />
      <KpiTile
        label='Renown'
        value={profile.renown}
        icon={STANDING_FIELDS.renown.icon}
        tone='gold'
        meter={{ value: profile.renown, max: PERCENT, label: 'Renown' }}
      />
      <KpiTile
        label='Wealth'
        value={profile.wealth}
        icon={STANDING_FIELDS.wealth.icon}
        tone='gold'
        meter={{ value: profile.wealth, max: PERCENT, label: 'Wealth' }}
      />
    </div>
  )
}

function Standing({ profile }: { profile: MortalProfile }) {
  return (
    <Panel title='Standing' icon={STANDING_FIELDS.honour.icon} tone='gold'>
      <ul className='flex min-w-0 flex-col gap-2'>
        {(['honour', 'infamy', 'education'] as const).map((key) => (
          <li key={key}>
            <StatBar
              label={STANDING_FIELDS[key].label}
              value={profile[key]}
              max={PERCENT}
              icon={STANDING_FIELDS[key].icon}
              tone={key === 'infamy' ? 'destructive' : 'default'}
              showMax={false}
            />
          </li>
        ))}
        {profile.legitimacy !== null && (
          <li>
            <StatBar
              label='Legitimacy in office'
              value={profile.legitimacy}
              max={PERCENT}
              icon={Gavel}
              showMax={false}
            />
          </li>
        )}
      </ul>
      <Fact icon={LIFE_FIELDS.fertility.icon} label='Fertility'>
        <Text>{profile.fertility}</Text>
      </Fact>
      {profile.last_break && (
        <Fact icon={named(BREAKS, profile.last_break).icon} label='Last broke'>
          <Tag spec={named(BREAKS, profile.last_break)} />
          {profile.last_break_epoch !== null && (
            <Muted variant='caption'>{`epoch ${profile.last_break_epoch}`}</Muted>
          )}
        </Fact>
      )}
    </Panel>
  )
}

function Loyalty({ profile }: { profile: MortalProfile }) {
  return (
    <Panel
      title='Loyalty'
      icon={LOYALTY_FIELDS.loyalty_liege.icon}
      tone='verdigris'
      hint='A torn heart breeds stress; a low one breeds plots'
    >
      {profile.polity && (
        <Fact icon={LOYALTY_FIELDS.loyalty_liege.icon} label='Realm'>
          <RefLink node={profile.polity} />
        </Fact>
      )}
      <ul className='flex min-w-0 flex-col gap-2'>
        {(['loyalty_liege', 'loyalty_community', 'loyalty_god'] as const).map(
          (key) => (
            <li key={key}>
              <StatBar
                label={LOYALTY_FIELDS[key].label}
                value={profile[key]}
                max={PERCENT}
                icon={LOYALTY_FIELDS[key].icon}
                showMax={false}
              />
            </li>
          )
        )}
      </ul>
      {profile.death_place && (
        <Fact icon={named(DEATHS, 'unknown').icon} label='Died at'>
          <RefLink node={profile.death_place} />
        </Fact>
      )}
    </Panel>
  )
}

function lifeGroups(profile: MortalProfile): AdjustGroup[] {
  return [
    {
      title: 'Life',
      fields: (['health', 'fertility', 'stress'] as const).map((key) => ({
        key,
        label: LIFE_FIELDS[key].label,
        value: profile[key],
        min: 0,
        max: PERCENT,
      })),
    },
    {
      title: 'Standing',
      fields: (
        ['wealth', 'renown', 'honour', 'infamy', 'education'] as const
      ).map((key) => ({
        key,
        label: STANDING_FIELDS[key].label,
        value: profile[key],
        min: 0,
        max: PERCENT,
      })),
    },
    {
      title: 'Loyalty',
      fields: (
        ['loyalty_liege', 'loyalty_community', 'loyalty_god'] as const
      ).map((key) => ({
        key,
        label: LOYALTY_FIELDS[key].label,
        value: profile[key],
        min: 0,
        max: PERCENT,
      })),
    },
  ]
}

function LifeControls({
  profile,
  readOnlyReason,
}: {
  profile: MortalProfile
  readOnlyReason: string | null
}) {
  const mortalId = profile.mortal.id
  const [hold, setHold] = useState(true)
  const [crime, setCrime] = useState('')
  const [punishment, setPunishment] = useState('')
  const action = useMortalAction(mortalId)
  const busy = readOnlyReason ?? (action.isPending ? WORKING : null)
  const send = (path: string, body: Record<string, unknown>) =>
    action.mutateAsync({ path, body: { mortal_id: mortalId, ...body } })
  const run = ({ key, value }: { key: string; value: number }) =>
    send('/api/actions/mortal:set', { field: key, value, hold })
  return (
    <AdjustPanel
      acts={[action]}
      title='Shape this life'
      note='Set health, stress, standing and loyalty; choose a stage, a sex or a path; sentence or pardon. A held value stops following their life until you release it. Every change goes into the ledger and can be undone.'
      hold={hold}
      onHold={setHold}
    >
      <div className='grid min-w-0 grid-cols-1 gap-3 @md/life:grid-cols-2 @2xl/life:grid-cols-4'>
        <MindPicker
          act={action}
          label='Life stage'
          value={profile.life_stage}
          table={table(STAGES)}
          blocked={busy}
          onPick={(value) =>
            void send('/api/actions/mortal:set', {
              field: 'life_stage',
              value,
              hold,
            })
          }
        />
        <MindPicker
          act={action}
          label='Sex'
          value={profile.sex}
          table={table(SEXES)}
          blocked={busy}
          onPick={(value) =>
            void send('/api/actions/mortal:sex', { sex: value as MortalSex })
          }
        />
        <MindPicker
          act={action}
          label='Profession'
          value={profile.profession ?? ''}
          table={table(PROFESSIONS)}
          blocked={busy}
          placeholder='No profession yet'
          onPick={(value) =>
            void send('/api/actions/mortal:set', {
              field: 'profession',
              value,
              hold,
            })
          }
        />
        <MindPicker
          act={action}
          label='Path in life'
          value={profile.career ?? ''}
          table={table(CAREERS)}
          blocked={busy}
          placeholder='No path chosen'
          onPick={(value) =>
            void send('/api/actions/mortal:set', {
              field: 'career',
              value,
              hold,
            })
          }
        />
      </div>
      {profile.held.length > 0 && (
        <div className='flex min-w-0 flex-col gap-2'>
          <PagedList
            items={profile.held}
            initial={12}
            noun={['entry', 'entries']}
            as='div'
            className='flex min-w-0 flex-wrap items-center gap-2'
            itemKey={(field) => field}
          >
            {(field) => (
              <Button
                act={action}
                key={field}
                size='sm'
                variant='outline'
                disabled={busy !== null}
                disabledReason={busy ?? undefined}
                onClick={() =>
                  void send('/api/actions/mortal:release', { field })
                }
              >
                <Unlock />
                {`Release ${heldLabel(field)}`}
              </Button>
            )}
          </PagedList>
        </div>
      )}
      <AdjustStats
        id={`life-${mortalId}`}
        groups={lifeGroups(profile)}
        note='Every value runs from 0 to 100.'
        run={run}
      />
      <div className='flex min-w-0 flex-col gap-2 rounded-md border surface-framed border-gild/70 bg-card p-3'>
        <Text weight='semibold'>Judgement</Text>
        <Muted variant='caption'>
          Sentence this mortal under the law, or pardon an exile. Maiming and
          death mark the judge with infamy.
        </Muted>
        <div className='grid min-w-0 grid-cols-1 gap-3 @md/life:grid-cols-2'>
          <MindPicker
            label='Crime'
            value={crime}
            table={table(CRIMES)}
            blocked={busy}
            placeholder='Choose a crime'
            onPick={setCrime}
          />
          <MindPicker
            label='Punishment'
            value={punishment}
            table={table(PUNISHMENTS)}
            blocked={busy}
            placeholder='Choose a punishment'
            onPick={setPunishment}
          />
        </div>
        <div className='flex min-w-0 flex-wrap gap-2'>
          <Button
            act={action}
            size='sm'
            variant='destructive'
            disabled={busy !== null || crime === '' || punishment === ''}
            disabledReason={busy ?? 'Choose a crime and a punishment first.'}
            onClick={() =>
              void send('/api/actions/mortal:sentence', {
                crime: crime as CrimeKind,
                punishment: punishment as PunishmentKind,
              })
            }
          >
            <Gavel />
            Sentence
          </Button>
          <Button
            act={action}
            size='sm'
            variant='outline'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => void send('/api/actions/mortal:pardon', {})}
          >
            Pardon
          </Button>
        </div>
      </div>
    </AdjustPanel>
  )
}

const UNION_FORM_KEYS = Object.keys(UNION_FORMS) as UnionForm[]
const UNION_PURPOSE_KEYS = Object.keys(UNION_PURPOSES) as UnionPurpose[]

export function LifeSection({
  mortalId,
  readOnlyReason,
}: {
  mortalId: number
  readOnlyReason?: string | null
}) {
  const { reason } = useGodGate()
  const query = useMortalProfile(mortalId)
  const profile = query.data
  return (
    <Section
      id='section-life'
      title='Life'
      description='The course of a life, health, stress, standing and loyalty. Each epoch ages, tests and moves them. Body and mind are set in the mind section.'
      icon={MORTAL_ICON}
    >
      {!profile ? (
        <EmptyState
          icon={MORTAL_ICON}
          title='No life recorded yet'
          description='The next epoch reads this mortal and records their life.'
        />
      ) : (
        <div className='@container/life flex min-w-0 flex-col gap-4'>
          <LifeHero profile={profile} />
          <LifeKpis profile={profile} />
          <div className='grid min-w-0 grid-cols-1 gap-3 @xl/life:grid-cols-2'>
            <Standing profile={profile} />
            <Loyalty profile={profile} />
          </div>
          <LifeControls
            profile={profile}
            readOnlyReason={readOnlyReason ?? reason()}
          />
        </div>
      )}
    </Section>
  )
}

function KinControls({
  profile,
  readOnlyReason,
}: {
  profile: MortalProfile
  readOnlyReason: string | null
}) {
  const mortalId = profile.mortal.id
  const [other, setOther] = useState<number | null>(null)
  const [form, setForm] = useState<UnionForm>('pair')
  const [purpose, setPurpose] = useState<UnionPurpose>('kinship')
  const [bond, setBond] = useState('parent_of')
  const [forced, setForced] = useState(true)
  const action = useMortalAction(mortalId)
  const busy = readOnlyReason ?? (action.isPending ? WORKING : null)
  const need = busy ?? (other === null ? 'Choose a mortal first.' : null)
  const send = (path: string, body: Record<string, unknown>) =>
    void action.mutateAsync({ path, body })
  return (
    <AdjustPanel
      acts={[action]}
      title='Bind and part'
      note='Promise, wed or bind this mortal to another; end or strike out a marriage. A forced marriage leaves both bitter. Every change can be undone from the ledger.'
    >
      <RecordField
        label='The other mortal'
        types={MORTALS}
        value={other}
        onChange={setOther}
        blocked={busy}
      />
      <div className='grid min-w-0 grid-cols-1 gap-3 @md/kin:grid-cols-2'>
        <MindPicker
          label='Form of the union'
          value={form}
          table={table(UNION_FORMS)}
          blocked={busy}
          onPick={(value) => setForm(value as UnionForm)}
        />
        <MindPicker
          label='What it is for'
          value={purpose}
          table={table(UNION_PURPOSES)}
          blocked={busy}
          onPick={(value) => setPurpose(value as UnionPurpose)}
        />
        <MindPicker
          label='Kin bond'
          value={bond}
          table={table(KIN_KINDS)}
          blocked={busy}
          onPick={setBond}
        />
      </div>
      <label className='flex items-center gap-2'>
        <Switch
          checked={forced}
          onCheckedChange={setForced}
          aria-label='Against their will'
        />
        <Text as='span'>Against their will</Text>
      </label>
      <div className='flex min-w-0 flex-wrap gap-2'>
        <Button
          act={action}
          size='sm'
          variant='outline'
          disabled={need !== null}
          disabledReason={need ?? undefined}
          onClick={() =>
            send('/api/actions/kin:betroth', {
              first_id: mortalId,
              second_id: other,
            })
          }
        >
          <Heart />
          Betroth
        </Button>
        <Button
          act={action}
          size='sm'
          disabled={need !== null}
          disabledReason={need ?? undefined}
          onClick={() =>
            send('/api/actions/kin:marry', {
              first_id: mortalId,
              second_id: other,
              form,
              purpose,
              forced,
            })
          }
        >
          <Plus />
          Wed
        </Button>
        <Button
          act={action}
          size='sm'
          variant='outline'
          disabled={need !== null}
          disabledReason={need ?? undefined}
          onClick={() =>
            send('/api/actions/kin:bond', {
              source_id: mortalId,
              target_id: other,
              kind: bond,
            })
          }
        >
          <Link2 />
          Bind as kin
        </Button>
      </div>
      {profile.marriages.some((item) => item.end_epoch === null) && (
        <div className='flex min-w-0 flex-col gap-2'>
          <Label variant='overline'>Change or end a marriage</Label>
          {profile.marriages
            .filter((item) => item.end_epoch === null)
            .map((item) => (
              <div
                key={item.id}
                className='flex min-w-0 flex-wrap items-center gap-2'
              >
                <Text truncate>{item.spouse?.name ?? 'A spouse'}</Text>
                <RowAction
                  path='/api/actions/kin:edit_marriage'
                  icon={PenLine}
                  label='Change it'
                  fixed={{ marriage_id: item.id }}
                  defaults={{
                    form: item.form,
                    purpose: item.purpose,
                    treaty_id: item.treaty?.id ?? null,
                    start_epoch: item.start_epoch,
                  }}
                  labels={{
                    form: 'Form of the union',
                    purpose: 'What it is for',
                    treaty_id: 'Sealing treaty',
                    start_epoch: 'Wed in epoch',
                  }}
                  pickers={{
                    treaty_id: { source: 'entity', types: ['treaty'] },
                  }}
                  choices={{
                    form: UNION_FORM_KEYS.map((key) => ({
                      value: key,
                      label: UNION_FORMS[key].label,
                    })),
                    purpose: UNION_PURPOSE_KEYS.map((key) => ({
                      value: key,
                      label: UNION_PURPOSES[key].label,
                    })),
                  }}
                />
                {(['divorce', 'annulment'] as const).map((cause) => (
                  <Button
                    act={action}
                    key={cause}
                    size='sm'
                    variant='outline'
                    disabled={busy !== null}
                    disabledReason={busy ?? undefined}
                    onClick={() =>
                      send('/api/actions/kin:end_marriage', {
                        marriage_id: item.id,
                        cause: cause as MarriageEnd,
                      })
                    }
                  >
                    {named(MARRIAGE_ENDS, cause).label}
                  </Button>
                ))}
                <Button
                  act={action}
                  size='sm'
                  variant='ghost'
                  disabled={busy !== null}
                  disabledReason={busy ?? undefined}
                  onClick={() =>
                    send('/api/actions/kin:delete_marriage', {
                      marriage_id: item.id,
                    })
                  }
                >
                  <Trash2 />
                  Strike out
                </Button>
              </div>
            ))}
        </div>
      )}
    </AdjustPanel>
  )
}

export function KinSection({
  mortalId,
  readOnlyReason,
}: {
  mortalId: number
  readOnlyReason?: string | null
}) {
  const { reason } = useGodGate()
  const profile = useMortalProfile(mortalId).data
  const blocked = readOnlyReason ?? reason()
  const action = useMortalAction(mortalId)
  return (
    <Section
      id='section-kin'
      title='Kin'
      description='Parents, children, spouses, the promised, wards and sworn kin, read from typed bonds of blood and marriage.'
      icon={KIN_ICON}
    >
      {!profile ? (
        <EmptyState
          icon={KIN_ICON}
          title='No kin recorded'
          description='Births, marriages and fostering will fill this tree.'
        />
      ) : (
        <div className='@container/kin flex min-w-0 flex-col gap-4'>
          <FamilyTreePanel mortalId={mortalId} blocked={blocked} />
          <div className='grid min-w-0 grid-cols-1 gap-3 @xl/kin:grid-cols-2'>
            <Panel
              title='Marriages'
              icon={UNION_FORMS.pair.icon}
              tone='danger'
              count={profile.marriages.length}
            >
              {profile.marriages.length === 0 && <Muted>Never wed.</Muted>}
              <ul className='flex min-w-0 flex-col gap-2'>
                <Paged items={profile.marriages} as='li'>
                  {(item) => (
                    <li
                      key={item.id}
                      className='flex min-w-0 flex-wrap items-center gap-2'
                    >
                      <Tag spec={UNION_FORMS[item.form]} />
                      <Tag spec={UNION_PURPOSES[item.purpose]} />
                      {item.spouse && <RefLink node={item.spouse} />}
                      <Muted variant='caption'>
                        {item.end_epoch === null
                          ? `since epoch ${item.start_epoch}`
                          : `epoch ${item.start_epoch}–${item.end_epoch}`}
                      </Muted>
                      {item.cause_end && (
                        <Tag spec={named(MARRIAGE_ENDS, item.cause_end)} />
                      )}
                      {item.forced && (
                        <Badge size='sm' variant='destructive'>
                          Forced
                        </Badge>
                      )}
                    </li>
                  )}
                </Paged>
              </ul>
            </Panel>
            <Panel
              title='Bonds of kin'
              icon={KIN_KINDS.sworn_kin.icon}
              tone='info'
              count={profile.kin.length}
            >
              {profile.kin.length === 0 && <Muted>No kin bonds.</Muted>}
              <ul className='flex min-w-0 flex-col gap-2'>
                <Paged items={profile.kin} as='li'>
                  {(link) => {
                    const spec = named(KIN_KINDS, link.kind)
                    const role = KIN_KINDS[link.kind]
                    return (
                      <li
                        key={link.bond_id}
                        className='flex min-w-0 items-center gap-2'
                      >
                        <Tag
                          spec={spec}
                          text={
                            role
                              ? link.outgoing
                                ? role.out
                                : role.in
                              : undefined
                          }
                        />
                        <span className='min-w-0 flex-1 truncate'>
                          <RefLink node={link.other} />
                        </span>
                        <Button
                          act={action}
                          size='icon'
                          variant='ghost'
                          aria-label='Undo this bond'
                          disabled={blocked !== null || action.isPending}
                          disabledReason={blocked ?? undefined}
                          onClick={() =>
                            void action.mutateAsync({
                              path: '/api/actions/kin:unbond',
                              body: { bond_id: link.bond_id },
                            })
                          }
                        >
                          <X />
                        </Button>
                      </li>
                    )
                  }}
                </Paged>
              </ul>
            </Panel>
          </div>
          <KinControls profile={profile} readOnlyReason={blocked} />
        </div>
      )}
    </Section>
  )
}

export function EquipmentSection({
  mortalId,
  readOnlyReason,
}: {
  mortalId: number
  readOnlyReason?: string | null
}) {
  const { reason } = useGodGate()
  const profile = useMortalProfile(mortalId).data
  const [slot, setSlot] = useState<EquipmentSlot>('wielded_main')
  const [item, setItem] = useState<number | null>(null)
  const [hold, setHold] = useState(true)
  const action = useMortalAction(mortalId)
  const blocked = readOnlyReason ?? reason()
  const busy = blocked ?? (action.isPending ? WORKING : null)
  const send = (path: string, body: Record<string, unknown>) =>
    void action.mutateAsync({ path, body: { mortal_id: mortalId, ...body } })
  return (
    <Section
      id='section-gear'
      title='Gear'
      description='What this mortal carries: weapons in hand, armour, a helm, a mount and a focus for magic. Each changes how they fight, ride and cast.'
      icon={GEAR_ICON}
    >
      {!profile ? (
        <EmptyState
          icon={GEAR_ICON}
          title='No gear recorded'
          description='The next epoch fits this mortal with what they own.'
        />
      ) : (
        <div className='@container/gear flex min-w-0 flex-col gap-4'>
          <ul className='grid min-w-0 grid-cols-1 gap-2 @md/gear:grid-cols-2 @2xl/gear:grid-cols-3'>
            <Paged items={profile.equipment} as='li'>
              {(entry) => {
                const spec = named(SLOTS, entry.slot)
                return (
                  <li
                    key={entry.slot}
                    className='flex min-w-0 items-center gap-2 rounded-md border surface-sheen border-gild/60 bg-card p-2'
                  >
                    <spec.icon
                      aria-hidden='true'
                      className='size-icon-sm shrink-0 text-muted-foreground'
                    />
                    <div className='flex min-w-0 flex-1 flex-col'>
                      <Label variant='overline'>{spec.label}</Label>
                      {entry.item ? (
                        <RefLink node={entry.item} />
                      ) : (
                        <Muted>Empty</Muted>
                      )}
                    </div>
                    {entry.held && (
                      <Lock
                        aria-label='Held'
                        className='size-icon-sm shrink-0 text-muted-foreground'
                      />
                    )}
                  </li>
                )
              }}
            </Paged>
          </ul>
          <AdjustPanel
            acts={[action]}
            title='Arm and outfit'
            note='Put an item, a beast or a tamed kind in a slot, or empty it. A held slot keeps your choice until you release it.'
            hold={hold}
            onHold={setHold}
          >
            <div className='grid min-w-0 grid-cols-1 gap-3 @md/gear:grid-cols-2'>
              <MindPicker
                label='Slot'
                value={slot}
                table={table(SLOTS)}
                blocked={busy}
                onPick={(value) => setSlot(value as EquipmentSlot)}
              />
              <RecordField
                label='What to carry'
                types={SLOT_TYPES[slot] ?? null}
                value={item}
                onChange={setItem}
                blocked={busy}
              />
            </div>
            <div className='flex min-w-0 flex-wrap gap-2'>
              <Button
                act={action}
                size='sm'
                disabled={busy !== null || item === null}
                disabledReason={busy ?? 'Choose something to carry.'}
                onClick={() =>
                  send('/api/actions/mortal:equip', {
                    slot,
                    item_id: item,
                    hold,
                  })
                }
              >
                <Plus />
                Equip
              </Button>
              <Button
                act={action}
                size='sm'
                variant='outline'
                disabled={busy !== null}
                disabledReason={busy ?? undefined}
                onClick={() =>
                  send('/api/actions/mortal:equip', {
                    slot,
                    item_id: null,
                    hold,
                  })
                }
              >
                <X />
                Empty slot
              </Button>
              {profile.equipment.some(
                (entry) => entry.slot === slot && entry.held
              ) && (
                <Button
                  act={action}
                  size='sm'
                  variant='outline'
                  disabled={busy !== null}
                  disabledReason={busy ?? undefined}
                  onClick={() =>
                    send('/api/actions/mortal:equip_release', { slot })
                  }
                >
                  <Unlock />
                  Release slot
                </Button>
              )}
            </div>
          </AdjustPanel>
        </div>
      )}
    </Section>
  )
}

export function StressCard({ mortalId }: { mortalId: number }) {
  const { reason } = useGodGate()
  const profile = useMortalProfile(mortalId).data
  const action = useMortalAction(mortalId)
  if (!profile) return null
  const busy = reason() ?? (action.isPending ? WORKING : null)
  const held = profile.held.includes('stress')
  const breaking = profile.stress >= profile.stress_threshold
  const send = (path: string, body: Record<string, unknown>) =>
    void action.mutateAsync({ path, body: { mortal_id: mortalId, ...body } })
  return (
    <Panel
      title='Stress'
      icon={LIFE_FIELDS.stress.icon}
      tone={breaking ? 'danger' : 'warning'}
      hint={`Past ${profile.stress_threshold} this mind breaks: rage, flight, despair, zeal, vice or revelation`}
    >
      <StatBar
        label='Strain'
        value={profile.stress}
        max={PERCENT}
        icon={LIFE_FIELDS.stress.icon}
        tone={breaking ? 'destructive' : 'warning'}
      />
      {profile.last_break && (
        <Fact icon={named(BREAKS, profile.last_break).icon} label='Last broke'>
          <Tag spec={named(BREAKS, profile.last_break)} />
        </Fact>
      )}
      <div className='flex min-w-0 flex-wrap gap-2'>
        <Button
          act={action}
          size='sm'
          variant='outline'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() =>
            send('/api/actions/mortal:set', {
              field: 'stress',
              value: 0,
              hold: false,
            })
          }
        >
          Ease their mind
        </Button>
        {held ? (
          <Button
            act={action}
            size='sm'
            variant='outline'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() =>
              send('/api/actions/mortal:release', { field: 'stress' })
            }
          >
            <Unlock />
            Release stress
          </Button>
        ) : (
          <Button
            act={action}
            size='sm'
            variant='ghost'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() =>
              send('/api/actions/mortal:set', {
                field: 'stress',
                value: profile.stress,
                hold: true,
              })
            }
          >
            <Lock />
            Hold stress
          </Button>
        )}
      </div>
    </Panel>
  )
}
