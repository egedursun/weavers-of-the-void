import { useState } from 'react'
import {
  Activity,
  Clock,
  Link2,
  Lock,
  Plug,
  ShieldCheck,
  Trash2,
  Unplug,
  Users,
  WifiOff,
} from 'lucide-react'
import { plural } from '@/lib/units'
import {
  EmptyState,
  KpiTile,
  LoadingBlock,
  Paged,
  Section,
  ShowMore,
  useShowMore,
} from '@/components/domain'
import { table } from '@/features/arcana/labels'
import {
  Chip,
  type Field,
  ForgeCard,
  RecordEditor,
  RecordRow,
} from '@/features/cosmography/parts'
import { StepButton, TextField } from '@/features/cycles/parts'
import { why } from '@/features/dominion/model'
import { Ref, ThingPicker } from '@/features/gatherings/parts'
import { ChoiceField, NumberField } from '@/features/wars/military/parts'
import {
  type NetworkMemberView,
  type NetworkNodeView,
  useMadeAction,
  useNodeNetworks,
  useProfileEdit,
  useRowDelete,
  useRowEdit,
} from './api'
import {
  NETWORK_ACCESS,
  NETWORK_CARRIERS,
  NETWORK_ICON,
  NETWORK_ROLES,
  OUTAGE_CAUSES,
} from './labels'

const SHOWN = 6
const YES_NO = { true: 'Yes', false: 'No' }
const CARRIES = [
  ['carries_messages', 'Messages'],
  ['carries_records', 'Records'],
  ['carries_control', 'Control of made things'],
  ['carries_money', 'Money'],
  ['carries_minds', 'Minds'],
  ['carries_opinion', 'Opinion'],
] as const

const PROFILE_FIELDS: readonly Field[] = [
  {
    key: 'carrier',
    label: 'How it carries',
    kind: 'pick',
    table: table(NETWORK_CARRIERS),
  },
  {
    key: 'access',
    label: 'Who may use it',
    kind: 'pick',
    table: table(NETWORK_ACCESS),
  },
  ...CARRIES.map(([key, label]): Field => ({
    key,
    label: `Carries ${label.toLowerCase()}`,
    kind: 'pick',
    table: YES_NO,
  })),
  { key: 'capacity', label: 'Capacity', kind: 'number', min: 0, max: 100 },
  {
    key: 'delay_days',
    label: 'Delay in days',
    kind: 'number',
    min: 0,
    max: 10000,
  },
  { key: 'security', label: 'Security', kind: 'number', min: 0, max: 100 },
  {
    key: 'reliability',
    label: 'Reliability',
    kind: 'number',
    min: 0,
    max: 100,
  },
  { key: 'curation', label: 'Curation', kind: 'number', min: 0, max: 100 },
  { key: 'censorship', label: 'Censorship', kind: 'number', min: 0, max: 100 },
  {
    key: 'owner_node_id',
    label: 'Owner of the network',
    kind: 'node',
    types: [],
  },
  {
    key: 'tech_level',
    label: 'Knowledge it takes to make',
    kind: 'number',
    min: 0,
    max: 100,
  },
  {
    key: 'down_until_epoch',
    label: 'Down until epoch',
    kind: 'number',
    min: 0,
    max: 100000,
  },
]

const MEMBER_FIELDS: readonly Field[] = [
  {
    key: 'role',
    label: 'Role on the network',
    kind: 'pick',
    table: table(NETWORK_ROLES),
  },
  {
    key: 'dependency_pct',
    label: 'Dependence (%)',
    kind: 'number',
    min: 0,
    max: 100,
  },
  { key: 'security', label: 'Security', kind: 'number', min: 0, max: 100 },
]

const GATEWAY_FIELDS: readonly Field[] = [
  { key: 'toll', label: 'Toll', kind: 'number', min: 0, max: 1000000 },
  {
    key: 'filter_pct',
    label: 'Filtered (%)',
    kind: 'number',
    min: 0,
    max: 100,
  },
  {
    key: 'owner_node_id',
    label: 'Keeper of the gateway',
    kind: 'node',
    types: [],
  },
]

