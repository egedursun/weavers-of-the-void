import { useMemo, useState } from 'react'
import {
  BookOpen,
  Eye,
  EyeOff,
  Flag,
  Landmark,
  PenLine,
  ScrollText,
  Sparkles,
  Star,
  Trash2,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Label, Muted } from '@/components/typography'
import { table } from '@/features/arcana/labels'
import { Chip, Facts, ForgeCard, Meter } from '@/features/cosmography/parts'
import { why } from '@/features/dominion/model'
import { NodePicker } from '@/features/dominion/parts'
import { MindPicker } from '@/features/entity/mind/parts'
import { NumberField } from '@/features/entity/realm/parts'
import { Ref } from '@/features/gatherings/parts'
import { AUTHENTICITIES } from '@/features/minds/labels'
import { useNodeHistory } from '@/features/records/api'
import {
  type AccountView,
  type CollectiveView,
  useCollectiveAction,
} from './api'
import { ACCOUNT_KINDS, MEDIA, STANCES } from './labels'
import { clamp, SPAN, useRemove, useRow } from './model'
import { EventPicker, Held, Listed } from './parts'

const HAPPENINGS_SHOWN = 50
const NO_HAPPENING = 'none'

type Strike = CollectiveView['strikes'][number]
type Myth = NonNullable<CollectiveView['myth']>
type Kept = CollectiveView['commemorations'][number]
type Land = CollectiveView['lost_lands'][number]
type Stance = AccountView['stances'][number]

const HOLDERS = ['polity', 'people', 'cult', 'mortal', 'settlement']
const STRIKERS = ['polity', 'cult']
const MYTHS = ['people', 'polity']
const YES_NO = { true: 'Yes', false: 'No' }

function accountName(account: AccountView) {
  const kind = ACCOUNT_KINDS[account.kind].label
  return account.collection_name
    ? `${kind}: ${account.collection_name}`
    : `${kind}, epoch ${account.epoch}`
}

function StanceRow({
  accountId,
  row,
  blocked,
}: {
  accountId: number
  row: Stance
  blocked: string | null
}) {
  const action = useRemove(
    'account_stance:delete',
    { account_id: accountId, node_id: row.node.id },
    blocked
  )
  const stance = STANCES[row.stance]
  return (
    <div className='flex min-w-0 flex-wrap items-center gap-2'>
      <Chip icon={stance.icon}>{stance.label}</Chip>
      <Ref node={row.node} />
      <Button
        size='sm'
        variant='ghost'
        disabled={action.busy !== null}
        disabledReason={action.busy ?? undefined}
        onClick={action.onRemove}
      >
        <Trash2 />
        Drop this stance
      </Button>
    </div>
  )
}

function StanceForge({
  accountId,
  blocked,
}: {
  accountId: number
  blocked: string | null
}) {
  const [node, setNode] = useState<number | null>(null)
  const [stance, setStance] = useState<keyof typeof STANCES>('glorify')
  const setting = useCollectiveAction(
    'account_stance:set',
    (_: void) => ({ account_id: accountId, node_id: node ?? 0, stance }),
    'The account speaks of them so'
  )
  const busy = why(
    node === null ? 'Choose whom the account speaks of' : blocked,
    setting.isPending
  )
  return (
    <div className='flex min-w-0 flex-wrap items-end gap-2'>
      <NodePicker
        label='Speaks of'
        value={node}
        onChange={setNode}
        blocked={blocked}
        kinds={['son', 'world']}
        types={['mortal', 'polity', 'people', 'cult', 'house', 'settlement']}
      />
      <MindPicker
        label='How'
        value={stance}
        table={table(STANCES)}
        blocked={blocked}
        onPick={(value) => setStance(value as keyof typeof STANCES)}
      />
      <Button
        act={setting}
        size='sm'
        variant='outline'
        disabled={busy !== null}
        disabledReason={busy ?? undefined}
        onClick={() => setting.mutate()}
      >
        <PenLine />
        Write it so
      </Button>
    </div>
  )
}

