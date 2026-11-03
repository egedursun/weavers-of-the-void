import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  Crown,
  Gavel,
  Landmark,
  Network,
  Save,
  ScrollText,
  Trash2,
  TriangleAlert,
  UserMinus,
  UserPlus,
  Unlock,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { formatInteger } from '@/lib/format'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Switch } from '@/components/ui/switch'
import {
  EmptyState,
  EntityLink,
  KpiTile,
  Section,
  StatBar,
} from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { MindPicker } from '../mind/parts'
import { useRealm, useRealmLink } from './api'

type Realm = components['schemas']['RealmView']
type Law = components['schemas']['LawView']
type LawKindSpec = components['schemas']['LawKindSpec']
type OfficeKind = components['schemas']['OfficeKind']
type LawKind = components['schemas']['LawKind']

const WORKING = 'Working…'
const PERCENT = 100
const GOVERNMENTS = [
  'chiefdom',
  'monarchy',
  'theocracy',
  'oligarchy',
  'republic',
  'tribal_confederation',
  'empire',
  'hive_council',
  'god_kingdom',
  'occupation',
] as const
const RULES = ['autocratic', 'council', 'assembly', 'divine'] as const
const OFFICES: OfficeKind[] = [
  'chancellor',
  'marshal',
  'treasurer',
  'high_judge',
  'spymaster',
  'governor',
  'ambassador',
  'regent',
  'heir_designate',
]
const AREAS = [
  'succession',
  'property',
  'fiscal',
  'penal',
  'military',
  'social',
  'public_health',
  'magic',
] as const

function words(value: string): string {
  return value.replaceAll('_', ' ')
}

function table(values: readonly string[]): Record<string, string> {
  return Object.fromEntries(values.map((value) => [value, words(value)]))
}

function useLawKinds() {
  return useQuery({
    queryKey: ['laws', 'kinds'],
    staleTime: Number.POSITIVE_INFINITY,
    queryFn: () => unwrap(api.GET('/api/laws/kinds')),
  })
}

function ParamField({
  spec,
  value,
  onChange,
  blocked,
}: {
  spec: components['schemas']['LawParamSpec']
  value: string | number | boolean
  onChange: (value: string | number | boolean) => void
  blocked: string | null
}) {
  if (spec.kind === 'bool')
    return (
      <label className='flex items-center gap-2'>
        <Switch
          checked={Boolean(value)}
          disabled={blocked !== null}
          onCheckedChange={onChange}
          aria-label={words(spec.key)}
        />
        <Text as='span'>{words(spec.key)}</Text>
      </label>
    )
  if (spec.kind === 'choice')
    return (
      <MindPicker
        label={words(spec.key)}
        value={String(value)}
        table={table(spec.choices)}
        blocked={blocked}
        onPick={onChange}
      />
    )
  return (
    <div className='flex min-w-0 flex-col gap-1'>
      <Label>{words(spec.key)}</Label>
      <Input
        type='number'
        min={spec.low}
        max={spec.high}
        value={String(value)}
        aria-label={words(spec.key)}
        onChange={(event) =>
          onChange(Math.round(Number(event.target.value) || 0))
        }
      />
    </div>
  )
}

