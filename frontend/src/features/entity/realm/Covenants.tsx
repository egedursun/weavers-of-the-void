import { useState } from 'react'
import {
  Dna,
  FileSignature,
  LockOpen,
  Merge,
  Plus,
  Save,
  Shield,
  Trash2,
  UserPlus,
  Users,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  EntityLink,
  Medallion,
  Paged,
  PagedList,
  RangeField,
} from '@/components/domain'
import { Label, Muted } from '@/components/typography'
import { MindPicker } from '@/features/entity/mind/parts'
import { useFrames } from '@/features/madeKinds/api'
import { frameTable } from '@/features/madeKinds/labels'
import { useGodAction } from '@/features/pantheon/godAction'
import { CLAUSES, PARTY_ROLES, TREATY_KINDS, type Named, named } from './labels'
import {
  AdjustPanel,
  ChoiceGrid,
  NumberField,
  Panel,
  RecordField,
  Tag,
} from './parts'

type House = components['schemas']['HouseView']
type Treaty = components['schemas']['TreatyView']
type ClauseKind = components['schemas']['ClauseKind']
type PartyRole = components['schemas']['PartyRole']
type TreatyKind = components['schemas']['TreatyKind']

const WORKING = 'Working…'
const PERCENT = 100
const MORTALS = ['mortal'] as const
const HOUSES = ['house'] as const
const ITEMS = ['item'] as const
const PARTIES = [
  'polity',
  'settlement',
  'people',
  'house',
  'cult',
  'faction',
  'beast',
  'mortal',
] as const

const HOUSE_TRAITS: Record<string, Named> = {
  long_lived: { label: 'Long-lived', icon: Dna, tone: 'success' },
  giant_blooded: { label: 'Giant-blooded', icon: Shield, tone: 'warning' },
  god_blooded: { label: 'God-blooded', icon: Dna, tone: 'gold' },
  cursed: { label: 'Cursed', icon: Dna, tone: 'danger' },
  fertile: { label: 'Fertile', icon: Users, tone: 'verdigris' },
  seer_gift: { label: 'Seer’s gift', icon: Dna, tone: 'info' },
}

export function FoundHouse({ blocked }: { blocked: string | null }) {
  const [founder, setFounder] = useState<number | null>(null)
  const found = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/house:found', {
          body: { mortal_id: founder ?? 0 },
        })
      ),
  })
  const busy = blocked ?? (found.isPending ? WORKING : null)
  return (
    <div data-surface='FoundHouse' className='flex min-w-0 flex-col gap-2'>
      <RecordField
        label='Founder'
        types={MORTALS}
        value={founder}
        onChange={setFounder}
        blocked={busy}
      />
      <Button
        size='sm'
        className='self-start'
        disabled={busy !== null || founder === null}
        disabledReason={busy ?? 'Choose every field first'}
        onClick={() => found.mutate(undefined)}
      >
        <UserPlus />
        Found the house
      </Button>
    </div>
  )
}

export function MergeHouses({
  house,
  blocked,
}: {
  house: House
  blocked: string | null
}) {
  const [into, setInto] = useState<number | null>(null)
  const merge = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/house:merge', {
          body: { house_id: house.id, into_id: into ?? 0 },
        })
      ),
  })
  const busy = blocked ?? (merge.isPending ? WORKING : null)
  return (
    <div data-surface='MergeHouses' className='flex min-w-0 flex-col gap-2'>
      <RecordField
        label='Fold this house into'
        types={HOUSES}
        value={into}
        onChange={setInto}
        blocked={busy}
      />
      <Button
        size='sm'
        className='self-start'
        disabled={busy !== null || into === null || into === house.id}
        disabledReason={busy ?? 'Choose every field first'}
        onClick={() => merge.mutate(undefined)}
      >
        <Merge />
        Merge the houses
      </Button>
    </div>
  )
}

