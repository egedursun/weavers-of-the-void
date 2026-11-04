import { useState } from 'react'
import {
  ArrowRight,
  CalendarClock,
  Coins,
  Crown,
  Gem,
  GitBranch,
  Handshake,
  Heart,
  HeartCrack,
  Hourglass,
  PenLine,
  Quote,
  RefreshCw,
  ScrollText,
  Shield,
  Skull,
  Sparkles,
  Sprout,
  Swords,
  TriangleAlert,
  Trophy,
  User,
  Users,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { formatInteger } from '@/lib/format'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  EmptyState,
  EntityLink,
  KpiTile,
  Medallion,
  Portrait,
  RangeField,
  Section,
  StatBar,
  Timeline,
  TimelineItem,
} from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { HouseEditor, TreatyBuilder } from './Covenants'
import { useHouse, useOaths, useTreaty } from './api'
import {
  CLAIM_BASES,
  CLAUSES,
  OATHS,
  OATH_STATUSES,
  OFFICES,
  PARTY_ROLES,
  SEXES,
  TINCTURES,
  TREATY_KINDS,
  TREATY_STATUSES,
  named,
  plain,
  sentence,
} from './labels'
import {
  AdjustPanel,
  ChoiceGrid,
  Fact,
  Hero,
  NumberField,
  Panel,
  RecordField,
  Tag,
} from './parts'

type Member = components['schemas']['HouseMemberView']
type OathKind = components['schemas']['OathKind']
type Oath = components['schemas']['OathView']
type TreatyStatus = components['schemas']['TreatyStatus']

const WORKING = 'Working…'
const PERCENT = 100
const CLAIM_STRENGTH = 50
const STRENGTH_WORDS: [string, string, string, string] = [
  'Faint',
  'Arguable',
  'Strong',
  'Undeniable',
]

function strengthWord(value: number): string {
  return STRENGTH_WORDS[[25, 50, 75].filter((edge) => value >= edge).length]
}

function generations(members: Member[]): Member[][] {
  const ids = new Set(members.map((member) => member.id))
  const depth = new Map<number, number>()
  const depthOf = (member: Member, seen: Set<number>): number => {
    if (depth.has(member.id)) return depth.get(member.id) ?? 0
    const parents = member.parents.filter(
      (parent) => ids.has(parent) && !seen.has(parent)
    )
    const value =
      parents.length === 0
        ? 0
        : 1 +
          Math.max(
            ...parents.map((parent) => {
              const found = members.find((item) => item.id === parent)
              return found ? depthOf(found, new Set([...seen, member.id])) : 0
            })
          )
    depth.set(member.id, value)
    return value
  }
  members.forEach((member) => depthOf(member, new Set()))
  const rows: Member[][] = []
  for (const member of members) {
    const level = depth.get(member.id) ?? 0
    rows[level] = [...(rows[level] ?? []), member]
  }
  return rows.filter(Boolean)
}

function MemberCard({ member }: { member: Member }) {
  const facts = [
    member.sex ? plain(SEXES, member.sex) : null,
    member.age !== null ? `age ${member.age}` : null,
  ].filter(Boolean)
  return (
    <li
      className={
        member.alive
          ? 'flex min-w-0 flex-col gap-2 rounded-lg border bg-background p-2'
          : 'flex min-w-0 flex-col gap-2 rounded-lg border border-dashed bg-muted/20 p-2'
      }
    >
      <div className='flex min-w-0 items-center gap-2'>
        <Portrait name={member.name} size='sm' />
        <div className='flex min-w-0 flex-1 flex-col'>
          <div className='flex min-w-0 items-center gap-1'>
            {!member.alive && (
              <Skull
                aria-label='Dead'
                className='size-icon-xs shrink-0 text-muted-foreground'
              />
            )}
            <EntityLink kind='entity' id={String(member.id)}>
              {member.name}
            </EntityLink>
          </div>
          <Muted variant='caption' truncate>
            {facts.length > 0 ? facts.join(' · ') : 'Age unknown'}
          </Muted>
        </div>
      </div>
      {(member.office || member.by_marriage || member.lasting_injuries > 0) && (
        <div className='flex min-w-0 flex-wrap gap-1'>
          {member.office && <Tag spec={named(OFFICES, member.office)} />}
          {member.by_marriage && (
            <Tag
              spec={{ label: 'By marriage', icon: Heart, tone: 'verdigris' }}
            />
          )}
          {member.lasting_injuries > 0 && (
            <Tag
              spec={{ label: 'Wounds', icon: TriangleAlert, tone: 'warning' }}
              text={`${member.lasting_injuries} lasting wounds`}
            />
          )}
        </div>
      )}
      {!member.alive && member.fate && (
        <Muted variant='caption' truncate={2}>
          {member.fate}
        </Muted>
      )}
    </li>
  )
}

