import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  Anchor,
  Ban,
  BookLock,
  Building2,
  Church,
  Cog,
  Coins,
  Crown,
  Eye,
  Flag,
  Gavel,
  Hammer,
  HandCoins,
  Handshake,
  HardHat,
  KeyRound,
  Landmark,
  Link2,
  LockOpen,
  Medal,
  Megaphone,
  PackageOpen,
  PackageSearch,
  Palette,
  Plus,
  Save,
  ScrollText,
  Shield,
  ShieldCheck,
  Ship,
  Skull,
  Sparkles,
  Store,
  Sword,
  Swords,
  Target,
  Tent,
  Trash2,
  TriangleAlert,
  Trophy,
  UserMinus,
  UserPlus,
  Users,
  Vote,
  Crosshair,
  Gem,
  Sailboat,
  UsersRound,
  Banknote,
  Speech,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Switch } from '@/components/ui/switch'
import {
  EmptyState,
  EntityLink,
  KpiTile,
  Medallion,
  RangeField,
  Section,
  StatBar,
  Paged,
  LoadingBlock,
  FieldTile,
} from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { NamedRecord } from '../NamedRecord'
import { loreKeys } from '../api/keys'
import { PowerBalance } from '../realm/Statecraft'
import { type Named, named, plain } from '../realm/labels'
import {
  AdjustPanel,
  ChoiceGrid,
  NumberField,
  Panel,
  RecordField,
  Tag,
} from '../realm/parts'

type Faction = components['schemas']['FactionView']
type GoalKind = components['schemas']['FactionGoalKind']
type Rank = components['schemas']['FactionRank']
type Kind = components['schemas']['FactionKind']

const WORKING = 'Working…'
const PERCENT = 100
const MORTALS = ['mortal'] as const
const REALMS = ['polity'] as const
const TARGETS = [
  'polity',
  'settlement',
  'people',
  'mortal',
  'cult',
  'faction',
] as const

