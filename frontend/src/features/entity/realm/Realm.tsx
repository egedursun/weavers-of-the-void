import { useState } from 'react'
import {
  ChevronRight,
  Church,
  Coins,
  Crown,
  Flag,
  Flame,
  Gavel,
  HandCoins,
  Handshake,
  Landmark,
  Layers,
  ListOrdered,
  Lock,
  Map as MapIcon,
  Network,
  Save,
  Scale,
  ScrollText,
  Shield,
  Trash2,
  TriangleAlert,
  Unlock,
  UserMinus,
  UserPlus,
  Users,
  Castle,
  Pencil,
  Ban,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { formatInteger } from '@/lib/format'
import { plural } from '@/lib/units'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  ChangeChip,
  EmptyState,
  EntityLink,
  KpiTile,
  LoadingBlock,
  Medallion,
  Paged,
  PagedList,
  Portrait,
  RangeField,
  Section,
  ShowMore,
  StatBar,
  Timeline,
  TimelineItem,
  useShowMore,
} from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { RowAction } from '../actions/RowAction'
import { MindPicker } from '../mind/parts'
import { LawProtection, Statecraft } from './Statecraft'
import { useRealm, useRealmLink } from './api'
import {
  CLAIM_BASES,
  GOVERNMENTS,
  LAW_AREAS,
  LAW_KINDS,
  LEGITIMACY_BASES,
  MEMBER_TYPES,
  OFFICES,
  REALM_FIELDS,
  RULES,
  STANDINGS,
  TINCTURES,
  TREASURY_ENTRIES,
  TREATY_KINDS,
  TREATY_STATUSES,
  badBand,
  goodBand,
  labels,
  named,
  plain,
  sentence,
} from './labels'
import { useLawKinds } from './lawKinds'
import { ParamField } from './lawTerms'
import {
  AdjustPanel,
  ChoiceCard,
  ChoiceGrid,
  Fact,
  Hero,
  NumberField,
  Panel,
  RecordField,
  Tag,
} from './parts'

type Realm = components['schemas']['RealmView']
type Law = components['schemas']['LawView']
type LawKindSpec = components['schemas']['LawKindSpec']
type OfficeKind = components['schemas']['OfficeKind']
type LawKind = components['schemas']['LawKind']
type Treaty = Realm['treaties'][number]

const WORKING = 'Working…'
const PERCENT = 100
const SHOWN = 6
const LEDGER_SHOWN = 5
const UNJUST = 40
const AUTONOMOUS = 60
const LEGITIMACY_WORDS: [string, string, string, string] = [
  'Contested',
  'Shaky',
  'Firm',
  'Unquestioned',
]
const STABILITY_WORDS: [string, string, string, string] = [
  'Collapsing',
  'Restless',
  'Steady',
  'Unshakeable',
]
const WEARINESS_WORDS: [string, string, string, string] = [
  'Eager',
  'Tiring',
  'Weary',
  'Exhausted',
]
const ENFORCEMENT_WORDS: [string, string, string, string] = [
  'Ignored',
  'Loosely kept',
  'Enforced',
  'Iron law',
]
const AREAS = Object.keys(LAW_AREAS)
const STATUS_ORDER = ['in_force', 'fulfilled', 'expired', 'broken']

function clampPercent(value: number): number {
  return Math.max(0, Math.min(PERCENT, Math.round(value)))
}

function toneOf(value: number): 'success' | 'warning' | 'destructive' {
  if (value < UNJUST) return 'destructive'
  if (value < PERCENT * 0.7) return 'warning'
  return 'success'
}

function RealmCrest({ realm }: { realm: Realm }) {
  const government = named(GOVERNMENTS, realm.government)
  const rule = RULES[realm.decision_rule] ?? named({}, realm.decision_rule)
  const tincture = realm.emblem.field
    ? named(TINCTURES, realm.emblem.field)
    : null
  return (
    <Hero
      icon={government.icon}
      tone={government.tone}
      eyebrow={`${government.label} · ${rule.label}`}
      title={
        <EntityLink kind='entity' id={String(realm.id)}>
          {realm.name}
        </EntityLink>
      }
    >
      <Tag spec={named(STANDINGS, realm.standing)} />
      <Badge size='sm' variant='secondary'>
        <Layers aria-hidden='true' />
        {`Tier ${realm.tier}`}
      </Badge>
      {realm.tier_strain > 0 && (
        <Badge size='sm' variant='warning'>
          {`Strained by its size: ${realm.tier_strain}`}
        </Badge>
      )}
      <Tag spec={rule} text={RULES[realm.decision_rule]?.hint ?? rule.label} />
      {tincture && <Tag spec={tincture} text={`Arms of ${tincture.label}`} />}
      {realm.overlord && (
        <Tag
          spec={{ label: 'Vassal', icon: Lock, tone: 'warning' }}
          text={`Vassal of ${realm.overlord.name}`}
        />
      )}
      {realm.locked.length > 0 && (
        <Tag
          spec={{ label: 'Held', icon: Lock, tone: 'info' }}
          text={`${realm.locked.length} held by a god`}
        />
      )}
    </Hero>
  )
}