function FamilyTree({ members }: { members: Member[] }) {
  const rows = generations(members)
  return (
    <Panel
      title='Family tree'
      icon={GitBranch}
      tone='verdigris'
      count={members.length}
      hint={`${rows.length} ${rows.length === 1 ? 'generation' : 'generations'} of blood and marriage`}
    >
      <div data-surface='FamilyTree' className='flex min-w-0 flex-col gap-3'>
        {members.length === 0 && <Muted>The house has no members left.</Muted>}
        {rows.map((row, index) => (
          <div key={index} className='flex min-w-0 flex-col gap-1.5'>
            <div className='flex min-w-0 items-center gap-2'>
              <Sprout
                aria-hidden='true'
                className='size-icon-sm shrink-0 text-muted-foreground'
              />
              <Label variant='overline'>{`Generation ${index + 1}`}</Label>
            </div>
            <ul className='grid min-w-0 grid-cols-1 gap-2 @xs/realm:grid-cols-2 @2xl/realm:grid-cols-3'>
              {row.map((member) => (
                <MemberCard key={member.id} member={member} />
              ))}
            </ul>
          </div>
        ))}
      </div>
    </Panel>
  )
}

export function HouseSection({
  houseId,
  readOnlyReason,
}: {
  houseId: number
  readOnlyReason?: string | null
}) {
  const view = useHouse(houseId)
  const { reason } = useGodGate()
  const blocked = readOnlyReason ?? reason()
  const [claimant, setClaimant] = useState<number | null>(null)
  const [polity, setPolity] = useState<number | null>(null)
  const [strength, setStrength] = useState(CLAIM_STRENGTH)
  const grant = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/claim:grant', {
          body: {
            mortal_id: claimant ?? 0,
            polity_id: polity ?? 0,
            strength,
            basis: 'divine',
            office: 'ruler',
          },
        })
      ),
  })
  const extinguish = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/house:extinguish', {
          body: { house_id: houseId },
        })
      ),
  })
  const busy =
    blocked ?? (grant.isPending || extinguish.isPending ? WORKING : null)
  const house = view.data
  const tincture = house?.emblem.field
    ? named(TINCTURES, house.emblem.field)
    : null
  const living = house?.members.filter((member) => member.alive).length ?? 0
  return (
    <Section
      id='section-house'
      title='The house'
      description='Its blood, its heads, its claims and its treasures.'
      icon={Shield}
    >
      {view.isPending && <Muted>Reading the line…</Muted>}
      {view.isError && (
        <EmptyState
          icon={TriangleAlert}
          title='The house could not be read'
          description={view.error.message}
        />
      )}
      {house && (
        <div
          data-surface='HouseView'
          className='@container/realm flex min-w-0 flex-col gap-4'
        >
          <Hero
            icon={Shield}
            tone={tincture?.tone ?? 'gold'}
            eyebrow={house.parent ? 'Cadet branch' : 'Noble house'}
            title={house.name}
          >
            {tincture && (
              <Tag spec={tincture} text={`Arms of ${tincture.label}`} />
            )}
            {house.motto && (
              <Badge size='sm' variant='outline'>
                <Quote aria-hidden='true' />
                {house.motto}
              </Badge>
            )}
            {house.divine_son_id !== null && (
              <Tag
                spec={{
                  label: 'Divine blood',
                  icon: Sparkles,
                  tone: 'verdigris',
                }}
              />
            )}
            {house.traits.map((trait) => (
              <Tag
                key={trait}
                spec={{
                  label: sentence(trait),
                  icon: Sparkles,
                  tone: 'warning',
                }}
              />
            ))}
          </Hero>
          <HouseEditor
            key={JSON.stringify([house.locked, house.prestige, house.traits])}
            house={house}
            blocked={blocked}
          />
          <div className='grid min-w-0 grid-cols-1 gap-3 @xs/realm:grid-cols-2 @xl/realm:grid-cols-4'>
            <KpiTile
              label='Prestige'
              value={formatInteger(house.prestige)}
              icon={Trophy}
              tone='gold'
              hint='From offices, renown and victories'
            />
            <KpiTile
              label='Wealth'
              value={formatInteger(house.wealth)}
              icon={Coins}
              tone='gold'
              hint='The family’s own gold'
            />
            <KpiTile
              label='Living'
              value={living}
              icon={Users}
              tone={living === 0 ? 'danger' : 'success'}
              hint={`${house.members.length - living} in the grave`}
            />
            <KpiTile
              label='Claims'
              value={house.claims.length}
              icon={ScrollText}
              tone='info'
              hint={`${house.heirlooms.length} heirlooms kept`}
            />
          </div>
          <Panel title='Lineage' icon={Crown}>
            <div className='flex min-w-0 flex-col gap-2'>
              <Fact icon={Sprout} label='Founder'>
                {house.founder ? (
                  <EntityLink kind='entity' id={String(house.founder.id)}>
                    {house.founder.name}
                  </EntityLink>
                ) : (
                  <Muted>Unknown</Muted>
                )}
              </Fact>
              <Fact icon={Crown} label='Head'>
                {house.head ? (
                  <EntityLink kind='entity' id={String(house.head.id)}>
                    {house.head.name}
                  </EntityLink>
                ) : (
                  <Muted>No living head</Muted>
                )}
              </Fact>
              <Fact icon={GitBranch} label='Branch of'>
                {house.parent ? (
                  <EntityLink kind='entity' id={String(house.parent.id)}>
                    {house.parent.name}
                  </EntityLink>
                ) : (
                  <Muted>A house of its own</Muted>
                )}
              </Fact>
              <Fact icon={Shield} label='Realm'>
                {house.polity ? (
                  <EntityLink kind='entity' id={String(house.polity.id)}>
                    {house.polity.name}
                  </EntityLink>
                ) : (
                  <Muted>Serves no realm</Muted>
                )}
              </Fact>
              <Fact icon={GitBranch} label='Branches'>
                {house.branches.length === 0 ? (
                  <Muted>None</Muted>
                ) : (
                  house.branches.map((item) => (
                    <EntityLink
                      key={item.id}
                      kind='entity'
                      id={String(item.id)}
                    >
                      {item.name}
                    </EntityLink>
                  ))
                )}
              </Fact>
            </div>
          </Panel>
          <FamilyTree members={house.members} />
          {(house.claims.length > 0 || house.heirlooms.length > 0) && (
            <div className='grid min-w-0 grid-cols-1 gap-3 @xl/realm:grid-cols-2'>
              <Panel
                title='Claims'
                icon={ScrollText}
                tone='info'
                count={house.claims.length}
              >
                {house.claims.length === 0 && (
                  <Muted>The house presses no claim.</Muted>
                )}
                <ul className='flex min-w-0 flex-col gap-2'>
                  {house.claims.map((claim) => (
                    <li
                      key={claim.id}
                      className='flex min-w-0 flex-col gap-2 rounded-lg border bg-background p-2'
                    >
                      <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
                        <EntityLink
                          kind='entity'
                          id={String(claim.claimant_id)}
                        >
                          {claim.claimant}
                        </EntityLink>
                        <ArrowRight
                          aria-hidden='true'
                          className='size-icon-xs text-muted-foreground'
                        />
                        <EntityLink kind='entity' id={String(claim.polity_id)}>
                          the realm
                        </EntityLink>
                        <Tag spec={named(CLAIM_BASES, claim.basis)} />
                        {claim.pressed && (
                          <Tag
                            spec={{
                              label: 'Pressed',
                              icon: Swords,
                              tone: 'danger',
                            }}
                          />
                        )}
                      </div>
                      <StatBar
                        label={`Strength: ${strengthWord(claim.strength)}`}
                        value={claim.strength}
                        max={PERCENT}
                        tone={claim.pressed ? 'destructive' : 'default'}
                      />
                    </li>
                  ))}
                </ul>
              </Panel>
              <Panel
                title='Heirlooms'
                icon={Gem}
                tone='verdigris'
                count={house.heirlooms.length}
              >
                {house.heirlooms.length === 0 && (
                  <Muted>No treasure is handed down.</Muted>
                )}
                <ul className='flex min-w-0 flex-col gap-2'>
                  {house.heirlooms.map((item) => (
                    <li
                      key={item.id}
                      className='flex min-w-0 items-center gap-2'
                    >
                      <Medallion icon={Gem} tone='verdigris' size='sm' />
                      <div className='flex min-w-0 flex-1 flex-col'>
                        <EntityLink kind='entity' id={String(item.id)}>
                          {item.name}
                        </EntityLink>
                        <Muted variant='caption'>{`Kept since epoch ${item.since_epoch}`}</Muted>
                      </div>
                    </li>
                  ))}
                </ul>
              </Panel>
            </div>
          )}
          <AdjustPanel
            trigger='Adjust the house'
            title='Shape the line'
            note='Grant a mortal a god-given claim on a realm, or end the house for good. Every change goes into the ledger.'
          >
            <div className='grid min-w-0 grid-cols-1 gap-3 @md/realm:grid-cols-2'>
              <RecordField
                label='Claimant'
                types={['mortal']}
                value={claimant}
                onChange={setClaimant}
                blocked={busy}
                placeholder='Choose a mortal'
              />
              <RecordField
                label='Realm claimed'
                types={['polity']}
                value={polity}
                onChange={setPolity}
                blocked={busy}
                placeholder='Choose a realm'
              />
            </div>
            <RangeField
              label='Strength of the claim'
              icon={ScrollText}
              value={strength}
              min={0}
              max={PERCENT}
              level={strengthWord(strength)}
              lowLabel='Faint'
              highLabel='Undeniable'
              onChange={setStrength}
            />
            <div className='flex min-w-0 flex-wrap items-center gap-2'>
              <Button
                size='sm'
                disabled={busy !== null || claimant === null || polity === null}
                disabledReason={busy ?? 'Choose the claimant and the realm'}
                onClick={() => grant.mutate(undefined)}
              >
                <ScrollText />
                Grant a divine claim
              </Button>
              <Button
                size='sm'
                variant='destructive'
                disabled={busy !== null}
                disabledReason={busy ?? undefined}
                onClick={() => extinguish.mutate(undefined)}
              >
                <Skull />
                Extinguish the house
              </Button>
            </div>
          </AdjustPanel>
        </div>
      )}
    </Section>
  )
}