const FACTION_KINDS: Record<string, Named> = {
  merchant_guild: { label: 'Trade association', icon: Store, tone: 'gold' },
  craft_guild: { label: 'Craft association', icon: Hammer, tone: 'gold' },
  priesthood: { label: 'Priesthood', icon: Sparkles, tone: 'verdigris' },
  warrior_order: { label: 'Warrior order', icon: Shield, tone: 'danger' },
  noble_council: { label: 'Noble council', icon: Crown, tone: 'gold' },
  peasant_league: { label: "Farmers' league", icon: Users, tone: 'success' },
  rebels: { label: 'Rebels', icon: Flag, tone: 'danger' },
  bandits: { label: 'Bandits', icon: Skull, tone: 'danger' },
  pirates: { label: 'Pirates', icon: Sailboat, tone: 'danger' },
  assassins: { label: 'Assassins', icon: Sword, tone: 'danger' },
  scholars_academy: { label: 'Academy', icon: ScrollText, tone: 'info' },
  secret_society: { label: 'Secret society', icon: BookLock, tone: 'muted' },
  mercenary_company: {
    label: 'Mercenary company',
    icon: Swords,
    tone: 'warning',
  },
  interworld_federation: {
    label: 'Interworld federation',
    icon: Handshake,
    tone: 'info',
  },
  wandering_market: { label: 'Wandering market', icon: Store, tone: 'success' },
  route_raiders: { label: 'Route raiders', icon: Ship, tone: 'danger' },
  social_circle: { label: 'Social circle', icon: Users, tone: 'success' },
  mage_order: { label: 'Mage order', icon: Sparkles, tone: 'verdigris' },
  estate: { label: 'Estate of the realm', icon: Landmark, tone: 'gold' },
  party: { label: 'Party', icon: Vote, tone: 'info' },
  movement: { label: 'Movement', icon: Megaphone, tone: 'warning' },
  chartered_company: {
    label: 'Chartered company',
    icon: Building2,
    tone: 'gold',
  },
  holy_order: { label: 'Holy order', icon: Church, tone: 'verdigris' },
  crime_family: { label: 'Crime family', icon: HandCoins, tone: 'danger' },
  thieves_guild: { label: "Thieves' ring", icon: KeyRound, tone: 'warning' },
  smuggling_ring: {
    label: 'Smuggling ring',
    icon: PackageOpen,
    tone: 'warning',
  },
  pirate_confederacy: {
    label: 'Pirate confederacy',
    icon: Anchor,
    tone: 'danger',
  },
  art_movement: { label: 'Art movement', icon: Palette, tone: 'verdigris' },
  workers_union: { label: "Workers' union", icon: Hammer, tone: 'warning' },
  engineers_society: { label: "Engineers' society", icon: Cog, tone: 'info' },
  financiers: { label: 'Financiers', icon: Coins, tone: 'gold' },
  veterans: { label: "Veterans' association", icon: Medal, tone: 'warning' },
  worker_body: { label: 'Worker body', icon: HardHat, tone: 'warning' },
  street_gang: { label: 'Street gang', icon: Crosshair, tone: 'danger' },
  trafficking_ring: { label: 'Trafficking ring', icon: Link2, tone: 'danger' },
  club: { label: 'Club', icon: Trophy, tone: 'gold' },
  league: { label: 'League', icon: Medal, tone: 'info' },
  fence_network: {
    label: 'Network of fences',
    icon: PackageSearch,
    tone: 'danger',
  },
  counterfeiting_ring: {
    label: 'Counterfeiting ring',
    icon: Banknote,
    tone: 'danger',
  },
}
const FACTION_SCALES: Record<string, Named> = {
  band: { label: 'Band', icon: Users, tone: 'muted' },
  company: { label: 'Company', icon: Users, tone: 'info' },
  organisation: { label: 'Organisation', icon: Users, tone: 'gold' },
  network: { label: 'Network', icon: UsersRound, tone: 'success' },
}
const FACTION_GOALS: Record<string, Named> = {
  lower_taxes: { label: 'Lower taxes', icon: Coins, tone: 'gold' },
  monopoly_on: { label: 'Win a monopoly', icon: Store, tone: 'gold' },
  install_claimant: { label: 'Crown a claimant', icon: Crown, tone: 'danger' },
  abolish_law: { label: 'Abolish a law', icon: Ban, tone: 'warning' },
  enact_law: { label: 'Enact a law', icon: Gavel, tone: 'info' },
  war_on: { label: 'War on an enemy', icon: Swords, tone: 'danger' },
  peace_with: {
    label: 'Peace with an enemy',
    icon: Handshake,
    tone: 'success',
  },
  protect_craft: { label: 'Protect the craft', icon: Hammer, tone: 'gold' },
  convert_realm: {
    label: 'Convert the realm',
    icon: Sparkles,
    tone: 'verdigris',
  },
  independence: { label: 'Independence', icon: Flag, tone: 'warning' },
  loot: { label: 'Loot', icon: Skull, tone: 'danger' },
  gain_privilege: { label: 'Gain a privilege', icon: Gem, tone: 'gold' },
  win_office: { label: 'Win an office', icon: Landmark, tone: 'info' },
  ruin_rival: { label: 'Ruin a rival', icon: Sword, tone: 'danger' },
  protect_members: {
    label: 'Protect its members',
    icon: ShieldCheck,
    tone: 'info',
  },
  found_settlement: {
    label: 'Found a settlement',
    icon: Tent,
    tone: 'success',
  },
}
const FACTION_ACTIONS: Record<string, Named> = {
  lobby: { label: 'Lobbied', icon: Megaphone, tone: 'info' },
  bribe: { label: 'Bribed', icon: HandCoins, tone: 'warning' },
  petition: { label: 'Petitioned', icon: Vote, tone: 'info' },
  strike: { label: 'Struck', icon: Hammer, tone: 'warning' },
  riot: { label: 'Rioted', icon: Flag, tone: 'danger' },
  coup: { label: 'Coup', icon: Crown, tone: 'danger' },
  assassinate: { label: 'Assassination', icon: Sword, tone: 'danger' },
  smuggle: { label: 'Smuggled', icon: Ship, tone: 'warning' },
  raid: { label: 'Raided', icon: Skull, tone: 'danger' },
  fund_war: { label: 'Funded a war', icon: Coins, tone: 'gold' },
  recruit: { label: 'Recruited', icon: UserPlus, tone: 'success' },
  schism: { label: 'Split', icon: TriangleAlert, tone: 'warning' },
  suppressed: { label: 'Hunted', icon: ShieldCheck, tone: 'danger' },
  hired: { label: 'Hired', icon: Handshake, tone: 'success' },
  defected: { label: 'Defected', icon: Target, tone: 'danger' },
  propaganda: { label: 'Propaganda', icon: Speech, tone: 'info' },
  boycott: { label: 'Boycott', icon: Ban, tone: 'warning' },
}
const RANKS: Record<string, Named> = {
  leader: { label: 'Leader', icon: Crown, tone: 'gold' },
  officer: { label: 'Officer', icon: Shield, tone: 'info' },
  member: { label: 'Member', icon: Users, tone: 'muted' },
  novice: { label: 'Novice', icon: UserPlus, tone: 'muted' },
}