function Member({
  member,
  blocked,
  showNetwork,
}: {
  member: NetworkMemberView
  blocked: string | null
  showNetwork: boolean
}) {
  const role = NETWORK_ROLES[member.role]
  const editing = useRowEdit('network_nodes', { id: member.id })
  const removing = useRowDelete('network_nodes', { id: member.id })
  return (
    <RecordRow
      icon={role.icon}
      tone={role.tone}
      title={
        showNetwork
          ? `${role.label} on ${member.network?.name ?? 'a lost network'}`
          : `${member.member?.name ?? 'A lost member'}, ${role.label.toLowerCase()}`
      }
      caption={`Dependence ${member.dependency_pct}%, security ${member.security}, joined in epoch ${member.joined_epoch}`}
      aside={<Ref node={showNetwork ? member.network : member.member} />}
    >
      <RecordEditor
        title='Set this membership'
        note='Values you set are held against the engine until you release them.'
        fields={MEMBER_FIELDS}
        locked={member.locked}
        busy={why(blocked, editing.isPending)}
        onSave={(values) => editing.mutate({ values, release: [] })}
        onRelease={(keys) => editing.mutate({ values: {}, release: keys })}
      />
      <StepButton
        icon={Unplug}
        label='Take it off the network'
        busy={why(blocked, removing.isPending)}
        onClick={() => removing.mutate()}
      />
    </RecordRow>
  )
}

function Gateway({
  gateway,
  blocked,
}: {
  gateway: NetworkNodeView['gateways'][number]
  blocked: string | null
}) {
  const editing = useRowEdit('network_gateways', { id: gateway.id })
  const removing = useRowDelete('network_gateways', { id: gateway.id })
  return (
    <RecordRow
      icon={Link2}
      tone='info'
      title={`Gateway between ${gateway.first?.name ?? 'a lost network'} and ${gateway.second?.name ?? 'a lost network'}`}
      caption={`Toll ${gateway.toll}, ${gateway.filter_pct}% filtered`}
      aside={<Ref node={gateway.owner} empty='kept by no one' />}
    >
      <RecordEditor
        title='Set this gateway'
        note='Values you set are held against the engine until you release them.'
        fields={GATEWAY_FIELDS}
        locked={gateway.locked}
        busy={why(blocked, editing.isPending)}
        onSave={(values) => editing.mutate({ values, release: [] })}
        onRelease={(keys) => editing.mutate({ values: {}, release: keys })}
      />
      <StepButton
        icon={Trash2}
        label='Close the gateway'
        busy={why(blocked, removing.isPending)}
        onClick={() => removing.mutate()}
      />
    </RecordRow>
  )
}

function Outage({
  outage,
  blocked,
}: {
  outage: NetworkNodeView['outages'][number]
  blocked: string | null
}) {
  const cause = OUTAGE_CAUSES[outage.cause]
  const removing = useRowDelete('network_outages', { id: outage.id })
  return (
    <RecordRow
      icon={cause.icon}
      tone={cause.tone}
      title={`${cause.label} brought it down in epoch ${outage.epoch}`}
      caption={`For ${plural(outage.epochs, 'epoch', 'epochs')}, severity ${outage.severity}`}
    >
      <StepButton
        icon={Trash2}
        label='Strike this outage from the record'
        busy={why(blocked, removing.isPending)}
        onClick={() => removing.mutate()}
      />
    </RecordRow>
  )
}