export function TreatySection({
  treatyId,
  readOnlyReason,
}: {
  treatyId: number
  readOnlyReason?: string | null
}) {
  const view = useTreaty(treatyId)
  const { reason } = useGodGate()
  const blocked = readOnlyReason ?? reason()
  const [until, setUntil] = useState('')
  const [status, setStatus] = useState<string>('in_force')
  const edit = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/treaty:edit', {
          body: {
            treaty_id: treatyId,
            until_epoch: until === '' ? null : Number(until),
            status: status as TreatyStatus,
          },
        })
      ),
  })
  const breakIt = useGodAction({
    run: (breaker: number) =>
      unwrap(
        api.POST('/api/actions/treaty:break', {
          body: { treaty_id: treatyId, breaker_id: breaker },
        })
      ),
  })
  const busy = blocked ?? (edit.isPending || breakIt.isPending ? WORKING : null)
  const treaty = view.data
  const kind = treaty ? named(TREATY_KINDS, treaty.kind) : null
  return (
    <Section
      id='section-treaty'
      title='Terms'
      description='Who is bound, by what, until when, and every breach.'
      icon={Handshake}
    >
      {view.isPending && <Muted>Reading the treaty…</Muted>}
      {view.isError && (
        <EmptyState
          icon={TriangleAlert}
          title='The treaty could not be read'
          description={view.error.message}
        />
      )}
      {treaty && kind && (
        <div
          data-surface='TreatyView'
          className='@container/realm flex min-w-0 flex-col gap-4'
        >
          <Hero
            icon={kind.icon}
            tone={kind.tone}
            eyebrow={kind.label}
            title={treaty.name}
          >
            <Tag spec={named(TREATY_STATUSES, treaty.status)} />
            {treaty.witness_son_id !== null && (
              <Tag
                spec={{
                  label: 'Sworn before a god',
                  icon: Sparkles,
                  tone: 'verdigris',
                }}
              />
            )}
            {treaty.renewals > 0 && (
              <Tag
                spec={{ label: 'Renewed', icon: RefreshCw, tone: 'info' }}
                text={`Renewed ${treaty.renewals} times`}
              />
            )}
          </Hero>
          <TreatyBuilder treaty={treaty} blocked={blocked} />
          <div className='grid min-w-0 grid-cols-1 gap-3 @xs/realm:grid-cols-3'>
            <KpiTile
              label='Signed'
              value={`Epoch ${treaty.signed_epoch}`}
              icon={PenLine}
              tone='gold'
            />
            <KpiTile
              label={treaty.ended_epoch !== null ? 'Ended' : 'Holds until'}
              value={
                treaty.ended_epoch !== null
                  ? `Epoch ${treaty.ended_epoch}`
                  : treaty.until_epoch !== null
                    ? `Epoch ${treaty.until_epoch}`
                    : 'Forever'
              }
              icon={Hourglass}
              tone='info'
            />
            <KpiTile
              label='Breaches'
              value={treaty.breaches.length}
              icon={HeartCrack}
              tone={treaty.breaches.length > 0 ? 'danger' : 'success'}
            />
          </div>
          <Panel
            title='Parties'
            icon={Users}
            count={treaty.parties.length}
            hint='Who is bound by it'
          >
            <ul className='grid min-w-0 grid-cols-1 gap-2 @xl/realm:grid-cols-2'>
              {treaty.parties.map((party) => (
                <li
                  key={party.id}
                  className='flex min-w-0 items-center gap-2 rounded-lg border bg-background p-2'
                >
                  <Portrait name={party.name} size='sm' />
                  <div className='flex min-w-0 flex-1 flex-col gap-1'>
                    <EntityLink kind='entity' id={String(party.id)}>
                      {party.name}
                    </EntityLink>
                    <div className='flex min-w-0'>
                      <Tag spec={named(PARTY_ROLES, party.role)} />
                    </div>
                  </div>
                  {treaty.status === 'in_force' && (
                    <Button
                      size='sm'
                      variant='ghost'
                      disabled={busy !== null}
                      disabledReason={busy ?? undefined}
                      onClick={() => breakIt.mutate(party.id)}
                    >
                      <HeartCrack />
                      Break it
                    </Button>
                  )}
                </li>
              ))}
            </ul>
          </Panel>
          <Panel
            title='Clauses'
            icon={ScrollText}
            count={treaty.clauses.length}
            hint='What each side owes the other'
          >
            {treaty.clauses.length === 0 && (
              <Muted>It binds no one to anything.</Muted>
            )}
            <ul className='flex min-w-0 flex-col gap-2'>
              {treaty.clauses.map((clause) => {
                const spec = named(CLAUSES, clause.kind)
                const terms = Object.entries(clause.params)
                return (
                  <li
                    key={clause.id}
                    className='flex min-w-0 items-center gap-2 rounded-lg border bg-background p-2'
                  >
                    <Medallion icon={spec.icon} tone={spec.tone} size='sm' />
                    <div className='flex min-w-0 flex-1 flex-col gap-0.5'>
                      <Text as='span' weight='medium' truncate>
                        {spec.label}
                      </Text>
                      {(clause.obligor || clause.beneficiary) && (
                        <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
                          {clause.obligor_id !== null && (
                            <EntityLink
                              kind='entity'
                              id={String(clause.obligor_id)}
                            >
                              {clause.obligor ?? ''}
                            </EntityLink>
                          )}
                          {clause.beneficiary_id !== null && (
                            <>
                              <ArrowRight
                                aria-label='owes'
                                className='size-icon-xs text-muted-foreground'
                              />
                              <EntityLink
                                kind='entity'
                                id={String(clause.beneficiary_id)}
                              >
                                {clause.beneficiary ?? ''}
                              </EntityLink>
                            </>
                          )}
                        </div>
                      )}
                      {terms.length > 0 && (
                        <Muted variant='caption' truncate>
                          {terms
                            .map(
                              ([key, value]) =>
                                `${sentence(key)}: ${typeof value === 'boolean' ? (value ? 'yes' : 'no') : String(value)}`
                            )
                            .join(' · ')}
                        </Muted>
                      )}
                    </div>
                    <Badge
                      size='sm'
                      variant={
                        clause.last_kept_epoch !== null ? 'success' : 'outline'
                      }
                    >
                      <CalendarClock aria-hidden='true' />
                      {clause.last_kept_epoch !== null
                        ? `Kept in epoch ${clause.last_kept_epoch}`
                        : 'Not yet called'}
                    </Badge>
                  </li>
                )
              })}
            </ul>
          </Panel>
          {treaty.breaches.length > 0 && (
            <Panel
              title='Breaches'
              icon={HeartCrack}
              tone='danger'
              count={treaty.breaches.length}
            >
              <Timeline label='Breaches'>
                {treaty.breaches.map((item, index) => (
                  <TimelineItem
                    key={index}
                    icon={HeartCrack}
                    tone='destructive'
                    framed
                    title={
                      item.breaker_id !== null ? (
                        <EntityLink kind='entity' id={String(item.breaker_id)}>
                          {item.breaker ?? 'Someone'}
                        </EntityLink>
                      ) : (
                        'Someone broke it'
                      )
                    }
                    timestamp={`Epoch ${item.epoch}`}
                    last={index === treaty.breaches.length - 1}
                  >
                    {item.note && <Muted>{sentence(item.note)}</Muted>}
                  </TimelineItem>
                ))}
              </Timeline>
            </Panel>
          )}
          <AdjustPanel
            trigger='Adjust the terms'
            title='Set the terms'
            note='Change how long it holds and where it stands. Every change goes into the ledger.'
          >
            <ChoiceGrid
              label='Standing'
              table={TREATY_STATUSES}
              value={status}
              blocked={busy}
              onPick={setStatus}
            />
            <div className='flex min-w-0 flex-wrap items-end gap-3'>
              <div className='min-w-48 flex-1'>
                <NumberField
                  label='Holds until epoch'
                  icon={Hourglass}
                  min={0}
                  value={until}
                  placeholder='Forever'
                  blocked={busy}
                  onChange={setUntil}
                />
              </div>
              <Button
                size='sm'
                disabled={busy !== null}
                disabledReason={busy ?? undefined}
                onClick={() => edit.mutate(undefined)}
              >
                <Swords />
                Set the terms
              </Button>
            </div>
          </AdjustPanel>
        </div>
      )}
    </Section>
  )
}