function useFaction(id: number) {
  return useQuery({
    queryKey: [...loreKeys.entity(id), 'faction'],
    queryFn: () =>
      unwrap(
        api.GET('/api/factions/{faction_id}', {
          params: { path: { faction_id: id } },
        })
      ),
  })
}

function AgendaCard({
  faction,
  blocked,
}: {
  faction: Faction
  blocked: string | null
}) {
  const [kind, setKind] = useState<string>('lower_taxes')
  const [target, setTarget] = useState<number | null>(null)
  const [key, setKey] = useState('')
  const [priority, setPriority] = useState(80)
  const set = useGodAction({
    writes: [{ lever: 'faction:goal' }],
    run: (change: {
      goalId?: number
      kind: GoalKind
      remove?: boolean
      priority?: number
    }) =>
      unwrap(
        api.POST('/api/actions/faction:goal', {
          body: {
            faction_id: faction.id,
            kind: change.kind,
            goal_id: change.goalId ?? null,
            target_id: change.goalId ? null : target,
            target_key: change.goalId ? null : key || null,
            priority: change.priority ?? priority,
            remove: change.remove ?? false,
          },
        })
      ),
  })
  const busy = blocked ?? (set.isPending ? WORKING : null)
  return (
    <Panel
      title='Agenda'
      icon={Target}
      tone='gold'
      hint='What the faction strives for, first to last'
      count={faction.goals.length}
    >
      <div data-surface='AgendaCard' className='flex min-w-0 flex-col gap-2'>
        {faction.goals.length === 0 && (
          <Muted>The faction wants nothing it has named.</Muted>
        )}
        <Paged items={faction.goals}>
          {(goal) => {
            const spec = named(FACTION_GOALS, goal.kind)
            return (
              <div
                key={goal.id}
                className='flex min-w-0 flex-col gap-1.5 rounded-md border surface-sheen border-gild/60 bg-card p-2'
              >
                <div className='flex min-w-0 items-center gap-2'>
                  <Medallion icon={spec.icon} tone={spec.tone} size='sm' />
                  <Text truncate>{spec.label}</Text>
                  {goal.target_id !== null && goal.target && (
                    <EntityLink kind='entity' id={String(goal.target_id)}>
                      {goal.target}
                    </EntityLink>
                  )}
                  {goal.target_key && (
                    <Badge size='sm' variant='outline'>
                      {plain({}, goal.target_key)}
                    </Badge>
                  )}
                  {goal.set_by_player && (
                    <Badge size='sm' variant='secondary'>
                      By your will
                    </Badge>
                  )}
                  <Button
                    act={set}
                    size='sm'
                    variant='outline'
                    className='ml-auto'
                    disabled={busy !== null}
                    disabledReason={busy ?? 'Choose every field first'}
                    onClick={() =>
                      set.mutate({
                        goalId: goal.id,
                        kind: goal.kind,
                        remove: true,
                      })
                    }
                  >
                    <Trash2 />
                    Strike
                  </Button>
                </div>
                <StatBar
                  label='Progress'
                  value={goal.progress}
                  max={PERCENT}
                  icon={Target}
                  tone='success'
                />
                <RangeField
                  act={set}
                  label='Priority'
                  icon={Flag}
                  value={goal.priority}
                  min={0}
                  max={PERCENT}
                  level={`${goal.priority}`}
                  lowLabel='Idle wish'
                  highLabel='Overriding aim'
                  onChange={(value) =>
                    set.mutate({
                      goalId: goal.id,
                      kind: goal.kind,
                      priority: value,
                    })
                  }
                />
              </div>
            )
          }}
        </Paged>
      </div>
      <AdjustPanel
        acts={[set]}
        trigger='Set a goal'
        title='Give the faction a goal'
        note='Goals you set are pursued before any the faction chose itself.'
      >
        <ChoiceGrid
          label='Goal'
          table={FACTION_GOALS}
          value={kind}
          blocked={busy}
          onPick={setKind}
        />
        <RecordField
          label='Target'
          types={TARGETS}
          value={target}
          onChange={setTarget}
          blocked={busy}
        />
        <FieldTile label='Law kind or commodity'>
          <Input
            value={key}
            disabled={busy !== null}
            onChange={(event) => setKey(event.target.value)}
          />
        </FieldTile>
        <RangeField
          label='Priority'
          icon={Flag}
          value={priority}
          min={0}
          max={PERCENT}
          level={`${priority}`}
          lowLabel='Idle wish'
          highLabel='Overriding aim'
          onChange={setPriority}
        />
        <Button
          act={set}
          size='sm'
          className='self-start'
          disabled={busy !== null}
          disabledReason={busy ?? 'Choose every field first'}
          onClick={() => set.mutate({ kind: kind as GoalKind })}
        >
          <Plus />
          Set the goal
        </Button>
      </AdjustPanel>
    </Panel>
  )
}