export function HouseEditor({
  house,
  blocked,
}: {
  house: House
  blocked: string | null
}) {
  const [prestige, setPrestige] = useState(house.prestige)
  const [wealth, setWealth] = useState(String(house.wealth))
  const [motto, setMotto] = useState(house.motto ?? '')
  const [traits, setTraits] = useState<string[]>(house.traits)
  const [head, setHead] = useState<number | null>(house.head?.id ?? null)
  const [member, setMember] = useState<number | null>(null)
  const [item, setItem] = useState<number | null>(null)
  const save = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/house:edit', {
          body: {
            house_id: house.id,
            values: {
              prestige,
              wealth: Number(wealth) || 0,
              motto,
              traits,
              ...(head !== null ? { head } : {}),
            },
            release: [],
          },
        })
      ),
  })
  const release = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/house:edit', {
          body: { house_id: house.id, values: {}, release: house.locked },
        })
      ),
  })
  const join = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/house:member', {
          body: {
            house_id: house.id,
            mortal_id: member ?? 0,
            remove: false,
            by_marriage: false,
          },
        })
      ),
  })
  const heirloom = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/house:heirloom', {
          body: { house_id: house.id, item_id: item ?? 0, remove: false },
        })
      ),
  })
  const busy =
    blocked ??
    (save.isPending || release.isPending || join.isPending || heirloom.isPending
      ? WORKING
      : null)
  return (
    <Panel
      title='The house as you would have it'
      icon={Shield}
      tone='gold'
      hint='Head, prestige, wealth, motto, bloodline, members and heirlooms'
    >
      <div className='flex min-w-0 flex-col gap-2'>
        <PagedList
          items={house.traits}
          initial={12}
          noun={['entry', 'entries']}
          as='div'
          className='flex min-w-0 flex-wrap gap-1.5'
          listProps={{ 'data-surface': 'HouseEditor' }}
          itemKey={(trait) => trait}
        >
          {(trait) => <Tag key={trait} spec={named(HOUSE_TRAITS, trait)} />}
        </PagedList>
        <div className='flex min-w-0 flex-wrap gap-1.5'>
          {house.motto && (
            <Badge size='sm' variant='outline'>{`“${house.motto}”`}</Badge>
          )}
        </div>
      </div>
      <AdjustPanel
        trigger='Shape the house'
        title='Shape the house'
        note='Every value you set is held until released.'
        hold={house.locked.length > 0}
        onHold={(on) =>
          on ? save.mutate(undefined) : release.mutate(undefined)
        }
      >
        <RangeField
          label='Prestige'
          icon={Shield}
          value={prestige}
          min={0}
          max={PERCENT}
          level={`${prestige}`}
          lowLabel='Obscure'
          highLabel='Illustrious'
          onChange={setPrestige}
        />
        <NumberField
          label='Wealth'
          value={wealth}
          min={0}
          blocked={busy}
          onChange={setWealth}
        />
        <div className='flex min-w-0 flex-col gap-1'>
          <Label>Motto</Label>
          <Input
            value={motto}
            disabled={busy !== null}
            onChange={(event) => setMotto(event.target.value)}
          />
        </div>
        <RecordField
          label='Head of the house'
          types={MORTALS}
          value={head}
          onChange={setHead}
          blocked={busy}
        />
        <div
          role='group'
          aria-label='Bloodline'
          className='flex min-w-0 flex-wrap gap-2'
        >
          {Object.entries(HOUSE_TRAITS).map(([key, spec]) => (
            <Button
              key={key}
              size='sm'
              variant={traits.includes(key) ? 'default' : 'outline'}
              disabled={busy !== null}
              disabledReason={busy ?? 'Choose every field first'}
              onClick={() =>
                setTraits((current) =>
                  current.includes(key)
                    ? current.filter((value) => value !== key)
                    : [...current, key]
                )
              }
            >
              <spec.icon />
              {spec.label}
            </Button>
          ))}
        </div>
        <div className='flex min-w-0 flex-wrap gap-2'>
          <Button
            size='sm'
            disabled={busy !== null}
            disabledReason={busy ?? 'Choose every field first'}
            onClick={() => save.mutate(undefined)}
          >
            <Save />
            Hold the house so
          </Button>
          {house.locked.length > 0 && (
            <Button
              size='sm'
              variant='outline'
              disabled={busy !== null}
              disabledReason={busy ?? 'Choose every field first'}
              onClick={() => release.mutate(undefined)}
            >
              <LockOpen />
              Release the holds
            </Button>
          )}
        </div>
        <RecordField
          label='Take a mortal into the house'
          types={MORTALS}
          value={member}
          onChange={setMember}
          blocked={busy}
        />
        <Button
          size='sm'
          variant='outline'
          className='self-start'
          disabled={busy !== null || member === null}
          disabledReason={busy ?? 'Choose every field first'}
          onClick={() => join.mutate(undefined)}
        >
          <UserPlus />
          Join the house
        </Button>
        <RecordField
          label='Make a treasure an heirloom'
          types={ITEMS}
          value={item}
          onChange={setItem}
          blocked={busy}
        />
        <Button
          size='sm'
          variant='outline'
          className='self-start'
          disabled={busy !== null || item === null}
          disabledReason={busy ?? 'Choose every field first'}
          onClick={() => heirloom.mutate(undefined)}
        >
          <Plus />
          Keep it as an heirloom
        </Button>
      </AdjustPanel>
      <AdjustPanel
        trigger='Merge or found'
        title='Merge this house, or found another'
        note='Merging moves every living member into the greater house.'
      >
        <MergeHouses house={house} blocked={blocked} />
        <FoundHouse blocked={blocked} />
      </AdjustPanel>
    </Panel>
  )
}

