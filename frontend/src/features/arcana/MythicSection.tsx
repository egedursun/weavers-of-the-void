import { useState } from 'react'
import {
  Footprints,
  Ghost,
  Landmark,
  Play,
  ScrollText,
  Trash2,
  Unlink,
  UserCheck,
  UserMinus,
  UserPlus,
} from 'lucide-react'
import { actKindValues } from '@/api/generated/schema'
import { plural } from '@/lib/units'
import { Button } from '@/components/ui/button'
import {
  EmptyState,
  KpiTile,
  LoadingBlock,
  PagedList,
  Section,
} from '@/components/domain'
import { Label, Muted } from '@/components/typography'
import {
  Chip,
  Facts,
  ForgeCard,
  Meter,
  RecordEditor,
  RecordRow,
} from '@/features/cosmography/parts'
import { GOD_KINDS, why } from '@/features/dominion/model'
import { NodePicker } from '@/features/dominion/parts'
import { wordOf } from '@/features/entity/affairs/labels'
import { TextField } from '@/features/entity/economy/parts'
import { MindPicker } from '@/features/entity/mind/parts'
import { Ref } from '@/features/gatherings/parts'
import { useKindTable } from '@/features/kinds/api'
import { CosmicOfficesPanel } from './CosmicOfficesPanel'
import {
  type GeasView,
  type HeroquestView,
  type MantlingView,
  type NodeMythicView,
  type ServitorView,
  useArcanaAction,
  useNodeMythic,
} from './api'
import {
  BOONS,
  GEAS_LAYERS,
  GEAS_MODES,
  GEAS_STATES,
  MANTLING_STATES,
  MYTH_ICON,
  ORIGINS,
  QUEST_STATES,
  REALMS,
  ROLES,
  SERVANT_ICON,
  TRIALS,
  listed,
  table,
} from './labels'
import { useEntityType } from './model'

type Values = Record<string, number | string | boolean | null>
type Edit = { values: Values; release: string[] }
const BOOLEAN = { true: 'Yes', false: 'No' }

function PartyEditor({
  quest,
  blocked,
}: {
  quest: HeroquestView
  blocked: string | null
}) {
  const [member, setMember] = useState<number | null>(null)
  const party = useArcanaAction(
    'heroquest:party',
    (members: number[]) => ({ quest_id: quest.id, members }),
    'The party is set'
  )
  const busy = why(blocked, party.isPending)
  const ids = quest.members.map((item) => item.id)
  const quester = quest.quester?.id ?? null
  const refused =
    member === null
      ? 'Choose a companion first'
      : ids.includes(member)
        ? 'Already walking beside the quester'
        : member === quester
          ? 'The quester cannot be its own companion'
          : null
  return (
    <div className='flex min-w-0 flex-col gap-2'>
      <Label variant='overline'>{`Party (${quest.members.length})`}</Label>
      {quest.members.length === 0 ? (
        <Muted variant='caption'>The quester walks alone.</Muted>
      ) : (
        <PagedList
          items={quest.members}
          initial={6}
          noun={['companion', 'companions']}
          className='flex min-w-0 flex-wrap gap-1.5'
          itemKey={(item) => item.id}
        >
          {(item) => (
            <li className='flex items-center gap-1'>
              <Chip icon={UserCheck}>{item.name}</Chip>
              <Button
                size='icon-sm'
                variant='ghost'
                aria-label={`Send ${item.name} home`}
                disabled={busy !== null}
                disabledReason={busy ?? undefined}
                onClick={() => party.mutate(ids.filter((id) => id !== item.id))}
              >
                <UserMinus />
              </Button>
            </li>
          )}
        </PagedList>
      )}
      <div className='grid min-w-0 grid-cols-1 items-end gap-2 sm:grid-cols-2'>
        <NodePicker
          label='Companion to add'
          value={member}
          onChange={setMember}
          blocked={busy}
          types={['mortal']}
        />
        <Button
          size='sm'
          variant='outline'
          disabled={busy !== null || refused !== null}
          disabledReason={busy ?? refused ?? undefined}
          onClick={() => {
            if (member !== null) party.mutate([...ids, member])
            setMember(null)
          }}
        >
          <UserPlus />
          Add to the party
        </Button>
      </div>
    </div>
  )
}