function FactionActionLog({ faction }: { faction: Faction }) {
  return (
    <Panel
      title='Deeds'
      icon={ScrollText}
      tone='info'
      hint='Every move the faction has made'
      count={faction.actions.length}
    >
      <ol
        data-surface='FactionActionLog'
        className='flex min-w-0 flex-col gap-1.5'
      >
        {faction.actions.length === 0 && (
          <Muted>The faction has not yet moved.</Muted>
        )}
        <Paged items={faction.actions} as='li'>
          {(item) => {
            const spec = named(FACTION_ACTIONS, item.kind)
            return (
              <li
                key={item.id}
                className='flex min-w-0 flex-wrap items-center gap-2'
              >
                <Badge
                  size='sm'
                  variant='outline'
                >{`Epoch ${item.epoch}`}</Badge>
                <Tag spec={spec} />
                {item.target_id !== null && item.target && (
                  <EntityLink kind='entity' id={String(item.target_id)}>
                    {item.target}
                  </EntityLink>
                )}
                {item.amount > 0 && (
                  <Badge
                    size='sm'
                    variant='secondary'
                  >{`${item.amount}`}</Badge>
                )}
                <Badge
                  size='sm'
                  variant={item.success ? 'success' : 'destructive'}
                >
                  {item.success ? 'Done' : 'Failed'}
                </Badge>
                {item.note && <Muted truncate>{item.note}</Muted>}
              </li>
            )
          }}
        </Paged>
      </ol>
    </Panel>
  )
}

function Members({
  faction,
  blocked,
}: {
  faction: Faction
  blocked: string | null
}) {
  const [mortal, setMortal] = useState<number | null>(null)
  const change = useGodAction({
    writes: [{ lever: 'faction:member' }],
    run: (input: { mortal: number; rank?: Rank; remove?: boolean }) =>
      unwrap(
        api.POST('/api/actions/faction:member', {
          body: {
            faction_id: faction.id,
            mortal_id: input.mortal,
            rank: input.rank ?? null,
            remove: input.remove ?? false,
          },
        })
      ),
  })
  const busy = blocked ?? (change.isPending ? WORKING : null)
  return (
    <Panel
      title='Members'
      icon={Users}
      tone='verdigris'
      hint='Named members and their ranks'
      count={faction.members.length}
    >
      <ul className='flex min-w-0 flex-col gap-1.5'>
        <Paged items={faction.members} as='li'>
          {(member) => (
            <li
              key={member.id}
              className='flex min-w-0 flex-wrap items-center gap-2'
            >
              <Tag spec={named(RANKS, member.rank)} />
              <EntityLink kind='entity' id={String(member.id)}>
                {member.name}
              </EntityLink>
              {!member.alive && (
                <Badge size='sm' variant='outline'>
                  Dead
                </Badge>
              )}
              <div className='ml-auto flex gap-1'>
                {Object.keys(RANKS)
                  .filter((rank) => rank !== member.rank)
                  .map((rank) => (
                    <Button
                      act={change}
                      key={rank}
                      size='sm'
                      variant='outline'
                      disabled={busy !== null}
                      disabledReason={busy ?? 'Choose every field first'}
                      onClick={() =>
                        change.mutate({ mortal: member.id, rank: rank as Rank })
                      }
                    >
                      {named(RANKS, rank).label}
                    </Button>
                  ))}
                <Button
                  act={change}
                  size='sm'
                  variant='outline'
                  disabled={busy !== null}
                  disabledReason={busy ?? 'Choose every field first'}
                  onClick={() =>
                    change.mutate({ mortal: member.id, remove: true })
                  }
                >
                  <UserMinus />
                  Cast out
                </Button>
              </div>
            </li>
          )}
        </Paged>
      </ul>
      <div className='flex min-w-0 items-end gap-2'>
        <RecordField
          label='Take in a member'
          types={MORTALS}
          value={mortal}
          onChange={setMortal}
          blocked={busy}
        />
        <Button
          act={change}
          size='sm'
          disabled={busy !== null || mortal === null}
          disabledReason={busy ?? 'Choose every field first'}
          onClick={() => change.mutate({ mortal: mortal ?? 0, rank: 'member' })}
        >
          <UserPlus />
          Take in
        </Button>
      </div>
    </Panel>
  )
}