type Draft = {
  kind: ClauseKind
  obligor: number | null
  beneficiary: number | null
  amount: string
  frame: string
}

function termsOf(
  kind: string,
  amount: string,
  frame: string
): Record<string, number | string> {
  return {
    ...(amount ? { amount: Number(amount) || 0 } : {}),
    ...(kind === 'fleet_limit' && frame ? { frame } : {}),
  }
}

function FrameChoice({
  value,
  blocked,
  onPick,
}: {
  value: string
  blocked: string | null
  onPick: (value: string) => void
}) {
  const frames = useFrames()
  const table = Object.fromEntries(
    Object.entries(frameTable(frames.data ?? [])).map(([key, spec]) => [
      key,
      spec.label,
    ])
  )
  return (
    <MindPicker
      label='Class of ship'
      value={value}
      table={table}
      blocked={blocked}
      placeholder='Every class'
      onPick={onPick}
    />
  )
}

export function SealTreaty({
  firstParty,
  blocked,
}: {
  firstParty: number | null
  blocked: string | null
}) {
  const [kind, setKind] = useState<string>('alliance_defensive')
  const [first, setFirst] = useState<number | null>(firstParty)
  const [second, setSecond] = useState<number | null>(null)
  const [guarantor, setGuarantor] = useState<number | null>(null)
  const [epochs, setEpochs] = useState('5')
  const [clauses, setClauses] = useState<Draft[]>([])
  const seal = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/treaty:sign', {
          body: {
            kind: kind as TreatyKind,
            parties: [
              {
                party_id: first ?? 0,
                role: (kind === 'vassalage'
                  ? 'vassal'
                  : 'signatory') as PartyRole,
              },
              {
                party_id: second ?? 0,
                role: (kind === 'vassalage'
                  ? 'overlord'
                  : 'signatory') as PartyRole,
              },
              ...(guarantor !== null
                ? [{ party_id: guarantor, role: 'guarantor' as PartyRole }]
                : []),
            ],
            clauses: clauses.map((clause) => ({
              kind: clause.kind,
              obligor_id: clause.obligor ?? first,
              beneficiary_id: clause.beneficiary ?? second,
              params: termsOf(clause.kind, clause.amount, clause.frame),
            })),
            epochs: Number(epochs) || null,
          },
        })
      ),
  })
  const busy = blocked ?? (seal.isPending ? WORKING : null)
  return (
    <div data-surface='SealTreaty' className='flex min-w-0 flex-col gap-3'>
      <ChoiceGrid
        label='Kind of treaty'
        table={TREATY_KINDS}
        value={kind}
        blocked={busy}
        onPick={setKind}
      />
      <div className='grid min-w-0 grid-cols-1 gap-2 @md/realm:grid-cols-3'>
        <RecordField
          label='First party'
          types={PARTIES}
          value={first}
          onChange={setFirst}
          blocked={busy}
        />
        <RecordField
          label='Second party'
          types={PARTIES}
          value={second}
          onChange={setSecond}
          blocked={busy}
        />
        <RecordField
          label='Guarantor'
          types={PARTIES}
          value={guarantor}
          onChange={setGuarantor}
          blocked={busy}
        />
      </div>
      <NumberField
        label='Epochs it holds'
        value={epochs}
        min={1}
        blocked={busy}
        onChange={setEpochs}
      />
      <div className='flex min-w-0 flex-col gap-2'>
        <Label>Clauses</Label>
        {clauses.length === 0 && (
          <Muted>
            Without clauses the treaty takes the usual terms of its kind.
          </Muted>
        )}
        <Paged items={clauses}>
          {(clause, index) => {
            const spec = named(CLAUSES, clause.kind)
            return (
              <div
                key={`${clause.kind}-${index}`}
                className='flex min-w-0 flex-wrap items-end gap-2 rounded-md border p-2'
              >
                <Medallion icon={spec.icon} tone={spec.tone} size='sm' />
                <Badge size='sm' variant='secondary'>
                  {spec.label}
                </Badge>
                <NumberField
                  label={clause.kind === 'fleet_limit' ? 'Tonnage' : 'Amount'}
                  value={clause.amount}
                  min={0}
                  blocked={busy}
                  onChange={(value) =>
                    setClauses((current) =>
                      current.map((item, at) =>
                        at === index ? { ...item, amount: value } : item
                      )
                    )
                  }
                />
                {clause.kind === 'fleet_limit' && (
                  <FrameChoice
                    value={clause.frame}
                    blocked={busy}
                    onPick={(value) =>
                      setClauses((current) =>
                        current.map((item, at) =>
                          at === index ? { ...item, frame: value } : item
                        )
                      )
                    }
                  />
                )}
                <Button
                  size='sm'
                  variant='outline'
                  disabled={busy !== null}
                  disabledReason={busy ?? 'Choose every field first'}
                  onClick={() =>
                    setClauses((current) =>
                      current.filter((_, at) => at !== index)
                    )
                  }
                >
                  <Trash2 />
                  Strike
                </Button>
              </div>
            )
          }}
        </Paged>
        <div className='flex min-w-0 flex-wrap gap-1.5'>
          {Object.entries(CLAUSES).map(([key, spec]) => (
            <Button
              key={key}
              size='sm'
              variant='outline'
              disabled={busy !== null}
              disabledReason={busy ?? 'Choose every field first'}
              onClick={() =>
                setClauses((current) => [
                  ...current,
                  {
                    kind: key as ClauseKind,
                    obligor: null,
                    beneficiary: null,
                    amount: '',
                    frame: '',
                  },
                ])
              }
            >
              <spec.icon />
              {spec.label}
            </Button>
          ))}
        </div>
      </div>
      <Button
        size='sm'
        className='self-start'
        disabled={busy !== null || first === null || second === null}
        disabledReason={busy ?? 'Choose every field first'}
        onClick={() => seal.mutate(undefined)}
      >
        <FileSignature />
        Seal the treaty
      </Button>
    </div>
  )
}