function QuestCard({
  quest,
  blocked,
}: {
  quest: HeroquestView
  blocked: string | null
}) {
  const edit = useArcanaAction(
    'heroquest:edit',
    (vars: Edit) => ({ quest_id: quest.id, ...vars }),
    'The heroquest is set'
  )
  const advance = useArcanaAction('heroquest:advance', (_: void) => ({
    quest_id: quest.id,
  }))
  const remove = useArcanaAction(
    'heroquest:delete',
    (_: void) => ({ quest_id: quest.id }),
    'The heroquest is struck out'
  )
  const busy = why(blocked, edit.isPending, advance.isPending, remove.isPending)
  const state = QUEST_STATES[quest.state]
  const realm = REALMS[quest.realm]
  const realmKinds = useKindTable('realm', null)
  const questing = quest.state === 'questing'
  return (
    <RecordRow
      icon={state.icon}
      tone={state.tone}
      title={<Ref node={quest.quester} empty='a lost quester' />}
      caption={`${state.label} · ${realm.label} · since epoch ${quest.start_epoch}${quest.end_epoch !== null ? `, ended in epoch ${quest.end_epoch}` : ''}`}
      aside={
        <div className='flex shrink-0 flex-wrap items-center gap-1'>
          <Button
            size='sm'
            variant='outline'
            disabled={busy !== null || !questing}
            disabledReason={
              busy ?? (questing ? undefined : 'Only a quest under way moves on')
            }
            onClick={() => advance.mutate()}
          >
            <Play />
            Next step
          </Button>
          <Button
            size='sm'
            variant='ghost'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => remove.mutate()}
          >
            <Trash2 />
            Remove
          </Button>
        </div>
      }
    >
      <Meter
        label={`Step ${quest.step} of ${quest.steps}`}
        value={quest.step}
        max={Math.max(quest.steps, 1)}
        tone='info'
      />
      <div className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-2'>
        <Meter
          label='Fidelity to the myth'
          value={quest.fidelity}
          tone='success'
        />
        <Meter
          label='Interference'
          value={quest.interference}
          tone='destructive'
        />
      </div>
      <div className='flex min-w-0 flex-wrap gap-1.5'>
        <Chip icon={realm.icon}>
          {quest.realm_kind_name
            ? `${quest.realm_kind_name} · ${realm.label}`
            : realm.label}
        </Chip>
        {quest.next_trial && (
          <Chip icon={TRIALS[quest.next_trial].icon}>
            {`Next: ${TRIALS[quest.next_trial].label.toLowerCase()}`}
          </Chip>
        )}
        {quest.deviated && (
          <Chip variant='warning'>Departed from the myth</Chip>
        )}
        {quest.boon && (
          <Chip icon={BOONS[quest.boon].icon}>{BOONS[quest.boon].label}</Chip>
        )}
      </div>
      <Facts
        items={[
          [
            'Legend',
            <Ref key='legend' node={quest.legend} empty='no legend' />,
          ],
          [
            'God of the myth',
            <Ref key='god' node={quest.god} empty='no god' />,
          ],
          [
            'Place',
            <Ref key='place' node={quest.place} empty='a mythic realm' />,
          ],
        ]}
      />
      <PartyEditor quest={quest} blocked={blocked} />
      <RecordEditor
        title='Reshape the heroquest'
        note='Values you set are held against the engine until you release them.'
        fields={[
          {
            key: 'state',
            label: 'State',
            kind: 'pick',
            table: table(QUEST_STATES),
          },
          { key: 'realm', label: 'Realm', kind: 'pick', table: table(REALMS) },
          {
            key: 'realm_kind_id',
            label: 'Realm it enters',
            kind: 'pick',
            table: realmKinds,
          },
          { key: 'boon', label: 'Boon', kind: 'pick', table: table(BOONS) },
          { key: 'steps', label: 'Steps', kind: 'number', min: 1 },
          { key: 'step', label: 'Step reached', kind: 'number', min: 0 },
          {
            key: 'fidelity',
            label: 'Fidelity',
            kind: 'number',
            min: 0,
            max: 100,
          },
          {
            key: 'interference',
            label: 'Interference',
            kind: 'number',
            min: 0,
            max: 100,
          },
          {
            key: 'deviated',
            label: 'Departed from the myth',
            kind: 'pick',
            table: BOOLEAN,
          },
          {
            key: 'legend_entity_id',
            label: 'Legend it walks (id)',
            kind: 'number',
            min: 1,
          },
          {
            key: 'god_node_id',
            label: 'God of the myth (id)',
            kind: 'number',
            min: 1,
          },
          {
            key: 'place_entity_id',
            label: 'Place of the myth (id)',
            kind: 'number',
            min: 1,
          },
          {
            key: 'start_epoch',
            label: 'Set out in epoch',
            kind: 'number',
            min: 0,
          },
          { key: 'end_epoch', label: 'Ended in epoch', kind: 'number', min: 0 },
        ]}
        locked={quest.locked}
        busy={busy}
        onSave={(values) => edit.mutate({ values, release: [] })}
        onRelease={(release) => edit.mutate({ values: {}, release })}
      />
    </RecordRow>
  )
}