function RealmVitals({ realm }: { realm: Realm }) {
  const legitimacy = goodBand(realm.legitimacy, LEGITIMACY_WORDS)
  const stability = goodBand(realm.stability, STABILITY_WORDS)
  const weariness = badBand(realm.war_weariness, WEARINESS_WORDS)
  const meter = (value: number, label: string) => ({
    value: Math.min(PERCENT, value),
    max: PERCENT,
    label,
  })
  return (
    <div className='grid min-w-0 grid-cols-1 gap-3 @xs/realm:grid-cols-2 @xl/realm:grid-cols-3'>
      <KpiTile
        label='Legitimacy'
        value={realm.legitimacy}
        icon={Crown}
        tone={legitimacy.tone}
        meter={meter(realm.legitimacy, 'Legitimacy')}
        hint={`${legitimacy.label}: how rightful the ruler seems`}
      />
      <KpiTile
        label='Stability'
        value={realm.stability}
        icon={Scale}
        tone={stability.tone}
        meter={meter(realm.stability, 'Stability')}
        hint={`${stability.label}: how far from revolt`}
      />
      <KpiTile
        label='War weariness'
        value={realm.war_weariness}
        icon={Flame}
        tone={weariness.tone}
        meter={meter(realm.war_weariness, 'War weariness')}
        hint={`${weariness.label}: the people’s patience for war`}
      />
      <KpiTile
        label='Treasury'
        value={formatInteger(realm.treasury)}
        icon={Coins}
        tone='gold'
        hint={`War chest ${formatInteger(realm.war_chest)} · gold in the vaults`}
      />
      <KpiTile
        label='Debt'
        value={formatInteger(realm.debt)}
        icon={HandCoins}
        tone={
          realm.debt === 0
            ? 'success'
            : realm.debt > realm.treasury
              ? 'danger'
              : 'warning'
        }
        valueTone={realm.debt > realm.treasury ? 'destructive' : 'default'}
        hint={
          realm.debt === 0
            ? 'The realm owes nothing'
            : realm.debt > realm.treasury
              ? 'More than the vaults hold'
              : 'Owed to lenders'
        }
      />
      <KpiTile
        label='Overextension'
        value={`${realm.overextension}%`}
        icon={Network}
        tone={realm.overextension > PERCENT ? 'danger' : 'info'}
        meter={meter(realm.overextension, 'Overextension')}
        hint={`Administration ${realm.administration}; past 100% the provinces drift away`}
      />
    </div>
  )
}

function whyGroups(realm: Realm): [string, [string, number][]][] {
  const groups = new Map<string, [string, number][]>()
  for (const part of realm.why) {
    const split = part.label.indexOf(': ')
    const group = split > 0 ? part.label.slice(0, split) : 'legitimacy'
    const label = split > 0 ? part.label.slice(split + 2) : part.label
    groups.set(group, [...(groups.get(group) ?? []), [label, part.value]])
  }
  return [...groups.entries()]
}

function RealmSeat({ realm }: { realm: Realm }) {
  const groups = whyGroups(realm)
  return (
    <div className='grid min-w-0 grid-cols-1 gap-3 @xl/realm:grid-cols-2'>
      <Panel title='Seat of power' icon={Castle}>
        <div className='flex min-w-0 flex-col gap-2'>
          <Fact icon={Crown} label='Ruler'>
            {realm.ruler ? (
              <EntityLink kind='entity' id={String(realm.ruler.id)}>
                {realm.ruler.name}
              </EntityLink>
            ) : (
              <Muted>No one rules</Muted>
            )}
          </Fact>
          <Fact icon={Castle} label='Capital'>
            {realm.capital ? (
              <EntityLink kind='entity' id={String(realm.capital.id)}>
                {realm.capital.name}
              </EntityLink>
            ) : (
              <Muted>No capital</Muted>
            )}
          </Fact>
          <Fact icon={Users} label='Heartland'>
            {realm.core ? (
              <EntityLink kind='entity' id={String(realm.core.id)}>
                {realm.core.name}
              </EntityLink>
            ) : (
              <Muted>None</Muted>
            )}
          </Fact>
          <Fact icon={Church} label='State faith'>
            {realm.state_religion ? (
              <EntityLink kind='entity' id={String(realm.state_religion.id)}>
                {realm.state_religion.name}
              </EntityLink>
            ) : (
              <Muted>No state faith</Muted>
            )}
          </Fact>
          <Fact icon={Shield} label='Overlord'>
            {realm.overlord ? (
              <EntityLink kind='entity' id={String(realm.overlord.id)}>
                {realm.overlord.name}
              </EntityLink>
            ) : (
              <Muted>Sovereign</Muted>
            )}
          </Fact>
          <Fact icon={Flag} label='Vassals'>
            {realm.vassals.length === 0 ? (
              <Muted>None</Muted>
            ) : (
              <Paged items={realm.vassals}>
                {(item) => (
                  <EntityLink key={item.id} kind='entity' id={String(item.id)}>
                    {item.name}
                  </EntityLink>
                )}
              </Paged>
            )}
          </Fact>
        </div>
      </Panel>
      <Panel
        title='Why the rule holds'
        icon={Scale}
        hint='What raises and lowers legitimacy and stability'
      >
        <div
          data-surface='LegitimacyWhy'
          className='flex min-w-0 flex-col gap-3'
        >
          {groups.length === 0 && <Muted>Nothing weighs on it yet.</Muted>}
          <Paged items={groups}>
            {([group, parts]) => (
              <div key={group} className='flex min-w-0 flex-col gap-1.5'>
                <div className='flex min-w-0 items-center justify-between gap-2'>
                  <Label variant='overline'>{plain(REALM_FIELDS, group)}</Label>
                  <ChangeChip
                    value={parts.reduce((sum, [, value]) => sum + value, 0)}
                    label='Total'
                  />
                </div>
                <ul className='flex min-w-0 flex-col gap-1'>
                  <Paged items={parts} as='li' noun={['part', 'parts']}>
                    {([label, value]) => (
                      <li
                        key={label}
                        className='flex min-w-0 items-center gap-2'
                      >
                        <Text as='span' className='min-w-0 flex-1' truncate>
                          {sentence(label)}
                        </Text>
                        <ChangeChip value={value} />
                      </li>
                    )}
                  </Paged>
                </ul>
              </div>
            )}
          </Paged>
        </div>
      </Panel>
    </div>
  )
}