function AccountCard({
  row,
  accounts,
  blocked,
}: {
  row: AccountView
  accounts: AccountView[]
  blocked: string | null
}) {
  const older = accounts.find((account) => account.id === row.revised_from_id)
  const action = useRow(
    'account:edit',
    'account:delete',
    { account_id: row.id },
    blocked
  )
  const revising = useCollectiveAction(
    'account:revise',
    (_: void) => ({ account_id: row.id, ousted_ids: [] }),
    'The account is rewritten'
  )
  const exposing = useCollectiveAction(
    'account:expose',
    (_: void) => ({ account_id: row.id }),
    'The older account comes to light'
  )
  const told = useNodeHistory(row.holder.id, {
    role: null,
    kind: null,
    limit: HAPPENINGS_SHOWN,
  })
  const happenings = useMemo(
    () => ({
      [NO_HAPPENING]: 'No single happening',
      ...Object.fromEntries(
        (told.data?.incidents ?? []).map((item) => [
          String(item.incident_id),
          item.line ?? item.kind.replaceAll('.', ' '),
        ])
      ),
    }),
    [told.data]
  )
  const kind = ACCOUNT_KINDS[row.kind]
  const medium = MEDIA[row.medium]
  const busy = why(action.busy, revising.isPending, exposing.isPending)
  const unrevised =
    row.revised_from_id === null
      ? 'Only a rewritten account has an older one to expose'
      : null
  return (
    <Held
      icon={kind.icon}
      tone={kind.tone}
      title={
        row.collection_name
          ? `${kind.label}: ${row.collection_name}`
          : kind.label
      }
      caption={`Kept by ${row.holder.name} · ${row.dated} (epoch ${row.epoch}) · ${AUTHENTICITIES[row.authenticity].label}`}
      removeLabel='Lose this account'
      editTitle='Set the account'
      note='Fidelity is how true it stays to what happened; credence is how far it is believed. Its distance from the truth adds every praise, blame and omission.'
      fields={[
        {
          key: 'fidelity',
          label: 'Fidelity',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'credence',
          label: 'Credence',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'kind',
          label: 'Kind of account',
          kind: 'pick',
          table: table(ACCOUNT_KINDS),
        },
        { key: 'medium', label: 'Kept as', kind: 'pick', table: table(MEDIA) },
        { key: 'defaced', label: 'Defaced', kind: 'pick', table: YES_NO },
        {
          key: 'authenticity',
          label: 'How genuine it is',
          kind: 'pick',
          table: table(AUTHENTICITIES),
        },
        {
          key: 'author_node_id',
          label: 'Written by',
          kind: 'node',
          types: ['mortal'],
          kinds: ['son', 'foreign_god'],
        },
        {
          key: 'incident_id',
          label: 'Happening it tells',
          kind: 'pick',
          table: happenings,
        },
        {
          key: 'subject_node_id',
          label: 'About',
          kind: 'node',
          types: [
            'mortal',
            'polity',
            'people',
            'cult',
            'house',
            'settlement',
            'army',
            'faction',
          ],
          kinds: ['son', 'foreign_god'],
        },
      ]}
      locked={row.locked}
      blocked={busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
      extra={
        <>
          <Chip icon={medium.icon}>{medium.label}</Chip>
          {row.defaced && (
            <Chip icon={EyeOff} variant='destructive'>
              Defaced
            </Chip>
          )}
          {row.revised_from_id !== null && (
            <Chip icon={PenLine} variant='warning'>
              {older
                ? `Rewrites the account of epoch ${older.epoch}`
                : 'Rewrites an older account'}
            </Chip>
          )}
        </>
      }
    >
      <div className='grid min-w-0 gap-2 sm:grid-cols-3'>
        <Meter
          label='Fidelity'
          value={row.fidelity}
          max={SPAN}
          tone='success'
          icon={BookOpen}
        />
        <Meter
          label='Credence'
          value={row.credence}
          max={SPAN}
          tone='info'
          icon={Eye}
        />
        <Meter
          label='Untruth'
          value={row.distance}
          max={SPAN}
          tone='warning'
          icon={EyeOff}
        />
      </div>
      <Facts
        items={[
          [
            'Written by',
            <Ref key='author' node={row.author} empty='no one named' />,
          ],
          [
            'Tells of',
            <Ref key='subject' node={row.subject} empty='the event itself' />,
          ],
          [
            'Carved on',
            <Ref key='structure' node={row.structure} empty='nothing' />,
          ],
          [
            'Shown in',
            <Ref key='artwork' node={row.artwork} empty='no work of art' />,
          ],
          ['Event', row.collection_name ?? 'none'],
          ['Happening', row.happening ?? 'none named'],
        ]}
      />
      <Label variant='overline'>{`How it speaks of each (${row.stances.length})`}</Label>
      {row.stances.length === 0 ? (
        <Muted variant='caption'>It names no one for praise or blame.</Muted>
      ) : (
        row.stances.map((stance) => (
          <StanceRow
            key={stance.node.id}
            accountId={row.id}
            row={stance}
            blocked={busy}
          />
        ))
      )}
      <StanceForge accountId={row.id} blocked={busy} />
      <div className='flex min-w-0 flex-wrap gap-2'>
        <Button
          act={revising}
          size='sm'
          variant='outline'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => revising.mutate()}
        >
          <PenLine />
          Rewrite it for the new reign
        </Button>
        <Button
          act={exposing}
          size='sm'
          variant='outline'
          disabled={(unrevised ?? busy) !== null}
          disabledReason={unrevised ?? busy ?? undefined}
          onClick={() => exposing.mutate()}
        >
          <Sparkles />
          Expose the older account
        </Button>
      </div>
    </Held>
  )
}