function QuestForm({
  questerId,
  blocked,
}: {
  questerId: number
  blocked: string | null
}) {
  const [legend, setLegend] = useState<number | null>(null)
  const [member, setMember] = useState<number | null>(null)
  const [members, setMembers] = useState<number[]>([])
  const begin = useArcanaAction(
    'heroquest:begin',
    (_: void) => ({ quester_id: questerId, legend_id: legend ?? 0, members }),
    'A heroquest begins'
  )
  const busy = why(blocked, begin.isPending)
  const missing = legend === null ? 'Choose the legend it walks' : null
  return (
    <ForgeCard
      icon={Footprints}
      tone='gold'
      title='Send on a heroquest'
      note='The quester walks a legend step by step in a mythic realm; companions make each step easier.'
      columns={3}
      meta={
        <Chip
          icon={UserPlus}
        >{`${plural(members.length, 'companion', 'companions')}`}</Chip>
      }
      action={
        <Button
          size='sm'
          disabled={busy !== null || missing !== null}
          disabledReason={busy ?? missing ?? undefined}
          onClick={() => begin.mutate()}
        >
          <Footprints />
          Begin
        </Button>
      }
    >
      <NodePicker
        label='Legend'
        value={legend}
        onChange={setLegend}
        blocked={busy}
        types={['legend']}
      />
      <NodePicker
        label='Companion'
        value={member}
        onChange={setMember}
        blocked={busy}
        types={['mortal']}
      />
      <Button
        size='sm'
        variant='outline'
        disabled={busy !== null || member === null || members.includes(member)}
        disabledReason={
          busy ??
          (member === null
            ? 'Choose a companion first'
            : members.includes(member)
              ? 'Already going'
              : undefined)
        }
        onClick={() => {
          if (member !== null) setMembers([...members, member])
          setMember(null)
        }}
      >
        <UserPlus />
        Add companion
      </Button>
    </ForgeCard>
  )
}

