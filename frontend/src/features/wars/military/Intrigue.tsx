import { useState } from 'react'
import {
  Drama,
  Eye,
  EyeOff,
  Gauge,
  Target,
  UserPlus,
  UserRound,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { EntityLink, Medallion, StatBar } from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { EntityPicker, Held, RecordButtons } from './controls'
import {
  AGENT_STATUS,
  OWNER_KIND,
  type RecordRow,
  nameOf,
  useRecords,
} from './depth'
import { COVER, PERCENT, busyOf } from './labels'
import {
  Adjust,
  ChoiceField,
  FieldGrid,
  NumberField,
  Panel,
  Plain,
  Tag,
} from './parts'
import {
  type Values,
  numbersOf,
  useRecordActions,
  useRecordCreate,
} from './recordHooks'

const COMMUNITIES = ['people', 'settlement', 'faction', 'cult', 'polity']
const AGENT_NUMBERS = ['skill', 'exposure'] as const

function AgentCard({
  row,
  networkId,
  blocked,
}: {
  row: RecordRow
  networkId: number
  blocked: string | null
}) {
  const actions = useRecordActions('spy_agent', row.id, networkId)
  const [draft, setDraft] = useState<Values>({})
  const value = (key: string) => (key in draft ? draft[key] : row.values[key])
  const status = nameOf(AGENT_STATUS, String(row.values.status))
  const mortal = row.refs.mortal_entity_id
  return (
    <li className='flex min-w-0 flex-col gap-2 rounded-lg border bg-background p-2.5'>
      <div className='flex min-w-0 items-center gap-2.5'>
        <Medallion
          icon={nameOf(COVER, String(row.values.cover)).icon}
          tone={status.tone}
          size='sm'
        />
        <div className='flex min-w-0 flex-1 flex-col'>
          {mortal ? (
            <EntityLink kind='entity' id={String(mortal.id)}>
              {mortal.name}
            </EntityLink>
          ) : (
            <Text as='span'>A nameless agent</Text>
          )}
          <Muted as='span' variant='caption' truncate>
            {`As a ${nameOf(COVER, String(row.values.cover)).label.toLowerCase()} since epoch ${String(row.values.since_epoch)}`}
          </Muted>
        </div>
        <Tag item={status} />
        <Held locked={row.locked} />
      </div>
      <div className='grid min-w-0 grid-cols-2 gap-1.5'>
        <StatBar
          label='Skill'
          icon={Gauge}
          value={Number(row.values.skill ?? 0)}
          max={PERCENT}
          tone='info'
        />
        <StatBar
          label='Exposure'
          icon={EyeOff}
          value={Number(row.values.exposure ?? 0)}
          max={PERCENT}
          tone='warning'
        />
      </div>
      <Adjust title='Agent' note='Their cover, skill, exposure and fate.'>
        <FieldGrid>
          <ChoiceField
            label='Cover'
            icon={Drama}
            value={String(value('cover'))}
            table={COVER}
            blocked={blocked}
            onPick={(next) => setDraft({ ...draft, cover: next })}
          />
          <ChoiceField
            label='Fate'
            icon={UserRound}
            value={String(value('status'))}
            table={AGENT_STATUS}
            blocked={blocked}
            onPick={(next) => setDraft({ ...draft, status: next })}
          />
          <NumberField
            label='Skill'
            icon={Gauge}
            value={String(value('skill') ?? 0)}
            max={PERCENT}
            onChange={(next) => setDraft({ ...draft, skill: next })}
          />
          <NumberField
            label='Exposure'
            icon={EyeOff}
            value={String(value('exposure') ?? 0)}
            max={PERCENT}
            onChange={(next) => setDraft({ ...draft, exposure: next })}
          />
        </FieldGrid>
        <RecordButtons
          actions={actions}
          values={numbersOf(draft, AGENT_NUMBERS)}
          locked={row.locked}
          blocked={blocked}
          removeLabel='Recall'
        />
      </Adjust>
    </li>
  )
}

function NetworkCommand({
  row,
  ownerId,
  blocked,
}: {
  row: RecordRow
  ownerId: number
  blocked: string | null
}) {
  const actions = useRecordActions('spy_network', row.id, ownerId)
  const [draft, setDraft] = useState<Values>({})
  const value = (key: string) => (key in draft ? draft[key] : row.values[key])
  const target = value('target_entity_id')
  const spymaster = value('spymaster_entity_id')
  return (
    <Adjust
      title='Aim the network'
      note='Turn its eyes on another community, give it a spymaster, or say whose spies they are.'
      label='Aim'
    >
      <FieldGrid>
        <EntityPicker
          label='Watching'
          icon={Target}
          types={COMMUNITIES}
          value={typeof target === 'number' ? target : null}
          onChange={(next) => setDraft({ ...draft, target_entity_id: next })}
          blocked={blocked}
        />
        <EntityPicker
          label='Spymaster'
          icon={UserRound}
          types={['mortal']}
          value={typeof spymaster === 'number' ? spymaster : null}
          onChange={(next) => setDraft({ ...draft, spymaster_entity_id: next })}
          blocked={blocked}
        />
        <ChoiceField
          label='Whose spies'
          icon={Eye}
          value={String(value('owner_kind') ?? 'community')}
          table={OWNER_KIND}
          blocked={blocked}
          onPick={(next) => setDraft({ ...draft, owner_kind: next })}
        />
      </FieldGrid>
      <RecordButtons
        actions={actions}
        values={draft}
        locked={row.locked}
        blocked={blocked}
        deletable={false}
      />
    </Adjust>
  )
}

export function NetworkAgents({
  networkId,
  ownerId,
  blocked,
}: {
  networkId: number
  ownerId: number
  blocked: string | null
}) {
  const agents = useRecords('spy_agent', networkId)
  const networks = useRecords('spy_network', ownerId)
  const create = useRecordCreate('spy_agent', networkId)
  const [mortal, setMortal] = useState<number | null>(null)
  const [cover, setCover] = useState('merchant')
  const network = networks.data?.rows.find((row) => row.id === networkId)
  const rows = agents.data?.rows ?? []
  const revealed = Array.isArray(network?.values.revealed_aims)
    ? network.values.revealed_aims.length
    : 0
  const busy = busyOf(blocked, create.isPending)
  return (
    <div
      data-surface='SpyNetworks'
      className='flex min-w-0 flex-col gap-2 border-t pt-3'
    >
      <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
        <Label variant='overline'>Agents in the field</Label>
        {revealed > 0 && (
          <Plain icon={Eye}>{`${revealed} enemy aims laid bare`}</Plain>
        )}
      </div>
      {rows.length === 0 ? (
        <Muted variant='caption'>
          No named agents; the network runs on nameless informers.
        </Muted>
      ) : (
        <ul className='grid min-w-0 grid-cols-1 gap-2'>
          {rows.map((row) => (
            <AgentCard
              key={row.id}
              row={row}
              networkId={networkId}
              blocked={blocked}
            />
          ))}
        </ul>
      )}
      <div className='flex min-w-0 flex-col gap-2'>
        {network && (
          <NetworkCommand row={network} ownerId={ownerId} blocked={blocked} />
        )}
        <Adjust
          title='Place an agent'
          note='A living mortal goes under cover for this network.'
          label='Place an agent'
        >
          <FieldGrid>
            <EntityPicker
              label='Mortal'
              icon={UserRound}
              types={['mortal']}
              value={mortal}
              onChange={setMortal}
              blocked={blocked}
            />
            <ChoiceField
              label='Cover'
              icon={Drama}
              value={cover}
              table={COVER}
              blocked={blocked}
              onPick={setCover}
            />
          </FieldGrid>
          <Button
            size='sm'
            className='self-start'
            disabled={busy !== null || mortal === null}
            disabledReason={
              busy ?? (mortal === null ? 'Choose a mortal' : undefined)
            }
            onClick={() =>
              create.mutate({
                network_id: networkId,
                mortal_entity_id: mortal,
                cover,
              })
            }
          >
            <UserPlus />
            Place
          </Button>
        </Adjust>
      </div>
    </div>
  )
}

export function FoundNetwork({
  ownerId,
  blocked,
}: {
  ownerId: number
  blocked: string | null
}) {
  const create = useRecordCreate('spy_network', ownerId)
  const [target, setTarget] = useState<number | null>(null)
  const [cover, setCover] = useState('merchant')
  const busy = busyOf(blocked, create.isPending)
  return (
    <Panel
      title='Spies'
      icon={Eye}
      tone='verdigris'
      hint='Plant a network inside another community'
    >
      <Adjust
        title='Found a spy network'
        note='Its agents gather intel, steal secrets and stir trouble inside the target.'
        label='Found a network'
      >
        <FieldGrid>
          <EntityPicker
            label='Inside'
            icon={Target}
            types={COMMUNITIES}
            value={target}
            onChange={setTarget}
            blocked={blocked}
          />
          <ChoiceField
            label='Cover'
            icon={Drama}
            value={cover}
            table={COVER}
            blocked={blocked}
            onPick={setCover}
          />
        </FieldGrid>
        <Button
          size='sm'
          className='self-start'
          disabled={busy !== null || target === null}
          disabledReason={
            busy ?? (target === null ? 'Choose whom to watch' : undefined)
          }
          onClick={() =>
            create.mutate({
              owner_entity_id: ownerId,
              target_entity_id: target,
              cover,
              agents: 1,
              agent_ids: [],
              revealed_aims: [],
            })
          }
        >
          <Eye />
          Plant the network
        </Button>
      </Adjust>
    </Panel>
  )
}