function AccountForge({
  nodeId,
  type,
  blocked,
}: {
  nodeId: number
  type: string | null
  blocked: string | null
}) {
  const [kind, setKind] =
    useState<keyof typeof ACCOUNT_KINDS>('official_chronicle')
  const [medium, setMedium] = useState<keyof typeof MEDIA>('book')
  const [event, setEvent] = useState('')
  const [fidelity, setFidelity] = useState('60')
  const holderOk = type !== null && HOLDERS.includes(type)
  const writing = useCollectiveAction(
    'account:write',
    (_: void) => ({
      holder_id: nodeId,
      kind,
      medium,
      collection_id: event ? Number(event) : null,
      subject_id: event ? null : nodeId,
      fidelity: clamp(fidelity),
    }),
    'The account is written'
  )
  const busy = why(
    holderOk
      ? blocked
      : 'Only a realm, people, cult, town or mortal keeps accounts',
    writing.isPending
  )
  return (
    <ForgeCard
      icon={ScrollText}
      tone='gold'
      title='Write an account'
      note='Have this holder tell an event, or tell of itself when no event is chosen; then set whom it praises, blames or leaves out.'
      columns={2}
      action={
        <Button
          act={writing}
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => writing.mutate()}
        >
          <ScrollText />
          Write it
        </Button>
      }
    >
      <MindPicker
        label='Kind of account'
        value={kind}
        table={table(ACCOUNT_KINDS)}
        blocked={busy}
        onPick={(value) => setKind(value as keyof typeof ACCOUNT_KINDS)}
      />
      <MindPicker
        label='Kept as'
        value={medium}
        table={table(MEDIA)}
        blocked={busy}
        onPick={(value) => setMedium(value as keyof typeof MEDIA)}
      />
      <EventPicker
        nodeId={nodeId}
        value={event}
        blocked={busy}
        onPick={setEvent}
      />
      <NumberField
        label='Fidelity'
        value={fidelity}
        min={0}
        max={SPAN}
        blocked={busy}
        onChange={setFidelity}
      />
    </ForgeCard>
  )
}