function MantlingCard({
  mortalId,
  row,
  blocked,
}: {
  mortalId: number
  row: MantlingView | null
  blocked: string | null
}) {
  const edit = useArcanaAction(
    'mantling:edit',
    (vars: Edit) => ({ mortal_id: mortalId, ...vars }),
    'The path is set'
  )
  const remove = useArcanaAction(
    'mantling:delete',
    (_: void) => ({ mortal_id: mortalId }),
    'The mortal walks no god’s path'
  )
  const busy = why(blocked, edit.isPending, remove.isPending)
  const state = row ? MANTLING_STATES[row.state] : null
  return (
    <RecordRow
      icon={state?.icon ?? Footprints}
      tone={state?.tone ?? 'muted'}
      title={
        row ? <Ref node={row.god} empty='no god' /> : 'Walks no god’s path'
      }
      caption={
        row && state
          ? `${state.label} · since epoch ${row.since_epoch}${row.notified ? ' · you were told' : ''}`
          : 'The engine watches whether this mortal takes up a god’s deeds'
      }
      aside={
        <Button
          size='sm'
          variant='ghost'
          disabled={busy !== null || row === null}
          disabledReason={
            busy ?? (row === null ? 'There is no path to end' : undefined)
          }
          onClick={() => remove.mutate()}
        >
          <Trash2 />
          End the path
        </Button>
      }
    >
      {row && (
        <>
          <Meter label='Toward godhood' value={row.progress} tone='default' />
          <Facts
            items={[
              ['Deeds on the path', String(row.deeds)],
              ['Communities that worship it', String(row.worship)],
              ['Blocked by the Creator', row.blocked ? 'Yes' : 'No'],
            ]}
          />
        </>
      )}
      <RecordEditor
        title='Set the path'
        note='Block a mantling, or pin its progress; Fate still has to approve an ascension.'
        fields={[
          {
            key: 'god_node_id',
            label: 'God whose path (id)',
            kind: 'number',
            min: 1,
          },
          { key: 'deeds', label: 'Deeds', kind: 'number', min: 0 },
          {
            key: 'worship',
            label: 'Worshipping communities',
            kind: 'number',
            min: 0,
          },
          {
            key: 'progress',
            label: 'Progress',
            kind: 'number',
            min: 0,
            max: 100,
          },
          {
            key: 'state',
            label: 'State',
            kind: 'pick',
            table: table(MANTLING_STATES),
          },
          { key: 'blocked', label: 'Blocked', kind: 'pick', table: BOOLEAN },
          {
            key: 'notified',
            label: 'You were told',
            kind: 'pick',
            table: BOOLEAN,
          },
        ]}
        locked={row?.locked ?? []}
        busy={busy}
        onSave={(values) => edit.mutate({ values, release: [] })}
        onRelease={(release) => edit.mutate({ values: {}, release })}
      />
    </RecordRow>
  )
}

function ServitorCard({
  servitor,
  blocked,
}: {
  servitor: ServitorView
  blocked: string | null
}) {
  const spiritId = servitor.spirit?.id ?? 0
  const edit = useArcanaAction(
    'servitor:edit',
    (vars: Edit) => ({ spirit_id: spiritId, ...vars }),
    'The servitor is set'
  )
  const release = useArcanaAction(
    'servitor:release',
    (_: void) => ({ spirit_id: spiritId }),
    'The servitor is released'
  )
  const busy = why(blocked, edit.isPending, release.isPending)
  const role = ROLES[servitor.role]
  return (
    <RecordRow
      icon={role.icon}
      tone={role.tone}
      title={<Ref node={servitor.spirit} empty='a vanished spirit' />}
      caption={`${role.label} of ${servitor.god?.name ?? 'a god'} · ${ORIGINS[servitor.origin].label.toLowerCase()} · since epoch ${servitor.since_epoch}`}
      aside={
        <Button
          size='sm'
          variant='ghost'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => release.mutate()}
        >
          <Unlink />
          Release
        </Button>
      }
    >
      <Meter label='Loyalty' value={servitor.loyalty} tone='success' />
      <div className='flex min-w-0 flex-wrap gap-1.5'>
        <Chip icon={role.icon}>{role.label}</Chip>
        {servitor.fallen_to && (
          <Chip variant='destructive'>{`Fell to ${servitor.fallen_to.name}`}</Chip>
        )}
      </div>
      <Facts
        items={[
          ['God', <Ref key='god' node={servitor.god} />],
          [
            'Post',
            <Ref key='post' node={servitor.post} empty='no fixed post' />,
          ],
        ]}
      />
      <RecordEditor
        title='Reshape the servitor'
        note='Values you set are held against the engine until you release them.'
        fields={[
          {
            key: 'god_node_id',
            label: 'God it serves (id)',
            kind: 'number',
            min: 1,
          },
          {
            key: 'origin',
            label: 'Origin',
            kind: 'pick',
            table: table(ORIGINS),
          },
          { key: 'role', label: 'Role', kind: 'pick', table: table(ROLES) },
          { key: 'post_entity_id', label: 'Post (id)', kind: 'number', min: 1 },
          {
            key: 'loyalty',
            label: 'Loyalty',
            kind: 'number',
            min: 0,
            max: 100,
          },
          {
            key: 'fallen_to_node_id',
            label: 'Fallen to (god id)',
            kind: 'number',
            min: 1,
          },
        ]}
        locked={servitor.locked}
        busy={busy}
        onSave={(values) => edit.mutate({ values, release: [] })}
        onRelease={(keys) => edit.mutate({ values: {}, release: keys })}
      />
    </RecordRow>
  )
}