function LawRow({
  law,
  spec,
  blocked,
}: {
  law: Law
  spec: LawKindSpec | undefined
  blocked: string | null
}) {
  const [params, setParams] = useState<
    Record<string, string | number | boolean>
  >({ ...law.params })
  const [enforcement, setEnforcement] = useState(String(law.enforcement))
  const save = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/law:edit', {
          body: {
            law_id: law.id,
            params,
            enforcement: Math.max(
              0,
              Math.min(PERCENT, Number(enforcement) || 0)
            ),
          },
        })
      ),
  })
  const repeal = useGodAction({
    run: () =>
      unwrap(api.POST('/api/actions/law:repeal', { body: { law_id: law.id } })),
  })
  const busy = blocked ?? (save.isPending || repeal.isPending ? WORKING : null)
  return (
    <li className='flex min-w-0 flex-col gap-2 rounded-lg border bg-muted/30 p-3'>
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <EntityLink kind='entity' id={String(law.id)}>
          {law.name}
        </EntityLink>
        <Badge variant='outline'>{words(law.kind)}</Badge>
        <Badge variant='outline'>{words(law.legitimacy_basis)}</Badge>
        {law.conflict > 0 && (
          <Badge variant='warning'>{`Legal conflict ${law.conflict}`}</Badge>
        )}
      </div>
      <Muted>{law.effect}</Muted>
      <div className='grid min-w-0 grid-cols-1 gap-3 md:grid-cols-2'>
        <StatBar label='Enforcement' value={law.enforcement} max={PERCENT} />
        <StatBar
          label='Justice'
          value={law.justice}
          max={PERCENT}
          tone={law.justice < 40 ? 'destructive' : 'success'}
        />
      </div>
      {spec && spec.params.length > 0 && (
        <div className='grid min-w-0 grid-cols-1 gap-3 md:grid-cols-3'>
          {spec.params.map((param) => (
            <ParamField
              key={param.key}
              spec={param}
              value={params[param.key] ?? param.default}
              blocked={busy}
              onChange={(value) =>
                setParams((current) => ({ ...current, [param.key]: value }))
              }
            />
          ))}
        </div>
      )}
      <div className='flex min-w-0 flex-wrap items-end gap-2'>
        <div className='flex w-28 flex-col gap-1'>
          <Label>Enforcement</Label>
          <Input
            type='number'
            min={0}
            max={PERCENT}
            value={enforcement}
            aria-label='Enforcement'
            onChange={(event) => setEnforcement(event.target.value)}
          />
        </div>
        <Button
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => save.mutate(undefined)}
        >
          <Save />
          Rewrite the law
        </Button>
        <Button
          size='sm'
          variant='outline'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => repeal.mutate(undefined)}
        >
          <Trash2 />
          Repeal it
        </Button>
      </div>
    </li>
  )
}

function LawCode({ realm, blocked }: { realm: Realm; blocked: string | null }) {
  const kinds = useLawKinds()
  const [kind, setKind] = useState<string>('quarantine')
  const enact = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/law:enact', {
          body: { holder_id: realm.id, kind: kind as LawKind, params: {} },
        })
      ),
  })
  const specs = Object.fromEntries(
    (kinds.data ?? []).map((item) => [item.kind, item])
  )
  const busy = blocked ?? (enact.isPending ? WORKING : null)
  return (
    <div data-surface='LawCode' className='flex min-w-0 flex-col gap-4'>
      {AREAS.map((area) => {
        const laws = realm.laws.filter((law) => law.area === area)
        if (laws.length === 0) return null
        return (
          <div key={area} className='flex min-w-0 flex-col gap-2'>
            <Label variant='overline'>{words(area)}</Label>
            <ul className='flex min-w-0 flex-col gap-2'>
              {laws.map((law) => (
                <LawRow
                  key={`${law.id}-${JSON.stringify(law.params)}`}
                  law={law}
                  spec={specs[law.kind]}
                  blocked={blocked}
                />
              ))}
            </ul>
          </div>
        )
      })}
      <div className='flex min-w-0 flex-wrap items-end gap-3'>
        <div className='min-w-48 flex-1'>
          <MindPicker
            label='Lay down a new law'
            value={kind}
            table={table(Object.keys(specs))}
            blocked={busy}
            onPick={setKind}
          />
        </div>
        <Button
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => enact.mutate(undefined)}
        >
          <Gavel />
          Enact it
        </Button>
      </div>
    </div>
  )
}