function StrikeCard({ row, blocked }: { row: Strike; blocked: string | null }) {
  const keys = { by_id: row.by.id, node_id: row.node.id }
  const action = useRow(
    'memory_strike:edit',
    'memory_strike:delete',
    keys,
    blocked
  )
  return (
    <Held
      icon={EyeOff}
      tone={row.active ? 'danger' : 'muted'}
      title={`${row.by.name} struck ${row.node.name} from memory`}
      caption={`Since epoch ${row.since_epoch}`}
      removeLabel='Restore their memory'
      editTitle='Set the strike'
      note='While a strike holds, the realm’s accounts omit them and their fame fades unless folk memory or foreigners keep it.'
      fields={[
        { key: 'active', label: 'In force', kind: 'pick', table: YES_NO },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
      extra={
        <Chip icon={row.active ? EyeOff : Eye}>
          {row.active ? 'In force' : 'Lifted'}
        </Chip>
      }
    />
  )
}

function StrikeForge({
  nodeId,
  blocked,
}: {
  nodeId: number
  blocked: string | null
}) {
  const [by, setBy] = useState<number | null>(null)
  const striking = useCollectiveAction(
    'memory_strike:set',
    (_: void) => ({ by_id: by ?? 0, node_id: nodeId }),
    'They are struck from the records'
  )
  const busy = why(
    by === null ? 'Choose the realm or cult that strikes them' : blocked,
    striking.isPending
  )
  return (
    <ForgeCard
      icon={EyeOff}
      tone='danger'
      title='Strike from memory'
      note='A realm or cult erases this figure: its accounts omit them, inscriptions are defaced and the works it made of them destroyed.'
      columns={2}
      action={
        <Button
          act={striking}
          size='sm'
          variant='destructive'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => striking.mutate()}
        >
          <EyeOff />
          Strike them
        </Button>
      }
    >
      <NodePicker
        label='Struck by'
        value={by}
        onChange={setBy}
        blocked={blocked}
        types={STRIKERS}
      />
    </ForgeCard>
  )
}

function MythCard({
  holderId,
  row,
  accounts,
  blocked,
}: {
  holderId: number
  row: Myth
  accounts: AccountView[]
  blocked: string | null
}) {
  const told = Object.fromEntries(
    accounts.map((account) => [String(account.id), accountName(account)])
  )
  const toldBy = accounts.find((account) => account.id === row.account_id)
  const action = useRow(
    'founding_myth:edit',
    'founding_myth:delete',
    { holder_id: holderId },
    blocked
  )
  const debunking = useCollectiveAction(
    'founding_myth:debunk',
    (_: void) => ({ holder_id: holderId }),
    'The founding story is shown untrue'
  )
  const done =
    row.debunked_epoch !== null ? 'It is already shown to be untrue' : null
  const busy = why(action.busy, debunking.isPending)
  return (
    <Held
      icon={Star}
      tone={row.debunked_epoch !== null ? 'muted' : 'gold'}
      title={`The founding story of ${row.holder.name}`}
      caption={
        row.debunked_epoch !== null
          ? `Shown untrue in epoch ${row.debunked_epoch}`
          : `Told since epoch ${row.since_epoch}`
      }
      removeLabel='Let it be told anew'
      editTitle='Set the founding myth'
      note='Its credence lends cohesion and legitimacy; shown untrue, it costs both.'
      fields={[
        {
          key: 'credence',
          label: 'Credence',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'account_id',
          label: 'Told in the account',
          kind: 'pick',
          table: { none: 'No written account', ...told },
        },
      ]}
      locked={row.locked}
      blocked={busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
      extra={
        toldBy ? (
          <Chip icon={ScrollText}>{accountName(toldBy)}</Chip>
        ) : undefined
      }
    >
      <Meter
        label='Credence'
        value={row.credence}
        max={SPAN}
        tone='success'
        icon={Star}
      />
      <Button
        act={debunking}
        size='sm'
        variant='outline'
        disabled={(done ?? busy) !== null}
        disabledReason={done ?? busy ?? undefined}
        onClick={() => debunking.mutate()}
      >
        <EyeOff />
        Show it untrue
      </Button>
    </Held>
  )
}

function MythForge({
  holderId,
  type,
  blocked,
}: {
  holderId: number
  type: string | null
  blocked: string | null
}) {
  const [credence, setCredence] = useState('70')
  const setting = useCollectiveAction(
    'founding_myth:set',
    (_: void) => ({ holder_id: holderId, credence: clamp(credence) }),
    'The founding story is told'
  )
  const busy = why(
    type !== null && MYTHS.includes(type)
      ? blocked
      : 'Only a people or realm has a founding story',
    setting.isPending
  )
  return (
    <ForgeCard
      icon={Star}
      tone='gold'
      title='Tell a founding story'
      note='Give this people or realm a founding account and set how firmly it is believed.'
      columns={2}
      action={
        <Button
          act={setting}
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => setting.mutate()}
        >
          <Star />
          Tell it
        </Button>
      }
    >
      <NumberField
        label='Credence'
        value={credence}
        min={0}
        max={SPAN}
        blocked={busy}
        onChange={setCredence}
      />
    </ForgeCard>
  )
}

function KeptCard({ row, blocked }: { row: Kept; blocked: string | null }) {
  const keys = { holder_id: row.holder.id, collection_id: row.collection_id }
  const action = useRow(
    'commemoration:edit',
    'commemoration:delete',
    keys,
    blocked
  )
  const reliving = useCollectiveAction(
    'commemoration:relive',
    (_: void) => keys,
    'The anniversary is kept'
  )
  const busy = why(action.busy, reliving.isPending)
  return (
    <Held
      icon={row.pride ? Landmark : Flag}
      tone={row.pride ? 'gold' : 'danger'}
      title={`${row.pride ? 'Celebrates' : 'Mourns'} ${row.collection_name}`}
      caption={
        row.last_observed_epoch !== null
          ? `Last kept in epoch ${row.last_observed_epoch}`
          : `Remembered since epoch ${row.since_epoch}`
      }
      removeLabel='Forget it'
      editTitle='Set the anniversary'
      note='A kept anniversary of pride lends order; of grief, it keeps the grievance and stirs unrest. Neglected, it fades.'
      fields={[
        {
          key: 'strength',
          label: 'Strength',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'pride',
          label: 'Pride, not grief',
          kind: 'pick',
          table: YES_NO,
        },
      ]}
      locked={row.locked}
      blocked={busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    >
      <Meter
        label='Strength of the memory'
        value={row.strength}
        max={SPAN}
        tone='warning'
        icon={Landmark}
      />
      <Button
        act={reliving}
        size='sm'
        variant='outline'
        disabled={busy !== null}
        disabledReason={busy ?? undefined}
        onClick={() => reliving.mutate()}
      >
        <Sparkles />
        Keep it now
      </Button>
    </Held>
  )
}

function KeptForge({
  nodeId,
  blocked,
}: {
  nodeId: number
  blocked: string | null
}) {
  const [event, setEvent] = useState('')
  const [pride, setPride] = useState('true')
  const setting = useCollectiveAction(
    'commemoration:set',
    (_: void) => ({
      holder_id: nodeId,
      collection_id: Number(event),
      pride: pride === 'true',
    }),
    'The anniversary will be kept'
  )
  const busy = why(
    event ? blocked : 'Choose an event to remember',
    setting.isPending
  )
  return (
    <ForgeCard
      icon={Landmark}
      tone='gold'
      title='Keep an anniversary'
      note='Make this holder relive an event with pride or grief every few epochs.'
      columns={2}
      action={
        <Button
          act={setting}
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => setting.mutate()}
        >
          <Landmark />
          Keep it
        </Button>
      }
    >
      <EventPicker
        nodeId={nodeId}
        value={event}
        blocked={blocked}
        onPick={setEvent}
      />
      <MindPicker
        label='Pride, not grief'
        value={pride}
        table={YES_NO}
        blocked={blocked}
        onPick={setPride}
      />
    </ForgeCard>
  )
}

function LandCard({ row, blocked }: { row: Land; blocked: string | null }) {
  const keys = { claimant_id: row.claimant.id, region_id: row.region.id }
  const action = useRow('lost_land:edit', 'lost_land:delete', keys, blocked)
  return (
    <Held
      icon={Flag}
      tone={row.claimed_epoch !== null ? 'danger' : 'warning'}
      title={`${row.claimant.name} remembers ${row.region.name}`}
      caption={`Lost in epoch ${row.lost_epoch}${row.claimed_epoch !== null ? ` · claimed back in epoch ${row.claimed_epoch}` : ''}`}
      removeLabel='Forget the land'
      editTitle='Set the memory'
      note='A strong memory of a lost land becomes a claim and a cause for war; anniversaries keep it alive.'
      fields={[
        {
          key: 'strength',
          label: 'Strength',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'claimed_epoch',
          label: 'Claimed back in epoch',
          kind: 'number',
          min: 0,
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    >
      <Meter
        label='Strength of the memory'
        value={row.strength}
        max={SPAN}
        tone='destructive'
        icon={Flag}
      />
    </Held>
  )
}

function LandForge({
  nodeId,
  type,
  blocked,
}: {
  nodeId: number
  type: string | null
  blocked: string | null
}) {
  const [region, setRegion] = useState<number | null>(null)
  const [strength, setStrength] = useState('70')
  const setting = useCollectiveAction(
    'lost_land:set',
    (_: void) => ({
      claimant_id: nodeId,
      region_id: region ?? 0,
      strength: clamp(strength),
    }),
    'The lost land is remembered'
  )
  const busy = why(
    type !== 'polity'
      ? 'Only a realm remembers its lost lands'
      : region === null
        ? 'Choose the land it lost'
        : blocked,
    setting.isPending
  )
  return (
    <ForgeCard
      icon={Flag}
      tone='warning'
      title='Remember a lost land'
      note='Make this realm mourn a region it once held; strong enough, it claims it back.'
      columns={2}
      action={
        <Button
          act={setting}
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => setting.mutate()}
        >
          <Flag />
          Remember it
        </Button>
      }
    >
      <NodePicker
        label='Land'
        value={region}
        onChange={setRegion}
        blocked={blocked}
        types={['region']}
      />
      <NumberField
        label='Strength'
        value={strength}
        min={0}
        max={SPAN}
        blocked={blocked}
        onChange={setStrength}
      />
    </ForgeCard>
  )
}

export function HistoryPanel({
  nodeId,
  type,
  data,
  blocked,
}: {
  nodeId: number
  type: string | null
  data: CollectiveView
  blocked: string | null
}) {
  return (
    <div
      id='section-collective-history'
      data-surface='HistoryPanel'
      className='flex min-w-0 flex-col gap-3'
    >
      <Label variant='overline'>Accounts and memory</Label>
      <Listed
        title='Accounts'
        items={data.accounts}
        empty='No account tells of this.'
        noun={['account', 'accounts']}
        itemKey={(row) => row.id}
      >
        {(row) => (
          <AccountCard row={row} accounts={data.accounts} blocked={blocked} />
        )}
      </Listed>
      <AccountForge nodeId={nodeId} type={type} blocked={blocked} />
      <Listed
        title='Struck memories'
        items={data.strikes}
        empty='No memory is struck here.'
        noun={['strike', 'strikes']}
        itemKey={(row) => `${row.node.id}-${row.by.id}`}
      >
        {(row) => <StrikeCard row={row} blocked={blocked} />}
      </Listed>
      <StrikeForge nodeId={nodeId} blocked={blocked} />
      {data.myth ? (
        <MythCard
          holderId={nodeId}
          row={data.myth}
          accounts={data.accounts}
          blocked={blocked}
        />
      ) : (
        <MythForge holderId={nodeId} type={type} blocked={blocked} />
      )}
      <Listed
        title='Anniversaries'
        items={data.commemorations}
        empty='No anniversary is kept here.'
        noun={['anniversary', 'anniversaries']}
        itemKey={(row) => `${row.holder.id}-${row.collection_id}`}
      >
        {(row) => <KeptCard row={row} blocked={blocked} />}
      </Listed>
      <KeptForge nodeId={nodeId} blocked={blocked} />
      <Listed
        title='Lost lands'
        items={data.lost_lands}
        empty='No lost land is remembered here.'
        noun={['land', 'lands']}
        itemKey={(row) => `${row.claimant.id}-${row.region.id}`}
      >
        {(row) => <LandCard row={row} blocked={blocked} />}
      </Listed>
      <LandForge nodeId={nodeId} type={type} blocked={blocked} />
    </div>
  )
}