function ServitorForm({
  godId,
  blocked,
}: {
  godId: number
  blocked: string | null
}) {
  const [name, setName] = useState('')
  const [role, setRole] = useState('')
  const [post, setPost] = useState<number | null>(null)
  const make = useArcanaAction(
    'servitor:make',
    (_: void) => ({
      god_id: godId,
      name: name.trim(),
      role: role as ServitorView['role'],
      post_id: post,
    }),
    'A servitor enters its god’s service'
  )
  const busy = why(blocked, make.isPending)
  const missing =
    name.trim() === ''
      ? 'Name the servitor'
      : role === ''
        ? 'Choose its role'
        : null
  return (
    <ForgeCard
      icon={Ghost}
      tone='verdigris'
      title='Make a servitor'
      note='Each servitor does one work: messengers carry dreams, guards turn back desecrators, judges win veneration among the dead, the host fights divine battles, spies watch, agents work at their post, avengers bring fear to the scornful, guides lead the dead to their place, worshippers deepen awe, wardens keep order and keepers of accounts keep records alive.'
      columns={3}
      action={
        <Button
          size='sm'
          disabled={busy !== null || missing !== null}
          disabledReason={busy ?? missing ?? undefined}
          onClick={() => make.mutate()}
        >
          <Ghost />
          Make
        </Button>
      }
    >
      <TextField
        label='Name of the servitor'
        value={name}
        disabled={busy !== null}
        onChange={setName}
      />
      <MindPicker
        label='Role'
        value={role}
        table={table(ROLES)}
        blocked={busy}
        onPick={setRole}
      />
      <NodePicker
        label='Post'
        value={post}
        onChange={setPost}
        blocked={busy}
        types={['place', 'structure', 'settlement', 'region']}
      />
    </ForgeCard>
  )
}

function GeasCard({
  geas,
  blocked,
}: {
  geas: GeasView
  blocked: string | null
}) {
  const edit = useArcanaAction(
    'geas:edit',
    (vars: Edit) => ({ geas_id: geas.id, ...vars }),
    'The geas is set'
  )
  const breakIt = useArcanaAction(
    'geas:break',
    (_: void) => ({ geas_id: geas.id }),
    'The geas is broken'
  )
  const remove = useArcanaAction(
    'geas:delete',
    (_: void) => ({ geas_id: geas.id }),
    'The geas is lifted'
  )
  const busy = why(blocked, edit.isPending, breakIt.isPending, remove.isPending)
  const mode = GEAS_MODES[geas.mode]
  const state = GEAS_STATES[geas.state]
  const kept = geas.state === 'kept'
  return (
    <RecordRow
      icon={mode.icon}
      tone={state.tone}
      title={`${mode.label}: ${wordOf(actKindValues, geas.act)}`}
      caption={`${state.label} · laid in epoch ${geas.laid_epoch}${geas.broken_epoch !== null ? `, broken in epoch ${geas.broken_epoch}` : ''}`}
      aside={
        <div className='flex shrink-0 flex-wrap items-center gap-1'>
          <Button
            size='sm'
            variant='outline'
            disabled={busy !== null || !kept}
            disabledReason={busy ?? (kept ? undefined : 'It is already broken')}
            onClick={() => breakIt.mutate()}
          >
            <ScrollText />
            Break it
          </Button>
          <Button
            size='sm'
            variant='ghost'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => remove.mutate()}
          >
            <Trash2 />
            Lift
          </Button>
        </div>
      }
    >
      <Meter label='Favour won' value={geas.favour} tone='success' />
      <Facts
        items={[
          ['Bearer', <Ref key='bearer' node={geas.bearer} />],
          [
            'Laid by',
            <Ref
              key='layer'
              node={geas.layer_node}
              empty={GEAS_LAYERS[geas.layer].label.toLowerCase()}
            />,
          ],
          ['Last kept', `Epoch ${geas.last_kept_epoch}`],
        ]}
      />
      <RecordEditor
        title='Reshape the geas'
        note='Values you set are held against the engine until you release them.'
        fields={[
          {
            key: 'layer',
            label: 'Laid by',
            kind: 'pick',
            table: table(GEAS_LAYERS),
          },
          {
            key: 'layer_node_id',
            label: 'God or seer (id)',
            kind: 'number',
            min: 1,
          },
          {
            key: 'mode',
            label: 'Taboo or duty',
            kind: 'pick',
            table: table(GEAS_MODES),
          },
          {
            key: 'act',
            label: 'Act',
            kind: 'pick',
            table: listed(actKindValues),
          },
          {
            key: 'state',
            label: 'State',
            kind: 'pick',
            table: table(GEAS_STATES),
          },
          { key: 'favour', label: 'Favour', kind: 'number', min: 0, max: 100 },
          {
            key: 'last_kept_epoch',
            label: 'Last kept in epoch',
            kind: 'number',
            min: 0,
          },
          { key: 'laid_epoch', label: 'Laid in epoch', kind: 'number', min: 0 },
          {
            key: 'broken_epoch',
            label: 'Broken in epoch',
            kind: 'number',
            min: 0,
          },
        ]}
        locked={geas.locked}
        busy={busy}
        onSave={(values) => edit.mutate({ values, release: [] })}
        onRelease={(release) => edit.mutate({ values: {}, release })}
      />
    </RecordRow>
  )
}