function Levers({
  faction,
  blocked,
}: {
  faction: Faction
  blocked: string | null
}) {
  const [kind, setKind] = useState<string>(faction.kind)
  const [values, setValues] = useState({
    treasury: faction.treasury,
    cohesion: faction.cohesion,
    secrecy: faction.secrecy,
    reputation: faction.reputation,
    loyalty: faction.loyalty,
    pay: faction.pay,
  })
  const [armed, setArmed] = useState(faction.armed)
  const [amount, setAmount] = useState('50')
  const [realm, setRealm] = useState<number | null>(
    faction.chartered_by_id ?? faction.employer_id
  )
  const [monopoly, setMonopoly] = useState(faction.monopoly ?? '')
  const edit = useGodAction({
    writes: [{ lever: 'faction:edit' }],
    run: () =>
      unwrap(
        api.POST('/api/actions/faction:edit', {
          body: {
            faction_id: faction.id,
            values: { ...values, armed, kind: kind as Kind },
            release: [],
          },
        })
      ),
  })
  const release = useGodAction({
    writes: [{ lever: 'faction:edit' }],
    run: () =>
      unwrap(
        api.POST('/api/actions/faction:edit', {
          body: { faction_id: faction.id, values: {}, release: faction.locked },
        })
      ),
  })
  const fund = useGodAction({
    writes: [{ lever: 'faction:fund' }],
    run: (sign: number) =>
      unwrap(
        api.POST('/api/actions/faction:fund', {
          body: {
            faction_id: faction.id,
            amount: sign * (Number(amount) || 0),
          },
        })
      ),
  })
  const outlaw = useGodAction({
    writes: [{ lever: 'faction:outlaw' }],
    run: (on: boolean) =>
      unwrap(
        api.POST('/api/actions/faction:outlaw', {
          body: { faction_id: faction.id, outlawed: on },
        })
      ),
  })
  const charter = useGodAction({
    writes: [{ lever: 'faction:charter' }],
    run: (revoke: boolean) =>
      unwrap(
        api.POST('/api/actions/faction:charter', {
          body: {
            faction_id: faction.id,
            polity_id: revoke ? null : realm,
            monopoly: monopoly || null,
          },
        })
      ),
  })
  const contract = useGodAction({
    writes: [{ lever: 'faction:contract' }],
    run: (end: boolean) =>
      unwrap(
        api.POST('/api/actions/faction:contract', {
          body: {
            faction_id: faction.id,
            polity_id: end ? null : realm,
            pay: values.pay,
            epochs: 3,
          },
        })
      ),
  })
  const busy =
    blocked ??
    (edit.isPending ||
    release.isPending ||
    fund.isPending ||
    outlaw.isPending ||
    charter.isPending ||
    contract.isPending
      ? WORKING
      : null)
  return (
    <Panel
      title='Your hand on the faction'
      icon={Gavel}
      tone='gold'
      hint='Fund it, outlaw it, charter it, hire it, or rewrite what it is'
    >
      <div className='flex min-w-0 flex-wrap items-end gap-2'>
        <NumberField
          label='Amount'
          icon={Coins}
          value={amount}
          min={0}
          blocked={busy}
          onChange={setAmount}
        />
        <Button
          act={fund}
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? 'Choose every field first'}
          onClick={() => fund.mutate(1)}
        >
          <HandCoins />
          Fund
        </Button>
        <Button
          act={fund}
          size='sm'
          variant='outline'
          disabled={busy !== null}
          disabledReason={busy ?? 'Choose every field first'}
          onClick={() => fund.mutate(-1)}
        >
          <Ban />
          Drain
        </Button>
        <FieldTile label='Outlawed'>
          <Switch
            act={outlaw}
            checked={faction.outlawed}
            disabled={busy !== null}
            onCheckedChange={(on) => outlaw.mutate(on)}
          />
        </FieldTile>
      </div>
      <AdjustPanel
        acts={[charter, contract]}
        trigger='Charter or hire'
        title='Charter the faction or seal a condotta'
        note='A charter makes pirates privateers or grants an association its monopoly; a condotta puts a free company in a realm’s pay.'
      >
        <RecordField
          label='Realm'
          types={REALMS}
          value={realm}
          onChange={setRealm}
          blocked={busy}
        />
        <FieldTile label='Monopoly over'>
          <Input
            value={monopoly}
            placeholder='The goods it holds alone'
            disabled={busy !== null}
            onChange={(event) => setMonopoly(event.target.value)}
          />
        </FieldTile>
        <div className='flex min-w-0 flex-wrap gap-2'>
          <Button
            act={charter}
            size='sm'
            disabled={busy !== null || realm === null}
            disabledReason={busy ?? 'Choose every field first'}
            onClick={() => charter.mutate(false)}
          >
            <ScrollText />
            Grant the charter
          </Button>
          <Button
            act={charter}
            size='sm'
            variant='outline'
            disabled={busy !== null}
            disabledReason={busy ?? 'Choose every field first'}
            onClick={() => charter.mutate(true)}
          >
            <Ban />
            Revoke the charter
          </Button>
          {faction.kind === 'mercenary_company' && (
            <>
              <Button
                act={contract}
                size='sm'
                disabled={busy !== null || realm === null}
                disabledReason={busy ?? 'Choose every field first'}
                onClick={() => contract.mutate(false)}
              >
                <Handshake />
                Seal the condotta
              </Button>
              <Button
                act={contract}
                size='sm'
                variant='outline'
                disabled={busy !== null}
                disabledReason={busy ?? 'Choose every field first'}
                onClick={() => contract.mutate(true)}
              >
                <Ban />
                End the condotta
              </Button>
            </>
          )}
        </div>
      </AdjustPanel>
      <AdjustPanel
        acts={[edit, release]}
        trigger='Rewrite the faction'
        title='Rewrite what the faction is'
        note='Every value you set is held until released.'
        hold={faction.locked.length > 0}
        onHold={(on) =>
          on ? edit.mutate(undefined) : release.mutate(undefined)
        }
      >
        <ChoiceGrid
          label='Kind'
          table={FACTION_KINDS}
          value={kind}
          blocked={busy}
          onPick={setKind}
        />
        {(['cohesion', 'secrecy', 'reputation', 'loyalty'] as const).map(
          (key) => (
            <RangeField
              key={key}
              label={plain({}, key)}
              icon={key === 'secrecy' ? Eye : key === 'loyalty' ? Crown : Users}
              value={values[key]}
              min={0}
              max={PERCENT}
              level={`${values[key]}`}
              lowLabel='None'
              highLabel='Full'
              onChange={(value) =>
                setValues((current) => ({ ...current, [key]: value }))
              }
            />
          )
        )}
        <div className='grid min-w-0 grid-cols-1 gap-2 @md/realm:grid-cols-2'>
          <NumberField
            label='Treasury'
            icon={Coins}
            value={String(values.treasury)}
            min={0}
            blocked={busy}
            onChange={(value) =>
              setValues((current) => ({
                ...current,
                treasury: Number(value) || 0,
              }))
            }
          />
          <NumberField
            label='Pay asked'
            icon={HandCoins}
            value={String(values.pay)}
            min={0}
            blocked={busy}
            onChange={(value) =>
              setValues((current) => ({ ...current, pay: Number(value) || 0 }))
            }
          />
        </div>
        <label className='flex items-center gap-2'>
          <FieldTile label='Bears arms'>
            <Switch
              checked={armed}
              disabled={busy !== null}
              aria-label='Armed'
              onCheckedChange={setArmed}
            />
          </FieldTile>
        </label>
        <div className='flex min-w-0 flex-wrap gap-2'>
          <Button
            act={edit}
            size='sm'
            disabled={busy !== null}
            disabledReason={busy ?? 'Choose every field first'}
            onClick={() => edit.mutate(undefined)}
          >
            <Save />
            Hold the faction so
          </Button>
          {faction.locked.length > 0 && (
            <Button
              act={release}
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
      </AdjustPanel>
    </Panel>
  )
}

function FactionBody({
  faction,
  blocked,
}: {
  faction: Faction
  blocked: string | null
}) {
  const kind = named(FACTION_KINDS, faction.kind)
  return (
    <div
      data-surface='FactionView'
      className='@container/realm flex min-w-0 flex-col gap-4'
    >
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Medallion icon={kind.icon} tone={kind.tone} />
        <Text>{kind.label}</Text>
        <Tag spec={named(FACTION_SCALES, faction.scale)} />
        {faction.outlawed && <Badge variant='destructive'>Outlawed</Badge>}
        {faction.chartered_by && (
          <Badge variant='success'>{`Chartered by ${faction.chartered_by}`}</Badge>
        )}
        {faction.employer && (
          <Badge variant='info'>{`In the pay of ${faction.employer}`}</Badge>
        )}
        {faction.monopoly && (
          <Badge variant='secondary'>{`Monopoly on ${plain({}, faction.monopoly)}`}</Badge>
        )}
      </div>
      {faction.contract_id !== null && (
        <Muted as='span' variant='caption'>
          {'Its condotta is sealed by '}
          <NamedRecord id={faction.contract_id} fallback='a lost treaty' />
        </Muted>
      )}
      {Object.keys(faction.influence_over).length > 0 && (
        <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
          <Muted as='span' variant='caption'>
            Holds sway over
          </Muted>
          {Object.entries(faction.influence_over).map(([id, share]) => (
            <Badge key={id} size='sm' variant='outline'>
              {`${faction.influence_names[id] ?? 'a community'} ${share}`}
            </Badge>
          ))}
        </div>
      )}
      {Object.keys(faction.cohort_share).length > 0 && (
        <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
          <Muted as='span' variant='caption'>
            Drawn from
          </Muted>
          {Object.entries(faction.cohort_share).map(([cohort, share]) => (
            <Badge key={cohort} size='sm' variant='outline'>
              {`${plain({}, cohort)} ${share}%`}
            </Badge>
          ))}
        </div>
      )}
      <div className='grid min-w-0 grid-cols-2 gap-2 @2xl/realm:grid-cols-4'>
        <KpiTile
          label='Treasury'
          value={faction.treasury}
          icon={Coins}
          tone='gold'
        />
        <KpiTile
          label='Cohesion'
          value={faction.cohesion}
          icon={Users}
          tone='success'
        />
        <KpiTile
          label='Secrecy'
          value={faction.secrecy}
          icon={Eye}
          tone='muted'
        />
        <KpiTile
          label='Reputation'
          value={faction.reputation}
          icon={Megaphone}
          tone='info'
        />
      </div>
      {faction.leader_id !== null && faction.leader && (
        <div className='flex min-w-0 items-center gap-2'>
          <Crown
            aria-hidden='true'
            className='size-icon-sm text-muted-foreground'
          />
          <Label>Led by</Label>
          <EntityLink kind='entity' id={String(faction.leader_id)}>
            {faction.leader}
          </EntityLink>
        </div>
      )}
      <PowerBalance
        slices={faction.balance}
        title='The realm’s power balance'
      />
      <AgendaCard faction={faction} blocked={blocked} />
      <Members faction={faction} blocked={blocked} />
      <FactionActionLog faction={faction} />
      <Levers
        key={JSON.stringify([faction.locked, faction.kind, faction.treasury])}
        faction={faction}
        blocked={blocked}
      />
    </div>
  )
}

export function FactionSection({
  factionId,
  readOnlyReason,
}: {
  factionId: number
  readOnlyReason?: string | null
}) {
  const view = useFaction(factionId)
  const { reason } = useGodGate()
  const blocked = readOnlyReason ?? reason()
  return (
    <Section
      id='section-faction'
      title='Faction'
      description='What it is, what it wants, who leads it and what it has done.'
      icon={Flag}
    >
      {view.isPending && <LoadingBlock label='Reading the faction' />}
      {view.isError && (
        <EmptyState
          icon={TriangleAlert}
          title='The faction could not be read'
          description={view.error.message}
        />
      )}
      {view.data && <FactionBody faction={view.data} blocked={blocked} />}
    </Section>
  )
}