function OathCard({
  oath,
  blocked,
  onBreak,
}: {
  oath: Oath
  blocked: string | null
  onBreak: () => void
}) {
  const kind = named(OATHS, oath.kind)
  return (
    <li className='flex min-w-0 flex-col gap-2 rounded-lg border bg-background p-3'>
      <div className='flex min-w-0 items-center gap-2'>
        <Medallion icon={kind.icon} tone={kind.tone} size='sm' />
        <div className='flex min-w-0 flex-1 flex-col'>
          <Text as='span' weight='semibold' truncate>
            {`Oath of ${kind.label.toLowerCase()}`}
          </Text>
          <Muted variant='caption' truncate>
            {`Sworn in epoch ${oath.sworn_epoch}${oath.deadline_epoch !== null ? ` · due by epoch ${oath.deadline_epoch}` : ''}${oath.ended_epoch !== null ? ` · ended in epoch ${oath.ended_epoch}` : ''}`}
          </Muted>
        </div>
        <Tag spec={named(OATH_STATUSES, oath.status)} />
      </div>
      <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
        <User
          aria-hidden='true'
          className='size-icon-xs shrink-0 text-muted-foreground'
        />
        <EntityLink kind='entity' id={String(oath.swearer_id)}>
          {oath.swearer}
        </EntityLink>
        {oath.recipient_id !== null && (
          <>
            <ArrowRight
              aria-label='sworn to'
              className='size-icon-xs text-muted-foreground'
            />
            <EntityLink kind='entity' id={String(oath.recipient_id)}>
              {oath.recipient ?? ''}
            </EntityLink>
          </>
        )}
      </div>
      {oath.note && <Muted>{sentence(oath.note)}</Muted>}
      {(oath.witness_son_id !== null || oath.status === 'sworn') && (
        <div className='flex min-w-0 flex-wrap items-center justify-between gap-2'>
          {oath.witness_son_id !== null ? (
            <Tag
              spec={{
                label: 'Witnessed by a god',
                icon: Sparkles,
                tone: 'verdigris',
              }}
            />
          ) : (
            <span />
          )}
          {oath.status === 'sworn' && (
            <Button
              size='sm'
              variant='ghost'
              disabled={blocked !== null}
              disabledReason={blocked ?? undefined}
              onClick={onBreak}
            >
              <HeartCrack />
              Break it
            </Button>
          )}
        </div>
      )}
    </li>
  )
}