function GeasForm({
  bearerId,
  blocked,
}: {
  bearerId: number
  blocked: string | null
}) {
  const [mode, setMode] = useState('')
  const [act, setAct] = useState('')
  const [layer, setLayer] = useState<number | null>(null)
  const lay = useArcanaAction(
    'geas:lay',
    (_: void) => ({
      bearer_id: bearerId,
      layer_id: layer,
      layer: 'god' as const,
      mode: mode as GeasView['mode'],
      act: act as GeasView['act'],
    }),
    'A geas is laid'
  )
  const busy = why(blocked, lay.isPending)
  const missing =
    mode === '' ? 'Choose taboo or duty' : act === '' ? 'Choose the act' : null
  return (
    <ForgeCard
      icon={ScrollText}
      tone='warning'
      title='Lay a geas'
      note='While kept it wins its god favour and dominion where the bearer lives; broken, its doom falls on the bearer.'
      columns={3}
      action={
        <Button
          size='sm'
          disabled={busy !== null || missing !== null}
          disabledReason={busy ?? missing ?? undefined}
          onClick={() => lay.mutate()}
        >
          <ScrollText />
          Lay it
        </Button>
      }
    >
      <MindPicker
        label='Taboo or duty'
        value={mode}
        table={table(GEAS_MODES)}
        blocked={busy}
        onPick={setMode}
      />
      <MindPicker
        label='Act'
        value={act}
        table={listed(actKindValues)}
        blocked={busy}
        onPick={setAct}
      />
      <NodePicker
        label='God who lays it'
        value={layer}
        onChange={setLayer}
        blocked={busy}
        kinds={GOD_KINDS}
      />
    </ForgeCard>
  )
}

function Listing<T>({
  items,
  title,
  empty,
  noun,
  keyOf,
  render,
}: {
  items: T[]
  title: string
  empty: string
  noun: [string, string]
  keyOf: (item: T) => number | string
  render: (item: T) => React.ReactNode
}) {
  return (
    <>
      <Label variant='overline'>{`${title} (${items.length})`}</Label>
      {items.length === 0 ? (
        <Muted variant='caption'>{empty}</Muted>
      ) : (
        <PagedList
          items={items}
          initial={3}
          noun={noun}
          className='flex min-w-0 flex-col gap-2'
          itemKey={keyOf}
        >
          {render}
        </PagedList>
      )}
    </>
  )
}