function NetworkControls({
  view,
  blocked,
}: {
  view: NetworkNodeView
  blocked: string | null
}) {
  const id = view.node.id
  const isNetwork = view.profile !== null
  const [name, setName] = useState('')
  const [carrier, setCarrier] = useState<string>('relay')
  const [place, setPlace] = useState<number | null>(null)
  const [network, setNetwork] = useState<number | null>(null)
  const [member, setMember] = useState<number | null>(null)
  const [role, setRole] = useState<string>('end')
  const [other, setOther] = useState<number | null>(null)
  const [toll, setToll] = useState('0')
  const [cause, setCause] = useState<string>('sabotage')
  const [epochs, setEpochs] = useState('1')
  const [severity, setSeverity] = useState('60')
  const founding = useMadeAction(
    'network:found',
    (_: void) => ({
      name: name.trim(),
      carrier: carrier as NonNullable<NetworkNodeView['profile']>['carrier'],
      owner_id: id,
      place_id: place,
    }),
    'A network is founded'
  )
  const joining = useMadeAction(
    'network:join',
    (_: void) => ({
      network_id: isNetwork ? id : (network ?? -1),
      member_id: isNetwork ? (member ?? -1) : id,
      role: role as NetworkMemberView['role'],
    }),
    'The member joins the network'
  )
  const linking = useMadeAction(
    'network:link',
    (_: void) => ({
      first_id: id,
      second_id: other ?? -1,
      toll: Number(toll) || 0,
    }),
    'A gateway joins the two networks'
  )
  const cutting = useMadeAction(
    'network:cut',
    (_: void) => ({
      network_id: id,
      cause: cause as NetworkNodeView['outages'][number]['cause'],
      epochs: Math.max(1, Number(epochs) || 1),
      severity: Number(severity) || 0,
    }),
    'The network goes down'
  )
  const unnamed = name.trim() ? null : 'Name the network first'
  const nobody = isNetwork
    ? member === null
      ? 'Pick the member who joins'
      : null
    : network === null
      ? 'Pick the network to join'
      : null
  const notNetwork = isNetwork ? null : `${view.node.name} is not a network`
  const noOther =
    other === null
      ? 'Pick the other network'
      : other === id
        ? 'A gateway joins two different networks'
        : null
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      <ForgeCard
        icon={NETWORK_ICON}
        tone='info'
        title={`Found a network owned by ${view.node.name}`}
        note='A network carries what you let it carry; its members come to depend on it and suffer when it goes down.'
        columns={3}
        action={
          <StepButton
            icon={NETWORK_ICON}
            label='Found it'
            variant='default'
            busy={why(blocked ?? unnamed, founding.isPending)}
            onClick={() => founding.mutate()}
          />
        }
      >
        <TextField
          label='Name of the network'
          value={name}
          blocked={blocked}
          onChange={setName}
        />
        <ChoiceField
          label='How it carries'
          value={carrier}
          table={NETWORK_CARRIERS}
          blocked={blocked}
          onPick={setCarrier}
        />
        <ThingPicker
          label='Where it is anchored'
          value={place}
          onChange={setPlace}
          blocked={blocked}
          types={['region', 'settlement', 'structure']}
        />
      </ForgeCard>
      <ForgeCard
        icon={Plug}
        tone='success'
        title={
          isNetwork
            ? 'Bring a member onto this network'
            : 'Bring this onto a network'
        }
        note='A member gains what the network carries and comes to depend on it.'
        columns={2}
        action={
          <StepButton
            icon={Plug}
            label='Join'
            busy={why(blocked ?? nobody, joining.isPending)}
            onClick={() => joining.mutate()}
          />
        }
      >
        {isNetwork ? (
          <ThingPicker
            label='Member'
            value={member}
            onChange={setMember}
            blocked={blocked}
          />
        ) : (
          <ThingPicker
            label='Network'
            value={network}
            onChange={setNetwork}
            blocked={blocked}
            types={['network']}
          />
        )}
        <ChoiceField
          label='Role on the network'
          value={role}
          table={NETWORK_ROLES}
          blocked={blocked}
          onPick={setRole}
        />
      </ForgeCard>
      <ForgeCard
        icon={Link2}
        tone='gold'
        title='Join it to another network by a gateway'
        note='What crosses the gateway pays its toll.'
        columns={2}
        action={
          <StepButton
            icon={Link2}
            label='Open the gateway'
            busy={why(blocked ?? notNetwork ?? noOther, linking.isPending)}
            onClick={() => linking.mutate()}
          />
        }
      >
        <ThingPicker
          label='Other network'
          value={other}
          onChange={setOther}
          blocked={blocked}
          types={['network']}
        />
        <NumberField label='Toll' value={toll} min={0} onChange={setToll} />
      </ForgeCard>
      <ForgeCard
        icon={WifiOff}
        tone='danger'
        title='Bring it down'
        note='While it is down its members go without what it carries.'
        columns={3}
        action={
          <StepButton
            icon={WifiOff}
            label='Bring it down'
            busy={why(blocked ?? notNetwork, cutting.isPending)}
            onClick={() => cutting.mutate()}
          />
        }
      >
        <ChoiceField
          label='Cause'
          value={cause}
          table={OUTAGE_CAUSES}
          blocked={blocked}
          onPick={setCause}
        />
        <NumberField
          label='Epochs down'
          value={epochs}
          min={1}
          max={100}
          onChange={setEpochs}
        />
        <NumberField
          label='Severity'
          value={severity}
          min={0}
          max={100}
          onChange={setSeverity}
        />
      </ForgeCard>
    </div>
  )
}

