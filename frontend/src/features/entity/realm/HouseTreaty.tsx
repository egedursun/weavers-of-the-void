import { useState } from 'react'
import {
  Handshake,
  HeartCrack,
  ScrollText,
  Shield,
  Skull,
  Swords,
  TriangleAlert,
  UserPlus,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { EmptyState, EntityLink, KpiTile, Section } from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { MindPicker } from '../mind/parts'
import { useHouse, useOaths, useTreaty } from './api'

type Member = components['schemas']['HouseMemberView']
type OathKind = components['schemas']['OathKind']
type TreatyStatus = components['schemas']['TreatyStatus']

const WORKING = 'Working…'
const OATHS: OathKind[] = [
  'fealty',
  'vengeance',
  'celibacy',
  'pilgrimage',
  'protection',
  'silence',
  'blood_brotherhood',
]

function words(value: string): string {
  return value.replaceAll('_', ' ')
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

function FamilyTree({ members }: { members: Member[] }) {
  return (
    <div data-surface='FamilyTree' className='flex min-w-0 flex-col gap-3'>
      {generations(members).map((row, index) => (
        <div key={index} className='flex min-w-0 flex-col gap-1'>
          <Label variant='overline'>{`Generation ${index + 1}`}</Label>
          <ul className='flex min-w-0 flex-wrap gap-2'>
            {row.map((member) => (
              <li
                key={member.id}
                className='flex min-w-40 flex-col gap-1 rounded-lg border bg-muted/30 p-2'
              >
                <div className='flex min-w-0 items-center gap-1'>
                  {!member.alive && (
                    <Skull
                      aria-hidden='true'
                      className='size-icon-sm text-muted-foreground'
                    />
                  )}
                  <EntityLink kind='entity' id={String(member.id)}>
                    {member.name}
                  </EntityLink>
                </div>
                <div className='flex min-w-0 flex-wrap gap-1'>
                  {member.sex && <Badge variant='outline'>{member.sex}</Badge>}
                  {member.age !== null && (
                    <Badge variant='outline'>{`age ${member.age}`}</Badge>
                  )}
                  {member.by_marriage && (
                    <Badge variant='outline'>by marriage</Badge>
                  )}
                  {member.office && (
                    <Badge variant='info'>{words(member.office)}</Badge>
                  )}
                  {member.lasting_injuries > 0 && (
                    <Badge variant='warning'>{`${member.lasting_injuries} lasting wounds`}</Badge>
                  )}
                </div>
                {!member.alive && member.fate && (
                  <Muted variant='caption'>{member.fate}</Muted>
                )}
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
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
  const [claimant, setClaimant] = useState('')
  const [polity, setPolity] = useState('')
  const [strength, setStrength] = useState('50')
  const grant = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/claim:grant', {
          body: {
            mortal_id: Number(claimant),
            polity_id: Number(polity),
            strength: Number(strength) || 50,
            basis: 'divine',
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
      {view.data && (
        <div data-surface='HouseView' className='flex min-w-0 flex-col gap-5'>
          <div className='flex min-w-0 flex-wrap items-center gap-2'>
            <Badge variant='info'>{`${words(view.data.emblem.field ?? 'plain')} field, a ${view.data.emblem.charge ?? 'mark'}`}</Badge>
            {view.data.motto && (
              <Badge variant='outline'>{view.data.motto}</Badge>
            )}
            {view.data.traits.map((trait) => (
              <Badge key={trait} variant='warning'>
                {words(trait)}
              </Badge>
            ))}
            {view.data.parent && (
              <Badge variant='outline'>
                {'branch of '}
                <EntityLink kind='entity' id={String(view.data.parent.id)}>
                  {view.data.parent.name}
                </EntityLink>
              </Badge>
            )}
            {view.data.polity && (
              <Badge variant='outline'>
                <EntityLink kind='entity' id={String(view.data.polity.id)}>
                  {view.data.polity.name}
                </EntityLink>
              </Badge>
            )}
          </div>
          <div className='grid min-w-0 grid-cols-2 gap-3 md:grid-cols-4'>
            <KpiTile
              label='Prestige'
              value={String(view.data.prestige)}
              icon={Shield}
            />
            <KpiTile
              label='Living'
              value={String(
                view.data.members.filter((member) => member.alive).length
              )}
              icon={UserPlus}
            />
            <KpiTile
              label='Claims'
              value={String(view.data.claims.length)}
              icon={ScrollText}
            />
            <KpiTile
              label='Heirlooms'
              value={String(view.data.heirlooms.length)}
              icon={Shield}
            />
          </div>
          <FamilyTree members={view.data.members} />
          {view.data.claims.length > 0 && (
            <div className='flex min-w-0 flex-col gap-1'>
              <Label variant='overline'>Claims</Label>
              {view.data.claims.map((claim) => (
                <Text key={claim.id}>
                  <EntityLink kind='entity' id={String(claim.claimant_id)}>
                    {claim.claimant}
                  </EntityLink>
                  {' on '}
                  <EntityLink kind='entity' id={String(claim.polity_id)}>
                    the realm
                  </EntityLink>
                  {` · ${words(claim.basis)} · ${claim.strength}${claim.pressed ? ' · pressed' : ''}`}
                </Text>
              ))}
            </div>
          )}
          {view.data.heirlooms.length > 0 && (
            <div className='flex min-w-0 flex-wrap gap-2'>
              {view.data.heirlooms.map((item) => (
                <Badge key={item.id} variant='outline'>
                  <EntityLink kind='entity' id={String(item.id)}>
                    {item.name}
                  </EntityLink>
                </Badge>
              ))}
            </div>
          )}
          <div className='flex min-w-0 flex-wrap items-end gap-3'>
            <div className='flex w-32 flex-col gap-1'>
              <Label>Claimant id</Label>
              <Input
                type='number'
                min={1}
                value={claimant}
                aria-label='Claimant id'
                onChange={(event) => setClaimant(event.target.value)}
              />
            </div>
            <div className='flex w-32 flex-col gap-1'>
              <Label>Realm id</Label>
              <Input
                type='number'
                min={1}
                value={polity}
                aria-label='Realm id'
                onChange={(event) => setPolity(event.target.value)}
              />
            </div>
            <div className='flex w-24 flex-col gap-1'>
              <Label>Strength</Label>
              <Input
                type='number'
                min={0}
                max={100}
                value={strength}
                aria-label='Strength'
                onChange={(event) => setStrength(event.target.value)}
              />
            </div>
            <Button
              size='sm'
              disabled={busy !== null || claimant === '' || polity === ''}
              disabledReason={busy ?? 'Name the claimant and the realm'}
              onClick={() => grant.mutate(undefined)}
            >
              <ScrollText />
              Grant a claim
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
      {view.data && (
        <div data-surface='TreatyView' className='flex min-w-0 flex-col gap-4'>
          <div className='flex min-w-0 flex-wrap gap-2'>
            <Badge variant='info'>{words(view.data.kind)}</Badge>
            <Badge
              variant={
                view.data.status === 'broken'
                  ? 'destructive'
                  : view.data.status === 'in_force'
                    ? 'success'
                    : 'outline'
              }
            >
              {words(view.data.status)}
            </Badge>
            <Badge variant='outline'>{`Signed in epoch ${view.data.signed_epoch}`}</Badge>
            {view.data.until_epoch !== null && (
              <Badge variant='outline'>{`Holds until epoch ${view.data.until_epoch}`}</Badge>
            )}
            {view.data.renewals > 0 && (
              <Badge variant='outline'>{`Renewed ${view.data.renewals} times`}</Badge>
            )}
            {view.data.witness_son_id !== null && (
              <Badge variant='warning'>Sworn before a god</Badge>
            )}
          </div>
          <div className='flex min-w-0 flex-col gap-1'>
            <Label variant='overline'>Parties</Label>
            {view.data.parties.map((party) => (
              <div key={party.id} className='flex min-w-0 items-center gap-2'>
                <EntityLink kind='entity' id={String(party.id)}>
                  {party.name}
                </EntityLink>
                <Badge variant='outline'>{words(party.role)}</Badge>
                {view.data.status === 'in_force' && (
                  <Button
                    size='sm'
                    variant='ghost'
                    disabled={busy !== null}
                    disabledReason={busy ?? undefined}
                    onClick={() => breakIt.mutate(party.id)}
                  >
                    <HeartCrack />
                    Make them break it
                  </Button>
                )}
              </div>
            ))}
          </div>
          <div className='flex min-w-0 flex-col gap-1'>
            <Label variant='overline'>Clauses</Label>
            {view.data.clauses.map((clause) => (
              <Text
                key={clause.id}
              >{`${words(clause.kind)}${clause.obligor ? `: ${clause.obligor}` : ''}${clause.beneficiary ? ` → ${clause.beneficiary}` : ''}${clause.last_kept_epoch !== null ? ` · kept in epoch ${clause.last_kept_epoch}` : ''}`}</Text>
            ))}
          </div>
          {view.data.breaches.length > 0 && (
            <div className='flex min-w-0 flex-col gap-1'>
              <Label variant='overline'>Breaches</Label>
              {view.data.breaches.map((item, index) => (
                <Text
                  key={index}
                  className='text-destructive'
                >{`Epoch ${item.epoch}: ${item.breaker ?? 'someone'} — ${item.note ?? ''}`}</Text>
              ))}
            </div>
          )}
          <div className='flex min-w-0 flex-wrap items-end gap-3'>
            <div className='flex w-32 flex-col gap-1'>
              <Label>Holds until epoch</Label>
              <Input
                type='number'
                min={0}
                value={until}
                placeholder='Forever'
                aria-label='Holds until epoch'
                onChange={(event) => setUntil(event.target.value)}
              />
            </div>
            <div className='min-w-36'>
              <MindPicker
                label='Standing'
                value={status}
                table={{
                  in_force: 'in force',
                  fulfilled: 'fulfilled',
                  expired: 'expired',
                  broken: 'broken',
                }}
                blocked={busy}
                onPick={setStatus}
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
        </div>
      )}
    </Section>
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
  const [recipient, setRecipient] = useState('')
  const swear = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/oath:swear', {
          body: {
            swearer_id: entityId,
            kind: kind as OathKind,
            recipient_id: recipient === '' ? null : Number(recipient),
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
  const all = [...view.data.sworn, ...view.data.received]
  return (
    <Section
      id='section-oaths'
      title='Oaths'
      description='Oaths sworn and received, kept and broken, and the gods who heard them.'
      icon={ScrollText}
    >
      <div data-surface='Oaths' className='flex min-w-0 flex-col gap-3'>
        {all.length === 0 && <Muted>No oath binds or is owed.</Muted>}
        {all.map((oath) => (
          <div
            key={oath.id}
            className='flex min-w-0 flex-wrap items-center gap-2'
          >
            <Badge
              variant={
                oath.status === 'broken'
                  ? 'destructive'
                  : oath.status === 'sworn'
                    ? 'info'
                    : 'success'
              }
            >{`${words(oath.kind)} · ${oath.status}`}</Badge>
            <Text>{`${oath.swearer}${oath.recipient ? ` to ${oath.recipient}` : ''}, epoch ${oath.sworn_epoch}${oath.deadline_epoch !== null ? `, due by ${oath.deadline_epoch}` : ''}`}</Text>
            {oath.witness_son_id !== null && (
              <Badge variant='warning'>witnessed by a god</Badge>
            )}
            {oath.status === 'sworn' && (
              <Button
                size='sm'
                variant='ghost'
                disabled={busy !== null}
                disabledReason={busy ?? undefined}
                onClick={() => breakIt.mutate(oath.id)}
              >
                <HeartCrack />
                Break it
              </Button>
            )}
          </div>
        ))}
        <div className='flex min-w-0 flex-wrap items-end gap-3'>
          <div className='min-w-40'>
            <MindPicker
              label='Oath'
              value={kind}
              table={Object.fromEntries(
                OATHS.map((item) => [item, words(item)])
              )}
              blocked={busy}
              onPick={setKind}
            />
          </div>
          <div className='flex w-36 flex-col gap-1'>
            <Label>Sworn to (id)</Label>
            <Input
              type='number'
              min={1}
              value={recipient}
              aria-label='Sworn to'
              onChange={(event) => setRecipient(event.target.value)}
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
      </div>
    </Section>
  )
}