function MythicBody({
  data,
  type,
  blocked,
}: {
  data: NodeMythicView
  type: string | null
  blocked: string | null
}) {
  const nodeId = data.node.id
  const god = (GOD_KINDS as readonly string[]).includes(data.node.kind)
  const mortal = type === 'mortal'
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      <div className='grid min-w-0 grid-cols-2 gap-2 lg:grid-cols-4'>
        <KpiTile
          label='Heroquests'
          value={data.heroquests.length}
          icon={Footprints}
          tone='gold'
        />
        <KpiTile
          label='Servitors'
          value={data.servitors.length}
          icon={SERVANT_ICON}
          tone='verdigris'
        />
        <KpiTile
          label='Geasa'
          value={data.geasa.length + data.laid.length}
          icon={ScrollText}
          tone='warning'
        />
        <KpiTile
          label='Offices held'
          value={data.offices.length}
          icon={Landmark}
          tone='info'
        />
      </div>
      <Listing
        items={data.heroquests}
        title='Heroquests'
        empty='No heroquest walks here.'
        noun={['quest', 'quests']}
        keyOf={(row) => row.id}
        render={(row) => <QuestCard quest={row} blocked={blocked} />}
      />
      <QuestForm
        questerId={nodeId}
        blocked={
          blocked ?? (mortal ? null : 'Only a mortal undertakes a heroquest')
        }
      />
      {mortal ? (
        <MantlingCard mortalId={nodeId} row={data.mantling} blocked={blocked} />
      ) : (
        <Muted variant='caption'>
          Only a mortal walks a god's path toward godhood.
        </Muted>
      )}
      <Listing
        items={data.walkers}
        title='Mortals walking this path'
        empty='No mortal walks this path.'
        noun={['mortal', 'mortals']}
        keyOf={(row) => row.mortal?.id ?? 0}
        render={(row) => (
          <MantlingCard
            mortalId={row.mortal?.id ?? 0}
            row={row}
            blocked={blocked}
          />
        )}
      />
      {data.servitor && (
        <ServitorCard servitor={data.servitor} blocked={blocked} />
      )}
      <Listing
        items={data.servitors}
        title='Servitors'
        empty='No servitor serves here.'
        noun={['servitor', 'servitors']}
        keyOf={(row) => row.spirit?.id ?? 0}
        render={(row) => <ServitorCard servitor={row} blocked={blocked} />}
      />
      <ServitorForm
        godId={nodeId}
        blocked={blocked ?? (god ? null : 'Only a god keeps servitors')}
      />
      <Listing
        items={data.geasa}
        title='Geasa borne'
        empty='Bears no geas.'
        noun={['geas', 'geasa']}
        keyOf={(row) => row.id}
        render={(row) => <GeasCard geas={row} blocked={blocked} />}
      />
      <Listing
        items={data.laid}
        title='Geasa laid'
        empty='Has laid no geas.'
        noun={['geas', 'geasa']}
        keyOf={(row) => row.id}
        render={(row) => <GeasCard geas={row} blocked={blocked} />}
      />
      <GeasForm
        bearerId={nodeId}
        blocked={blocked ?? (mortal ? null : 'A geas is laid on a mortal')}
      />
      {god ? (
        <CosmicOfficesPanel holderId={nodeId} blocked={blocked} />
      ) : (
        <Muted variant='caption'>Cosmic offices are held by gods.</Muted>
      )}
    </div>
  )
}

export function MythicSection({
  nodeId,
  readOnlyReason = null,
}: {
  nodeId: number
  readOnlyReason?: string | null
}) {
  const query = useNodeMythic(nodeId)
  const type = useEntityType(nodeId)
  return (
    <Section
      id='section-mythic'
      title='Myth'
      description='Heroquests, the path toward godhood, divine servitors, geasa and the cosmic offices of the gods.'
      icon={MYTH_ICON}
      tone='gold'
    >
      <div data-surface='MythicSection' className='flex min-w-0 flex-col gap-3'>
        {query.isPending ? (
          <LoadingBlock label='Reading the myths' />
        ) : query.isError ? (
          <EmptyState
            icon={MYTH_ICON}
            size='inline'
            title='The myths could not be read'
            description={query.error.message}
          />
        ) : (
          <MythicBody data={query.data} type={type} blocked={readOnlyReason} />
        )}
      </div>
    </Section>
  )
}