export function NetworkSection({
  nodeId,
  readOnlyReason = null,
}: {
  nodeId: number
  readOnlyReason?: string | null
}) {
  const query = useNodeNetworks(nodeId)
  const members = useShowMore(query.data?.members ?? [], SHOWN, SHOWN * 2)
  const memberships = useShowMore(
    query.data?.memberships ?? [],
    SHOWN,
    SHOWN * 2
  )
  const outages = useShowMore(query.data?.outages ?? [], SHOWN, SHOWN * 2)
  const editing = useProfileEdit(nodeId, 'network_profiles')
  const profile = query.data?.profile ?? null
  return (
    <Section
      id='section-networks'
      title='Networks: what it is joined to and what it carries'
      description='Networks carry messages, records, control, money, minds and opinion between their members by whatever means the world has. A network’s own page shows its members, gateways and outages; every other thing shows the networks it is on.'
      icon={NETWORK_ICON}
      tone='info'
    >
      <div
        data-surface='NetworkSection'
        className='flex min-w-0 flex-col gap-6'
      >
        {query.isPending ? (
          <LoadingBlock label='Reading its networks' />
        ) : query.isError ? (
          <EmptyState
            icon={NETWORK_ICON}
            size='inline'
            title='This could not be read'
            description={query.error.message}
          />
        ) : (
          <>
            {profile && (
              <>
                <div className='grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-3'>
                  <KpiTile
                    label='Carried by'
                    value={NETWORK_CARRIERS[profile.carrier].label}
                    icon={NETWORK_CARRIERS[profile.carrier].icon}
                    tone={NETWORK_CARRIERS[profile.carrier].tone}
                  />
                  <KpiTile
                    label='Running'
                    value={
                      profile.running
                        ? 'Running'
                        : `Down until epoch ${profile.down_until_epoch}`
                    }
                    icon={profile.running ? Activity : WifiOff}
                    tone={profile.running ? 'success' : 'danger'}
                  />
                  <KpiTile
                    label='Members'
                    value={String(query.data.members.length)}
                    icon={Users}
                    tone='info'
                  />
                  <KpiTile
                    label='Capacity, reliability'
                    value={`${profile.capacity}, ${profile.reliability}`}
                    icon={Activity}
                    tone='muted'
                  />
                  <KpiTile
                    label='Security, censorship'
                    value={`${profile.security}, ${profile.censorship}`}
                    icon={ShieldCheck}
                    tone={profile.censorship > 50 ? 'warning' : 'muted'}
                  />
                  <KpiTile
                    label='Delay, founded'
                    value={`${profile.delay_days} days, epoch ${profile.founded_epoch}`}
                    icon={Clock}
                    tone='muted'
                  />
                </div>
                <div className='flex min-w-0 flex-wrap items-center gap-2'>
                  <Chip icon={NETWORK_ACCESS[profile.access].icon}>
                    {NETWORK_ACCESS[profile.access].label}
                  </Chip>
                  {CARRIES.filter(([key]) => profile[key]).map(
                    ([key, label]) => (
                      <Chip key={key} icon={NETWORK_ICON}>
                        Carries {label.toLowerCase()}
                      </Chip>
                    )
                  )}
                  <Chip icon={Lock}>
                    Curation {profile.curation}, knowledge to make{' '}
                    {profile.tech_level}
                  </Chip>
                  <Ref node={profile.owner} empty='owned by no one' />
                </div>
                <RecordEditor
                  title='Set this network'
                  note='Values you set are held against the engine until you release them.'
                  fields={PROFILE_FIELDS}
                  locked={profile.locked}
                  busy={why(readOnlyReason, editing.isPending)}
                  onSave={(values) => editing.mutate({ values, release: [] })}
                  onRelease={(keys) =>
                    editing.mutate({ values: {}, release: keys })
                  }
                />
                <ul className='flex min-w-0 flex-col gap-2'>
                  {members.visible.map((member) => (
                    <Member
                      key={member.id}
                      member={member}
                      blocked={readOnlyReason}
                      showNetwork={false}
                    />
                  ))}
                </ul>
                <ShowMore state={members} />
                <ul className='flex min-w-0 flex-col gap-2'>
                  <Paged items={query.data.gateways} as='li'>
                    {(gateway) => (
                      <Gateway
                        key={gateway.id}
                        gateway={gateway}
                        blocked={readOnlyReason}
                      />
                    )}
                  </Paged>
                </ul>
                <ul className='flex min-w-0 flex-col gap-2'>
                  {outages.visible.map((outage) => (
                    <Outage
                      key={outage.id}
                      outage={outage}
                      blocked={readOnlyReason}
                    />
                  ))}
                </ul>
                <ShowMore state={outages} />
              </>
            )}
            {query.data.memberships.length ? (
              <div className='flex min-w-0 flex-col gap-2'>
                <ul className='flex min-w-0 flex-col gap-2'>
                  {memberships.visible.map((member) => (
                    <Member
                      key={member.id}
                      member={member}
                      blocked={readOnlyReason}
                      showNetwork
                    />
                  ))}
                </ul>
                <ShowMore state={memberships} />
              </div>
            ) : (
              <EmptyState
                icon={NETWORK_ICON}
                size='inline'
                title='On no network'
                description={`${query.data.node.name} is on no network; join one below.`}
              />
            )}
            <NetworkControls view={query.data} blocked={readOnlyReason} />
          </>
        )}
      </div>
    </Section>
  )
}