function OfficeCard({ item }: { item: Realm['offices'][number] }) {
  const spec = named(OFFICES, item.kind)
  const title = item.region ? `${spec.label} of ${item.region}` : spec.label
  return (
    <li
      className={
        item.holder_id
          ? 'flex min-w-0 items-center gap-2 rounded-md border surface-sheen border-gild/60 bg-card p-2'
          : 'flex min-w-0 items-center gap-2 rounded-md p-2 sealed-well'
      }
    >
      <Medallion
        icon={spec.icon}
        tone={item.holder_id ? (spec.tone ?? 'gold') : 'muted'}
        size='sm'
      />
      <div className='flex min-w-0 flex-1 flex-col'>
        <Label truncate>{title}</Label>
        {item.holder_id ? (
          <EntityLink kind='entity' id={String(item.holder_id)}>
            {item.holder ?? ''}
          </EntityLink>
        ) : (
          <Muted as='span' truncate>
            Vacant seat
          </Muted>
        )}
      </div>
      {item.holder_id && <Portrait name={item.holder ?? ''} size='xs' />}
    </li>
  )
}

function Court({ realm, blocked }: { realm: Realm; blocked: string | null }) {
  const [office, setOffice] = useState<string>('chancellor')
  const [mortal, setMortal] = useState<number | null>(null)
  const appoint = useGodAction({
    writes: [{ lever: 'polity:appoint' }],
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
    writes: [{ lever: 'polity:depose' }],
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
  const filled = below.filter((item) => item.holder_id).length
  const choices = Object.fromEntries(
    Object.entries(labels(OFFICES)).filter(([key]) => key !== 'ruler')
  )
  return (
    <Panel
      title='The court'
      icon={Crown}
      hint={`${filled} of ${plural(below.length, 'seat', 'seats')} filled`}
    >
      <div data-surface='OfficesChart' className='flex min-w-0 flex-col gap-3'>
        <div className='flex min-w-0 items-center gap-3 rounded-md border surface-framed border-primary/30 bg-primary/5 p-3'>
          <Portrait name={ruler?.holder ?? realm.name} size='md' />
          <div className='flex min-w-0 flex-1 flex-col gap-0.5'>
            <Label variant='overline'>Ruler</Label>
            {ruler?.holder_id ? (
              <EntityLink kind='entity' id={String(ruler.holder_id)}>
                {ruler.holder ?? ''}
              </EntityLink>
            ) : (
              <Muted>No one rules</Muted>
            )}
            {ruler && (
              <Muted variant='caption'>{`Ruling since epoch ${ruler.since_epoch}`}</Muted>
            )}
          </div>
          <Medallion icon={Crown} tone='gold' />
        </div>
        <ul className='grid min-w-0 grid-cols-1 gap-2 @xs/realm:grid-cols-2 @2xl/realm:grid-cols-3'>
          <Paged items={below} as='li'>
            {(item) => <OfficeCard key={item.id} item={item} />}
          </Paged>
        </ul>
        <AdjustPanel
          acts={[appoint, depose]}
          trigger='Adjust the court'
          title='Appoint and dismiss'
          note='Seat a mortal in any office, empty a seat, or cast the ruler down. Every change goes into the ledger.'
        >
          <div className='grid min-w-0 grid-cols-1 items-end gap-3 @md/realm:grid-cols-2'>
            <MindPicker
              label='Office'
              value={office}
              table={choices}
              blocked={busy}
              onPick={setOffice}
            />
            <RecordField
              label='Mortal'
              types={['mortal']}
              value={mortal}
              onChange={setMortal}
              blocked={busy}
              placeholder='Choose a mortal'
            />
          </div>
          <div className='flex min-w-0 flex-wrap items-center gap-2'>
            <Button
              act={appoint}
              size='sm'
              disabled={busy !== null || mortal === null}
              disabledReason={busy ?? 'Choose a mortal first'}
              onClick={() => appoint.mutate(mortal)}
            >
              <UserPlus />
              Appoint
            </Button>
            <Button
              act={appoint}
              size='sm'
              variant='outline'
              disabled={busy !== null}
              disabledReason={busy ?? undefined}
              onClick={() => appoint.mutate(null)}
            >
              <UserMinus />
              Empty the seat
            </Button>
            <Button
              act={depose}
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
        </AdjustPanel>
      </div>
    </Panel>
  )
}

function Succession({ realm }: { realm: Realm }) {
  return (
    <Panel
      title='Line of succession'
      icon={ListOrdered}
      hint='Who comes to rule if the ruler dies now'
    >
      <div
        data-surface='SuccessionPreview'
        className='flex min-w-0 flex-col gap-3'
      >
        {realm.succession.length === 0 ? (
          <div className='flex min-w-0 items-center gap-2 rounded-md border-warning/40 bg-warning/5 p-2 sealed-well'>
            <Medallion icon={TriangleAlert} tone='warning' size='sm' />
            <Muted>
              No heir stands in line; the succession would be disputed or a
              stranger would come to rule.
            </Muted>
          </div>
        ) : (
          <ol className='flex min-w-0 flex-wrap items-center gap-2'>
            <Paged items={realm.succession} as='li'>
              {(item, index) => (
                <li key={item.id} className='flex min-w-0 items-center gap-2'>
                  {index > 0 && (
                    <ChevronRight
                      aria-hidden='true'
                      className='size-icon-sm shrink-0 text-muted-foreground'
                    />
                  )}
                  <div
                    className={
                      index === 0
                        ? 'flex min-w-0 items-center gap-2 rounded-md border surface-sheen border-primary/30 bg-primary/5 p-2'
                        : 'flex min-w-0 items-center gap-2 rounded-md border surface-sheen border-gild/60 bg-card p-2'
                    }
                  >
                    <Badge
                      size='sm'
                      variant={index === 0 ? 'default' : 'outline'}
                    >
                      {index === 0 ? 'Heir' : `#${index + 1}`}
                    </Badge>
                    <Portrait name={item.name} size='xs' />
                    <EntityLink kind='entity' id={String(item.id)}>
                      {item.name}
                    </EntityLink>
                  </div>
                </li>
              )}
            </Paged>
          </ol>
        )}
        {realm.claims.length > 0 && (
          <div className='flex min-w-0 flex-col gap-2'>
            <Label variant='overline'>Claims to rule</Label>
            <ul className='grid min-w-0 grid-cols-1 gap-2 @xl/realm:grid-cols-2'>
              <Paged items={realm.claims} as='li'>
                {(claim) => (
                  <li
                    key={claim.id}
                    className='flex min-w-0 flex-col gap-2 rounded-md border surface-sheen border-gild/60 bg-card p-2'
                  >
                    <div className='flex min-w-0 flex-wrap items-center gap-2'>
                      <EntityLink kind='entity' id={String(claim.claimant_id)}>
                        {claim.claimant}
                      </EntityLink>
                      <Tag spec={named(CLAIM_BASES, claim.basis)} />
                      {claim.pressed && (
                        <Tag
                          spec={{
                            label: 'Pressed',
                            icon: Gavel,
                            tone: 'danger',
                          }}
                        />
                      )}
                    </div>
                    <StatBar
                      label={`Strength, held since epoch ${claim.since_epoch}`}
                      value={claim.strength}
                      max={PERCENT}
                      tone={claim.pressed ? 'destructive' : 'default'}
                    />
                    <div className='flex min-w-0 flex-wrap items-center gap-2'>
                      <RowAction
                        path='/api/actions/claim:edit'
                        icon={Pencil}
                        label='Edit claim'
                        fixed={{ claim_id: claim.id }}
                        defaults={{
                          strength: claim.strength,
                          basis: claim.basis,
                          pressed: claim.pressed,
                          office: claim.office,
                          backer_id: claim.backer_id,
                        }}
                        labels={{ backer_id: 'Backer' }}
                        pickers={{ backer_id: { source: 'entity' } }}
                        held={claim.locked}
                      />
                      <RowAction
                        path='/api/actions/claim:revoke'
                        icon={Ban}
                        label='Void claim'
                        fixed={{ claim_id: claim.id }}
                        destructive
                        confirm={`${claim.claimant}'s claim to rule will be voided.`}
                      />
                    </div>
                  </li>
                )}
              </Paged>
            </ul>
          </div>
        )}
      </div>
    </Panel>
  )
}

function Dominion({ realm }: { realm: Realm }) {
  const lands = useShowMore(realm.territory, SHOWN)
  const members = useShowMore(realm.members, SHOWN)
  return (
    <div className='grid min-w-0 grid-cols-1 gap-3 @xl/realm:grid-cols-2'>
      <Panel
        title='Lands held'
        icon={MapIcon}
        tone='success'
        count={realm.territory.length}
        hint='How firmly each land obeys'
      >
        <div
          data-surface='RealmTerritory'
          className='flex min-w-0 flex-col gap-2'
        >
          {realm.territory.length === 0 && (
            <Muted>The realm holds no land.</Muted>
          )}
          {lands.visible.map((item) => (
            <div
              key={item.region_id}
              className='flex min-w-0 items-center gap-2'
            >
              <div className='min-w-0 flex-1'>
                <StatBar
                  label={
                    item.province
                      ? `${item.name} · ${item.province}`
                      : item.name
                  }
                  value={item.control}
                  max={PERCENT}
                  icon={MapIcon}
                  tone={toneOf(item.control)}
                />
              </div>
              {item.locked.length > 0 && (
                <Lock
                  aria-label='Held by you'
                  className='size-icon-sm shrink-0 text-muted-foreground'
                />
              )}
              <RowAction
                path='/api/actions/polity:territory'
                icon={Pencil}
                label={`Edit ${item.name}`}
                iconOnly
                fixed={{ polity_id: realm.id, region_id: item.region_id }}
                defaults={{
                  control: item.control,
                  province: item.province ?? '',
                }}
                held={item.locked}
              />
            </div>
          ))}
          <ShowMore state={lands} noun={['land', 'lands']} />
        </div>
      </Panel>
      <Panel
        title='Members'
        icon={Users}
        tone='info'
        count={realm.members.length}
        hint='Peoples and towns under the crown'
      >
        <ul className='flex min-w-0 flex-col gap-2'>
          {realm.members.length === 0 && <Muted>No one answers to it.</Muted>}
          {members.visible.map((member) => {
            const spec = named(MEMBER_TYPES, member.entity_type)
            return (
              <li key={member.id} className='flex min-w-0 items-center gap-2'>
                <Medallion icon={spec.icon} tone={spec.tone} size='sm' />
                <div className='flex min-w-0 flex-1 flex-col'>
                  <EntityLink kind='entity' id={String(member.id)}>
                    {member.name}
                  </EntityLink>
                  <Muted variant='caption' truncate>
                    {`${spec.label} · ${plural(member.population, 'soul', 'souls')}`}
                  </Muted>
                </div>
                <Badge
                  size='sm'
                  variant={
                    member.autonomy > AUTONOMOUS
                      ? 'warning'
                      : member.autonomy > 0
                        ? 'secondary'
                        : 'success'
                  }
                >
                  {member.autonomy > 0
                    ? `Autonomy ${member.autonomy}`
                    : 'Loyal'}
                </Badge>
                <RowAction
                  path='/api/actions/polity:member'
                  icon={Pencil}
                  label={`Edit ${member.name}`}
                  iconOnly
                  fixed={{ polity_id: realm.id, member_id: member.id }}
                  defaults={{ autonomy: member.autonomy }}
                  held={member.locked}
                />
              </li>
            )
          })}
        </ul>
        <ShowMore state={members} noun={['member', 'members']} />
      </Panel>
    </div>
  )
}

function TreatyRow({ item }: { item: Treaty }) {
  const kind = named(TREATY_KINDS, item.kind)
  return (
    <li className='flex min-w-0 items-center gap-2 rounded-md border surface-sheen border-gild/60 bg-card p-2'>
      <Medallion icon={kind.icon} tone={kind.tone} size='sm' />
      <div className='flex min-w-0 flex-1 flex-col'>
        <EntityLink kind='entity' id={String(item.id)}>
          {item.name}
        </EntityLink>
        <Muted variant='caption' truncate>
          {item.until_epoch === null
            ? `${kind.label} · without end`
            : `${kind.label} · until epoch ${item.until_epoch}`}
        </Muted>
      </div>
      <Tag spec={named(TREATY_STATUSES, item.status)} />
    </li>
  )
}

function Treaties({ realm }: { realm: Realm }) {
  const [kind, setKind] = useState<string | null>(null)
  const kinds = Object.keys(TREATY_KINDS).filter((key) =>
    realm.treaties.some((item) => item.kind === key)
  )
  const shown = realm.treaties
    .filter((item) => kind === null || item.kind === kind)
    .sort(
      (left, right) =>
        STATUS_ORDER.indexOf(left.status) - STATUS_ORDER.indexOf(right.status)
    )
  const list = useShowMore(shown, SHOWN)
  const live = realm.treaties.filter((item) => item.status === 'in_force')
  if (realm.treaties.length === 0) return null
  return (
    <Panel
      title='Treaties and pacts'
      icon={Handshake}
      tone='info'
      count={realm.treaties.length}
      hint={`${live.length} in force · pick a kind to see only those`}
    >
      <div className='grid min-w-0 grid-cols-1 gap-2 @xs/realm:grid-cols-2 @2xl/realm:grid-cols-3'>
        {kinds.map((key) => {
          const all = realm.treaties.filter((item) => item.kind === key)
          const binding = all.filter((item) => item.status === 'in_force')
          return (
            <ChoiceCard
              key={key}
              spec={{ ...TREATY_KINDS[key], label: TREATY_KINDS[key].plural }}
              hint={`${binding.length} in force`}
              count={all.length}
              selected={kind === key}
              onSelect={() => setKind(kind === key ? null : key)}
            />
          )
        })}
      </div>
      <ul className='flex min-w-0 flex-col gap-2'>
        {list.visible.map((item) => (
          <TreatyRow key={item.id} item={item} />
        ))}
      </ul>
      <ShowMore
        key={kind ?? 'all'}
        state={list}
        noun={['treaty', 'treaties']}
      />
    </Panel>
  )
}

function TreasuryLedger({ realm }: { realm: Realm }) {
  const lines = [...realm.treasury_ledger].reverse()
  const list = useShowMore(lines, LEDGER_SHOWN)
  const income = lines
    .filter((line) => line.amount > 0)
    .reduce((sum, line) => sum + line.amount, 0)
  const spent = lines
    .filter((line) => line.amount < 0)
    .reduce((sum, line) => sum + line.amount, 0)
  return (
    <Panel
      title='Treasury ledger'
      icon={Coins}
      count={lines.length}
      hint='Every coin the crown gathered and spent'
      actions={
        lines.length > 0 && (
          <>
            <ChangeChip value={income} label='In' />
            <ChangeChip value={spent} label='Out' />
          </>
        )
      }
    >
      <div data-surface='RealmTreasury' className='flex min-w-0 flex-col gap-2'>
        {lines.length === 0 ? (
          <Muted>No coin has moved yet.</Muted>
        ) : (
          <Timeline label='Treasury ledger'>
            {list.visible.map((line, index) => {
              const entry = named(TREASURY_ENTRIES, line.entry)
              const note = line.note
                ? line.amount < 0
                  ? `Spent on ${line.note}`
                  : sentence(line.note)
                : null
              return (
                <TimelineItem
                  key={`${line.epoch}-${index}`}
                  icon={entry.icon}
                  framed
                  title={entry.label}
                  timestamp={`Epoch ${line.epoch}`}
                  tone={
                    line.amount > 0
                      ? 'success'
                      : line.amount < 0
                        ? 'destructive'
                        : 'default'
                  }
                  last={index === list.visible.length - 1}
                >
                  <div className='flex min-w-0 flex-wrap items-center gap-2'>
                    <ChangeChip value={line.amount} icon={Coins} />
                    {note && (
                      <Muted as='span' variant='caption' truncate>
                        {note}
                      </Muted>
                    )}
                    <Muted
                      as='span'
                      variant='caption'
                      className='ms-auto'
                    >{`Balance ${formatInteger(line.balance)}`}</Muted>
                  </div>
                </TimelineItem>
              )
            })}
          </Timeline>
        )}
        <ShowMore state={list} noun={['entry', 'entries']} />
      </div>
    </Panel>
  )
}

function LawCard({
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
  const [enforcement, setEnforcement] = useState(law.enforcement)
  const save = useGodAction({
    writes: [{ lever: 'law:edit' }],
    run: () =>
      unwrap(
        api.POST('/api/actions/law:edit', {
          body: {
            law_id: law.id,
            params,
            enforcement: clampPercent(enforcement),
          },
        })
      ),
  })
  const repeal = useGodAction({
    writes: [{ lever: 'law:repeal' }],
    run: () =>
      unwrap(api.POST('/api/actions/law:repeal', { body: { law_id: law.id } })),
  })
  const busy = blocked ?? (save.isPending || repeal.isPending ? WORKING : null)
  const area = named(LAW_AREAS, law.area)
  return (
    <li className='flex min-w-0 flex-col gap-3 rounded-md border surface-framed border-gild/70 bg-card p-3'>
      <div className='flex min-w-0 items-start gap-2'>
        <Medallion icon={area.icon} tone={area.tone} size='sm' />
        <div className='flex min-w-0 flex-1 flex-col gap-1'>
          <EntityLink kind='entity' id={String(law.id)}>
            {law.name}
          </EntityLink>
          <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
            <Badge size='sm' variant='secondary'>
              <ScrollText aria-hidden='true' />
              {plain(LAW_KINDS, law.kind)}
            </Badge>
            <Tag spec={named(LEGITIMACY_BASES, law.legitimacy_basis)} />
            <Badge size='sm' variant='outline'>
              {`Since epoch ${law.enacted_epoch}`}
            </Badge>
            {law.conflict > 0 && (
              <Tag
                spec={{
                  label: 'Conflict',
                  icon: TriangleAlert,
                  tone: 'warning',
                }}
                text={`Legal conflict ${law.conflict}`}
              />
            )}
          </div>
        </div>
      </div>
      <Text>{law.effect}</Text>
      <div className='grid min-w-0 grid-cols-1 gap-3 @md/realm:grid-cols-2'>
        <StatBar
          label='Enforcement'
          value={law.enforcement}
          max={PERCENT}
          icon={Gavel}
          tone={toneOf(law.enforcement)}
        />
        <StatBar
          label='Justice'
          value={law.justice}
          max={PERCENT}
          icon={Scale}
          tone={toneOf(law.justice)}
        />
      </div>
      <AdjustPanel
        acts={[save, repeal]}
        trigger='Amend'
        title='Amend this law'
        note='Rewrite its terms or how hard it is enforced, or strike it from the code.'
      >
        {spec && spec.params.length > 0 && (
          <div className='grid min-w-0 grid-cols-1 items-end gap-3 @md/realm:grid-cols-2 @2xl/realm:grid-cols-3'>
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
        <RangeField
          label='Enforcement'
          icon={Gavel}
          value={enforcement}
          min={0}
          max={PERCENT}
          level={goodBand(enforcement, ENFORCEMENT_WORDS).label}
          lowLabel='Ignored'
          highLabel='Iron law'
          onChange={setEnforcement}
        />
        <LawProtection law={law} blocked={busy} />
        <div className='flex min-w-0 flex-wrap items-center gap-2'>
          <Button
            act={save}
            size='sm'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => save.mutate(undefined)}
          >
            <Save />
            Rewrite the law
          </Button>
          <Button
            act={repeal}
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
      </AdjustPanel>
    </li>
  )
}

function LawCode({ realm, blocked }: { realm: Realm; blocked: string | null }) {
  const kinds = useLawKinds()
  const [kind, setKind] = useState<string>('quarantine')
  const enact = useGodAction({
    writes: [{ lever: 'law:enact' }],
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
  const choices = Object.fromEntries(
    [...(kinds.data ?? [])]
      .sort(
        (left, right) => AREAS.indexOf(left.area) - AREAS.indexOf(right.area)
      )
      .map((item) => [
        item.kind,
        `${plain(LAW_KINDS, item.kind)} · ${named(LAW_AREAS, item.area).label}`,
      ])
  )
  return (
    <div data-surface='LawCode' className='flex min-w-0 flex-col gap-4'>
      {realm.laws.length === 0 && (
        <EmptyState
          icon={ScrollText}
          size='compact'
          title='No written law'
          description='The realm lives by custom alone.'
        />
      )}
      {AREAS.map((area) => {
        const laws = realm.laws.filter((law) => law.area === area)
        if (laws.length === 0) return null
        const spec = named(LAW_AREAS, area)
        return (
          <div key={area} className='flex min-w-0 flex-col gap-2'>
            <div className='flex min-w-0 items-center gap-2'>
              <spec.icon
                aria-hidden='true'
                className='size-icon-sm shrink-0 text-muted-foreground'
              />
              <Label variant='overline'>{spec.label}</Label>
              <Badge size='sm' variant='secondary'>
                {laws.length}
              </Badge>
            </div>
            <ul className='flex min-w-0 flex-col gap-2'>
              <Paged items={laws} as='li'>
                {(law) => (
                  <LawCard
                    key={`${law.id}-${JSON.stringify(law.params)}-${law.enforcement}`}
                    law={law}
                    spec={specs[law.kind]}
                    blocked={blocked}
                  />
                )}
              </Paged>
            </ul>
          </div>
        )
      })}
      <AdjustPanel
        acts={[enact]}
        trigger='Lay down a law'
        title='Lay down a new law'
        note='The law starts with its usual terms; amend it afterwards to change them.'
      >
        <div className='flex min-w-0 flex-wrap items-end gap-3'>
          <div className='min-w-48 flex-1'>
            <MindPicker
              label='Law'
              value={kind}
              table={choices}
              blocked={busy}
              onPick={setKind}
            />
          </div>
          <Button
            act={enact}
            size='sm'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => enact.mutate(undefined)}
          >
            <Gavel />
            Enact it
          </Button>
        </div>
      </AdjustPanel>
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
    legitimacy: realm.legitimacy,
    stability: realm.stability,
    war_weariness: realm.war_weariness,
    treasury: String(realm.treasury),
    debt: String(realm.debt),
  })
  const save = useGodAction({
    writes: [{ lever: 'polity:edit' }],
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
                    legitimacy: clampPercent(values.legitimacy),
                    stability: clampPercent(values.stability),
                    treasury: Number(values.treasury) || 0,
                    debt: Number(values.debt) || 0,
                    war_weariness: clampPercent(values.war_weariness),
                  },
            release,
          },
        })
      ),
  })
  const free = useGodAction({
    writes: [{ lever: 'polity:independence' }],
    run: () =>
      unwrap(
        api.POST('/api/actions/polity:independence', {
          body: { polity_id: realm.id },
        })
      ),
  })
  const busy = blocked ?? (save.isPending || free.isPending ? WORKING : null)
  const set = (key: keyof typeof values, value: string | number) =>
    setValues((current) => ({ ...current, [key]: value }))
  return (
    <AdjustPanel
      acts={[save, free]}
      trigger='Adjust the realm'
      title='Shape the realm'
      note='Set its government and its fortunes. What you set is held against the world until you let the realm change again. Every change goes into the ledger.'
    >
      <ChoiceGrid
        label='Government'
        table={GOVERNMENTS}
        value={values.government}
        blocked={busy}
        onPick={(value) => set('government', value)}
      />
      <ChoiceGrid
        label='Who decides'
        table={RULES}
        hints={Object.fromEntries(
          Object.entries(RULES).map(([key, rule]) => [key, rule.hint])
        )}
        value={values.decision_rule}
        blocked={busy}
        onPick={(value) => set('decision_rule', value)}
      />
      <div className='grid min-w-0 grid-cols-1 gap-3 @xl/realm:grid-cols-2'>
        <RangeField
          label='Legitimacy'
          icon={Crown}
          value={values.legitimacy}
          min={0}
          max={PERCENT}
          level={goodBand(values.legitimacy, LEGITIMACY_WORDS).label}
          lowLabel='Contested'
          highLabel='Unquestioned'
          onChange={(value) => set('legitimacy', value)}
        />
        <RangeField
          label='Stability'
          icon={Scale}
          value={values.stability}
          min={0}
          max={PERCENT}
          level={goodBand(values.stability, STABILITY_WORDS).label}
          lowLabel='Collapsing'
          highLabel='Unshakeable'
          onChange={(value) => set('stability', value)}
        />
        <RangeField
          label='War weariness'
          icon={Flame}
          value={values.war_weariness}
          min={0}
          max={PERCENT}
          level={badBand(values.war_weariness, WEARINESS_WORDS).label}
          lowLabel='Eager'
          highLabel='Exhausted'
          onChange={(value) => set('war_weariness', value)}
        />
        <div className='flex min-w-0 flex-col gap-2 rounded-md border surface-framed border-gild/70 bg-card p-3'>
          <div className='flex min-w-0 items-center gap-2.5'>
            <Medallion icon={Coins} tone='gold' size='sm' />
            <div className='flex min-w-0 flex-col'>
              <Text as='span' weight='medium'>
                Coffers
              </Text>
              <Muted as='span' variant='caption' truncate>
                Gold in the vaults and what is owed
              </Muted>
            </div>
          </div>
          <div className='grid min-w-0 grid-cols-2 gap-2'>
            <NumberField
              label='Treasury'
              icon={Coins}
              tone='text-primary'
              min={0}
              value={values.treasury}
              blocked={busy}
              onChange={(value) => set('treasury', value)}
            />
            <NumberField
              label='Debt'
              icon={HandCoins}
              tone='text-destructive'
              min={0}
              value={values.debt}
              blocked={busy}
              onChange={(value) => set('debt', value)}
            />
          </div>
        </div>
      </div>
      {realm.locked.length > 0 && (
        <PagedList
          items={realm.locked}
          initial={12}
          noun={['entry', 'entries']}
          as='div'
          className='flex min-w-0 flex-wrap items-center gap-1.5'
          itemKey={(key) => key}
        >
          {(key) => (
            <Tag
              key={key}
              spec={{ label: key, icon: Lock, tone: 'info' }}
              text={`Holding ${plain(REALM_FIELDS, key).toLowerCase()}`}
            />
          )}
        </PagedList>
      )}
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Button
          act={save}
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => save.mutate([])}
        >
          <Lock />
          Set and hold these values
        </Button>
        {realm.locked.length > 0 && (
          <Button
            act={save}
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
            act={free}
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
      </div>
    </AdjustPanel>
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
    <div
      data-surface='RealmView'
      className='@container/realm flex min-w-0 flex-col gap-4'
    >
      <RealmCrest realm={realm} />
      <RealmVitals realm={realm} />
      <RealmForm
        key={JSON.stringify([
          realm.locked,
          realm.government,
          realm.decision_rule,
          realm.legitimacy,
          realm.stability,
          realm.war_weariness,
          realm.treasury,
          realm.debt,
        ])}
        realm={realm}
        blocked={blocked}
      />
      <RealmSeat realm={realm} />
      <Court realm={realm} blocked={blocked} />
      <Succession realm={realm} />
      <Dominion realm={realm} />
      <Treaties realm={realm} />
      <TreasuryLedger realm={realm} />
      <Statecraft realm={realm} blocked={blocked} />
      <Section
        id='section-law-code'
        level={3}
        title='Law code'
        description='Every law in force, by area, with what it does.'
        icon={ScrollText}
      >
        <LawCode realm={realm} blocked={blocked} />
      </Section>
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
      {view.isPending && <LoadingBlock label='Reading the realm' />}
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