export function OathsSection({
  entityId,
  readOnlyReason,
}: {
  entityId: number
  readOnlyReason?: string | null
}) {
  const view = useOaths(entityId)
  const { reason } = useGodGate()
  const blocked = readOnlyReason ?? reason()
  const [kind, setKind] = useState<string>('fealty')
  const [recipient, setRecipient] = useState<number | null>(null)
  const swear = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/oath:swear', {
          body: {
            swearer_id: entityId,
            kind: kind as OathKind,
            recipient_id: recipient,
          },
        })
      ),
  })
  const breakIt = useGodAction({
    run: (oathId: number) =>
      unwrap(
        api.POST('/api/actions/oath:break', { body: { oath_id: oathId } })
      ),
  })
  const busy =
    blocked ?? (swear.isPending || breakIt.isPending ? WORKING : null)
  if (!view.data) return null
  const groups: [string, Oath[]][] = [
    ['Sworn by them', view.data.sworn],
    ['Sworn to them', view.data.received],
  ]
  const total = view.data.sworn.length + view.data.received.length
  return (
    <Section
      id='section-oaths'
      title='Oaths'
      description='Oaths sworn and received, kept and broken, and the gods who heard them.'
      icon={ScrollText}
    >
      <div
        data-surface='Oaths'
        className='@container/realm flex min-w-0 flex-col gap-4'
      >
        {total === 0 && (
          <EmptyState
            icon={ScrollText}
            size='compact'
            title='No oaths'
            description='No oath binds them and none is owed to them.'
          />
        )}
        {groups.map(([title, oaths]) =>
          oaths.length === 0 ? null : (
            <div key={title} className='flex min-w-0 flex-col gap-2'>
              <div className='flex min-w-0 items-center gap-2'>
                <Label variant='overline'>{title}</Label>
                <Badge size='sm' variant='secondary'>
                  {oaths.length}
                </Badge>
              </div>
              <ul
                className={
                  oaths.length > 1
                    ? 'grid min-w-0 grid-cols-1 gap-2 @xl/realm:grid-cols-2'
                    : 'grid min-w-0 grid-cols-1 gap-2'
                }
              >
                {oaths.map((oath) => (
                  <OathCard
                    key={oath.id}
                    oath={oath}
                    blocked={busy}
                    onBreak={() => breakIt.mutate(oath.id)}
                  />
                ))}
              </ul>
            </div>
          )
        )}
        <AdjustPanel
          trigger='Swear an oath'
          title='Swear a new oath'
          note='Bind this mortal by an oath, to someone or to no one. A broken oath costs honour, and more if a god heard it.'
        >
          <ChoiceGrid
            label='Oath'
            table={OATHS}
            value={kind}
            blocked={busy}
            onPick={setKind}
          />
          <div className='flex min-w-0 flex-wrap items-end gap-3'>
            <div className='min-w-48 flex-1'>
              <RecordField
                label='Sworn to'
                types={null}
                value={recipient}
                onChange={setRecipient}
                blocked={busy}
                placeholder='No one in particular'
              />
            </div>
            <Button
              size='sm'
              disabled={busy !== null}
              disabledReason={busy ?? undefined}
              onClick={() => swear.mutate(undefined)}
            >
              <ScrollText />
              Swear it
            </Button>
          </div>
        </AdjustPanel>
      </div>
    </Section>
  )
}