function OrgChart({
  realm,
  blocked,
}: {
  realm: Realm
  blocked: string | null
}) {
  const [office, setOffice] = useState<string>('chancellor')
  const [mortal, setMortal] = useState('')
  const appoint = useGodAction({
    run: (holder: number | null) =>
      unwrap(
        api.POST('/api/actions/polity:appoint', {
          body: {
            polity_id: realm.id,
            office: office as OfficeKind,
            mortal_id: holder,
          },
        })
      ),
  })
  const depose = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/polity:depose', {
          body: { polity_id: realm.id },
        })
      ),
  })
  const busy =
    blocked ?? (appoint.isPending || depose.isPending ? WORKING : null)
  const ruler = realm.offices.find((item) => item.kind === 'ruler')
  const below = realm.offices.filter((item) => item.kind !== 'ruler')
  return (
    <div data-surface='OfficesChart' className='flex min-w-0 flex-col gap-3'>
      <div className='flex min-w-0 justify-center'>
        <div className='flex min-w-48 flex-col items-center gap-1 rounded-lg border bg-muted/30 p-3'>
          <Crown
            aria-hidden='true'
            className='size-icon-sm text-muted-foreground'
          />
          <Label variant='overline'>Ruler</Label>
          {ruler?.holder_id ? (
            <EntityLink kind='entity' id={String(ruler.holder_id)}>
              {ruler.holder ?? ''}
            </EntityLink>
          ) : (
            <Muted>The throne is empty</Muted>
          )}
        </div>
      </div>
      <ul className='grid min-w-0 grid-cols-2 gap-2 md:grid-cols-4'>
        {below.map((item) => (
          <li
            key={item.id}
            className='flex min-w-0 flex-col gap-1 rounded-lg border bg-background p-2'
          >
            <Label variant='overline'>{`${words(item.kind)}${item.region ? ` of ${item.region}` : ''}`}</Label>
            {item.holder_id ? (
              <EntityLink kind='entity' id={String(item.holder_id)}>
                {item.holder ?? ''}
              </EntityLink>
            ) : (
              <Muted variant='caption'>Vacant</Muted>
            )}
          </li>
        ))}
      </ul>
      <div className='flex min-w-0 flex-wrap items-end gap-3'>
        <div className='min-w-40'>
          <MindPicker
            label='Office'
            value={office}
            table={table(OFFICES)}
            blocked={busy}
            onPick={setOffice}
          />
        </div>
        <div className='flex w-36 flex-col gap-1'>
          <Label>Mortal id</Label>
          <Input
            type='number'
            min={1}
            value={mortal}
            aria-label='Mortal id'
            onChange={(event) => setMortal(event.target.value)}
          />
        </div>
        <Button
          size='sm'
          disabled={busy !== null || mortal === ''}
          disabledReason={busy ?? 'Name a mortal first'}
          onClick={() => appoint.mutate(Number(mortal))}
        >
          <UserPlus />
          Appoint
        </Button>
        <Button
          size='sm'
          variant='outline'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => appoint.mutate(null)}
        >
          <UserMinus />
          Dismiss
        </Button>
        <Button
          size='sm'
          variant='destructive'
          disabled={busy !== null || !ruler?.holder_id}
          disabledReason={busy ?? 'There is no ruler'}
          onClick={() => depose.mutate(undefined)}
        >
          <Crown />
          Depose the ruler
        </Button>
      </div>
    </div>
  )
}

function RealmForm({
  realm,
  blocked,
}: {
  realm: Realm
  blocked: string | null
}) {
  const [values, setValues] = useState({
    government: realm.government,
    decision_rule: realm.decision_rule,
    legitimacy: String(realm.legitimacy),
    stability: String(realm.stability),
    treasury: String(realm.treasury),
    debt: String(realm.debt),
    war_weariness: String(realm.war_weariness),
  })
  const save = useGodAction({
    run: (release: string[]) =>
      unwrap(
        api.POST('/api/actions/polity:edit', {
          body: {
            polity_id: realm.id,
            values:
              release.length > 0
                ? {}
                : {
                    government: values.government,
                    decision_rule: values.decision_rule,
                    legitimacy: Number(values.legitimacy) || 0,
                    stability: Number(values.stability) || 0,
                    treasury: Number(values.treasury) || 0,
                    debt: Number(values.debt) || 0,
                    war_weariness: Number(values.war_weariness) || 0,
                  },
            release,
          },
        })
      ),
  })
  const free = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/polity:independence', {
          body: { polity_id: realm.id },
        })
      ),
  })
  const busy = blocked ?? (save.isPending || free.isPending ? WORKING : null)
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      <div className='grid min-w-0 grid-cols-1 gap-3 md:grid-cols-2'>
        <MindPicker
          label='Government'
          value={values.government}
          table={table(GOVERNMENTS)}
          blocked={busy}
          onPick={(value) =>
            setValues((current) => ({
              ...current,
              government: value as Realm['government'],
            }))
          }
        />
        <MindPicker
          label='Who decides'
          value={values.decision_rule}
          table={table(RULES)}
          blocked={busy}
          onPick={(value) =>
            setValues((current) => ({
              ...current,
              decision_rule: value as Realm['decision_rule'],
            }))
          }
        />
      </div>
      <div className='grid min-w-0 grid-cols-2 gap-3 md:grid-cols-5'>
        {(
          [
            'legitimacy',
            'stability',
            'treasury',
            'debt',
            'war_weariness',
          ] as const
        ).map((key) => (
          <div key={key} className='flex min-w-0 flex-col gap-1'>
            <Label>{words(key)}</Label>
            <Input
              type='number'
              min={0}
              value={values[key]}
              aria-label={words(key)}
              onChange={(event) =>
                setValues((current) => ({
                  ...current,
                  [key]: event.target.value,
                }))
              }
            />
          </div>
        ))}
      </div>
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Button
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => save.mutate([])}
        >
          <Save />
          Hold these values
        </Button>
        {realm.locked.length > 0 && (
          <Button
            size='sm'
            variant='outline'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => save.mutate(realm.locked)}
          >
            <Unlock />
            Let the realm change again
          </Button>
        )}
        {realm.overlord && (
          <Button
            size='sm'
            variant='outline'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => free.mutate(undefined)}
          >
            <Unlock />
            Free it from its overlord
          </Button>
        )}
        {realm.locked.map((key) => (
          <Badge key={key} variant='outline'>{`held: ${words(key)}`}</Badge>
        ))}
      </div>
    </div>
  )
}