export function TreatyBuilder({
  treaty,
  blocked,
}: {
  treaty: Treaty
  blocked: string | null
}) {
  const [clauseKind, setClauseKind] = useState<string>('tribute')
  const [amount, setAmount] = useState('100')
  const [frame, setFrame] = useState('')
  const [party, setParty] = useState<number | null>(null)
  const [role, setRole] = useState<string>('guarantor')
  const first = treaty.parties[0]?.id ?? null
  const second = treaty.parties[1]?.id ?? null
  const add = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/treaty:clause_add', {
          body: {
            treaty_id: treaty.id,
            kind: clauseKind as ClauseKind,
            obligor_id: first,
            beneficiary_id: second,
            params: termsOf(clauseKind, amount, frame),
          },
        })
      ),
  })
  const remove = useGodAction({
    run: (clauseId: number) =>
      unwrap(
        api.POST('/api/actions/treaty:clause_remove', {
          body: { clause_id: clauseId },
        })
      ),
  })
  const bind = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/treaty:party_add', {
          body: {
            treaty_id: treaty.id,
            party_id: party ?? 0,
            role: role as PartyRole,
          },
        })
      ),
  })
  const release = useGodAction({
    run: (partyId: number) =>
      unwrap(
        api.POST('/api/actions/treaty:party_remove', {
          body: { treaty_id: treaty.id, party_id: partyId },
        })
      ),
  })
  const unhold = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/treaty:edit', {
          body: { treaty_id: treaty.id, hold: [], release: treaty.locked },
        })
      ),
  })
  const busy =
    blocked ??
    (add.isPending ||
    remove.isPending ||
    bind.isPending ||
    release.isPending ||
    unhold.isPending
      ? WORKING
      : null)
  return (
    <Panel
      title='Rewrite the treaty'
      icon={FileSignature}
      tone='info'
      hint='Write clauses in or out, bind guarantors, release its holds'
    >
      <ul className='flex min-w-0 flex-col gap-1.5'>
        <Paged items={treaty.clauses} as='li'>
          {(clause) => (
            <li key={clause.id} className='flex min-w-0 items-center gap-2'>
              <Tag spec={named(CLAUSES, clause.kind)} />
              <Muted
                truncate
              >{`${clause.obligor ?? 'someone'} → ${clause.beneficiary ?? 'someone'}`}</Muted>
              <Button
                size='sm'
                variant='outline'
                className='ml-auto'
                disabled={busy !== null}
                disabledReason={busy ?? 'Choose every field first'}
                onClick={() => remove.mutate(clause.id)}
              >
                <Trash2 />
                Strike
              </Button>
            </li>
          )}
        </Paged>
        <Paged items={treaty.parties}>
          {(item) => (
            <li key={item.id} className='flex min-w-0 items-center gap-2'>
              <Tag spec={named(PARTY_ROLES, item.role)} />
              <EntityLink kind='entity' id={String(item.id)}>
                {item.name}
              </EntityLink>
              <Button
                size='sm'
                variant='outline'
                className='ml-auto'
                disabled={busy !== null}
                disabledReason={busy ?? 'Choose every field first'}
                onClick={() => release.mutate(item.id)}
              >
                <LockOpen />
                Release
              </Button>
            </li>
          )}
        </Paged>
      </ul>
      <AdjustPanel
        trigger='Add a clause'
        title='Write a clause in'
        note='The first party owes it to the second; it runs from the next age.'
      >
        <ChoiceGrid
          label='Clause'
          table={CLAUSES}
          value={clauseKind}
          blocked={busy}
          onPick={setClauseKind}
        />
        <NumberField
          label={clauseKind === 'fleet_limit' ? 'Tonnage' : 'Amount'}
          value={amount}
          min={0}
          blocked={busy}
          onChange={setAmount}
        />
        {clauseKind === 'fleet_limit' && (
          <FrameChoice value={frame} blocked={busy} onPick={setFrame} />
        )}
        <Button
          size='sm'
          className='self-start'
          disabled={busy !== null}
          disabledReason={busy ?? 'Choose every field first'}
          onClick={() => add.mutate(undefined)}
        >
          <Plus />
          Write it in
        </Button>
      </AdjustPanel>
      <AdjustPanel
        trigger='Bind a party'
        title='Bind another party'
        note='A guarantor marches against whoever breaks the treaty.'
      >
        <RecordField
          label='Party'
          types={PARTIES}
          value={party}
          onChange={setParty}
          blocked={busy}
        />
        <ChoiceGrid
          label='Role'
          table={PARTY_ROLES}
          value={role}
          blocked={busy}
          onPick={setRole}
        />
        <Button
          size='sm'
          className='self-start'
          disabled={busy !== null || party === null}
          disabledReason={busy ?? 'Choose every field first'}
          onClick={() => bind.mutate(undefined)}
        >
          <UserPlus />
          Bind them
        </Button>
      </AdjustPanel>
      {treaty.locked.length > 0 && (
        <Button
          size='sm'
          variant='outline'
          className='self-start'
          disabled={busy !== null}
          disabledReason={busy ?? 'Choose every field first'}
          onClick={() => unhold.mutate(undefined)}
        >
          <LockOpen />
          Release its term and standing
        </Button>
      )}
    </Panel>
  )
}