function RealmBody({
  realm,
  readOnlyReason,
}: {
  realm: Realm
  readOnlyReason?: string | null
}) {
  const { reason } = useGodGate()
  const blocked = readOnlyReason ?? reason()
  return (
    <div data-surface='RealmView' className='flex min-w-0 flex-col gap-5'>
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <EntityLink kind='entity' id={String(realm.id)}>
          {realm.name}
        </EntityLink>
        <Badge variant='info'>{words(realm.government)}</Badge>
        <Badge variant='outline'>{words(realm.standing)}</Badge>
        <Badge variant='outline'>{`Tier ${realm.tier}`}</Badge>
        {realm.overlord && (
          <Badge variant='warning'>{`Vassal of ${realm.overlord.name}`}</Badge>
        )}
        {realm.vassals.map((item) => (
          <Badge
            key={item.id}
            variant='outline'
          >{`Overlord of ${item.name}`}</Badge>
        ))}
      </div>
      <div className='grid min-w-0 grid-cols-2 gap-3 md:grid-cols-4'>
        <KpiTile
          label='Legitimacy'
          value={String(realm.legitimacy)}
          icon={Crown}
          tone={realm.legitimacy < 40 ? 'danger' : 'success'}
        />
        <KpiTile
          label='Stability'
          value={String(realm.stability)}
          icon={Landmark}
          tone={realm.stability < 40 ? 'danger' : 'muted'}
        />
        <KpiTile
          label='Treasury'
          value={formatInteger(realm.treasury)}
          icon={Landmark}
          hint={realm.debt ? `Owes ${formatInteger(realm.debt)}` : undefined}
        />
        <KpiTile
          label='Overextension'
          value={`${realm.overextension}%`}
          icon={Network}
          tone={realm.overextension > PERCENT ? 'warning' : 'muted'}
          hint={`Administration ${realm.administration}`}
        />
      </div>
      {realm.why.length > 0 && (
        <div
          data-surface='LegitimacyWhy'
          className='flex min-w-0 flex-col gap-1'
        >
          <Label variant='overline'>Why</Label>
          <ul className='grid min-w-0 grid-cols-1 gap-1 md:grid-cols-2'>
            {realm.why.map((part) => (
              <li key={part.label} className='flex min-w-0 items-center gap-2'>
                <Text className='min-w-0 flex-1' truncate>
                  {part.label}
                </Text>
                <Text
                  className={
                    part.value < 0 ? 'text-destructive' : 'text-success'
                  }
                >
                  {part.value > 0 ? `+${part.value}` : String(part.value)}
                </Text>
              </li>
            ))}
          </ul>
        </div>
      )}
      <OrgChart realm={realm} blocked={blocked} />
      <div
        data-surface='SuccessionPreview'
        className='flex min-w-0 flex-col gap-1'
      >
        <Label variant='overline'>If the ruler died now</Label>
        {realm.succession.length === 0 ? (
          <Muted>
            No heir stands in line; the succession would be disputed or a
            stranger would take the throne.
          </Muted>
        ) : (
          <ol className='flex min-w-0 flex-wrap gap-2'>
            {realm.succession.map((item, index) => (
              <li key={item.id} className='flex items-center gap-1'>
                <Badge variant={index === 0 ? 'info' : 'outline'}>
                  {String(index + 1)}
                </Badge>
                <EntityLink kind='entity' id={String(item.id)}>
                  {item.name}
                </EntityLink>
              </li>
            ))}
          </ol>
        )}
      </div>
      {realm.claims.length > 0 && (
        <div className='flex min-w-0 flex-col gap-1'>
          <Label variant='overline'>Claims on the throne</Label>
          {realm.claims.map((claim) => (
            <Text key={claim.id}>
              <EntityLink kind='entity' id={String(claim.claimant_id)}>
                {claim.claimant}
              </EntityLink>
              {` · ${words(claim.basis)} · strength ${claim.strength}${claim.pressed ? ' · pressed' : ''}`}
            </Text>
          ))}
        </div>
      )}
      <div
        data-surface='RealmTerritory'
        className='grid min-w-0 grid-cols-1 gap-2 md:grid-cols-2'
      >
        {realm.territory.map((item) => (
          <StatBar
            key={item.region_id}
            label={item.name}
            value={item.control}
            max={PERCENT}
          />
        ))}
      </div>
      <div className='flex min-w-0 flex-wrap gap-2'>
        {realm.members.map((member) => (
          <Badge
            key={member.id}
            variant={member.autonomy > 60 ? 'warning' : 'outline'}
          >
            <EntityLink kind='entity' id={String(member.id)}>
              {member.name}
            </EntityLink>
            {member.autonomy > 0 ? ` · autonomy ${member.autonomy}` : ''}
          </Badge>
        ))}
      </div>
      <Section
        id='section-law-code'
        level={3}
        title='Law code'
        description='Every law in force, by area, with what it does.'
        icon={ScrollText}
      >
        <LawCode realm={realm} blocked={blocked} />
      </Section>
      {realm.treaties.length > 0 && (
        <div className='flex min-w-0 flex-wrap gap-2'>
          {realm.treaties.map((item) => (
            <Badge
              key={item.id}
              variant={item.status === 'in_force' ? 'info' : 'outline'}
            >
              <EntityLink kind='entity' id={String(item.id)}>
                {item.name}
              </EntityLink>
            </Badge>
          ))}
        </div>
      )}
      {realm.treasury_ledger.length > 0 && (
        <ul
          data-surface='RealmTreasury'
          className='flex min-w-0 flex-col gap-1'
        >
          {realm.treasury_ledger.map((line, index) => (
            <li
              key={`${line.epoch}-${index}`}
              className='flex min-w-0 items-center gap-3'
            >
              <Muted
                variant='caption'
                className='w-16 shrink-0'
              >{`Epoch ${line.epoch}`}</Muted>
              <Text
                className='min-w-0 flex-1'
                truncate
              >{`${words(line.entry)}${line.note ? `: ${line.note}` : ''}`}</Text>
              <Text
                className={
                  line.amount < 0
                    ? 'w-24 shrink-0 text-right text-destructive'
                    : 'w-24 shrink-0 text-right text-success'
                }
              >
                {formatInteger(line.amount)}
              </Text>
            </li>
          ))}
        </ul>
      )}
      <RealmForm
        key={JSON.stringify([realm.locked, realm.government, realm.legitimacy])}
        realm={realm}
        blocked={blocked}
      />
    </div>
  )
}

export function RealmSection({
  entityId,
  readOnlyReason,
}: {
  entityId: number
  readOnlyReason?: string | null
}) {
  const link = useRealmLink(entityId)
  const polity = link.data?.polity_id ?? null
  const view = useRealm(polity)
  if (link.isPending) return null
  if (polity === null) return null
  return (
    <Section
      id='section-realm'
      title='Realm'
      description='The realm, its rulers, laws, lands and fortunes.'
      icon={Landmark}
    >
      {view.isPending && <Muted>Reading the realm…</Muted>}
      {view.isError && (
        <EmptyState
          icon={TriangleAlert}
          title='The realm could not be read'
          description={view.error.message}
        />
      )}
      {view.data && (
        <RealmBody realm={view.data} readOnlyReason={readOnlyReason} />
      )}
    </Section>
  )
}
