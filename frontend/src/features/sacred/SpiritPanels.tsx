import { useState } from 'react'
import {
  Coins,
  FileText,
  Gavel,
  Gift,
  Landmark,
  Scale,
  Sparkles,
  ThumbsDown,
  ThumbsUp,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { KpiTile } from '@/components/domain'
import { table } from '@/features/arcana/labels'
import { Held, Listed } from '@/features/collective/parts'
import { Facts, ForgeCard, Meter } from '@/features/cosmography/parts'
import { YES_NO } from '@/features/cycles/labels'
import { StepButton } from '@/features/cycles/parts'
import { why } from '@/features/dominion/model'
import { NodePicker } from '@/features/dominion/parts'
import { MindPicker } from '@/features/entity/mind/parts'
import { NumberField } from '@/features/entity/realm/parts'
import { Ref } from '@/features/gatherings/parts'
import { Tag } from '@/features/wars/military/parts'
import { type SacredNodeView, useSacredAction } from './api'
import {
  OFFENCES,
  PETITION_KINDS,
  PETITION_STATUS,
  RANKS,
  SPIRIT_KINDS,
} from './labels'
import {
  GOD_KINDS,
  MANY,
  SPAN,
  SPIRIT_HOMES,
  SPIRIT_TYPES,
  TOWN_TYPES,
  useSacredRow,
  useSacredStep,
  withNone,
} from './model'
import { Bars } from './parts'

type Spirit = SacredNodeView['spirits'][number]
type Office = SacredNodeView['offices'][number]
type Petition = SacredNodeView['petitions'][number]

const JURISDICTIONS = ['settlement', 'region', 'place', 'house'] as const
const PETITIONERS = ['mortal', 'settlement'] as const
const SETTLED = 'That petition is already settled'
const OPEN = new Set(['filed', 'delayed', 'appealed'])
const ROGUE_AT = 70

function SpiritCard({ row, blocked }: { row: Spirit; blocked: string | null }) {
  const action = useSacredRow(
    'genius_locus:edit',
    'genius_locus:delete',
    { spirit_id: row.spirit.id },
    blocked
  )
  const kind = SPIRIT_KINDS[row.kind]
  const offence = row.offended ? OFFENCES[row.offended] : null
  return (
    <Held
      icon={kind.icon}
      tone={offence ? 'danger' : row.favour > 0 ? 'success' : kind.tone}
      title={row.spirit.name}
      caption={`Spirit of the ${kind.label.toLowerCase()} · dwelling since epoch ${row.bound_epoch}`}
      removeLabel='Release the place'
      editTitle='Set the place spirit'
      note='A place spirit takes offerings from its community each epoch and expects more the touchier it is. Paid in full it grows content and grants favour: food and prosperity for its town. Left unpaid, or offended by pollution of its land, the clearing of its woods or a work raised on its ground, it brings misfortune: lives lost and health worn down.'
      fields={[
        {
          key: 'place_entity_id',
          label: 'Where it dwells',
          kind: 'node',
          types: SPIRIT_HOMES,
        },
        {
          key: 'community_entity_id',
          label: 'Its community',
          kind: 'node',
          types: TOWN_TYPES,
        },
        {
          key: 'kind',
          label: 'Spirit of the',
          kind: 'pick',
          table: table(SPIRIT_KINDS),
        },
        {
          key: 'temperament',
          label: 'Temperament (touchier when higher)',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'contentment',
          label: 'Contentment',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'offerings',
          label: 'Offerings held',
          kind: 'number',
          min: 0,
          max: MANY,
        },
        {
          key: 'owed',
          label: 'Offerings owed',
          kind: 'number',
          min: 0,
          max: MANY,
        },
        { key: 'favour', label: 'Favour', kind: 'number', min: 0, max: SPAN },
        {
          key: 'offended',
          label: 'Offended by',
          kind: 'pick',
          table: withNone(table(OFFENCES), 'Nothing'),
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
      extra={offence ? <Tag item={offence} /> : <Tag item={kind} />}
    >
      <Meter
        label={`Contentment (${row.contentment} of ${SPAN})`}
        value={row.contentment}
        tone='success'
        icon={Sparkles}
      />
      <Meter
        label={`Favour (${row.favour} of ${SPAN})`}
        value={row.favour}
        tone='info'
        icon={Gift}
      />
      <Meter
        label={`Temperament (${row.temperament} of ${SPAN})`}
        value={row.temperament}
        tone='warning'
        icon={Scale}
      />
      <div className='@container/tiles min-w-0'>
        <div className='grid min-w-0 grid-cols-2 gap-2'>
          <KpiTile
            label='Offerings held'
            value={row.offerings}
            icon={Coins}
            tone='gold'
          />
          <KpiTile
            label='Offerings owed'
            value={row.owed}
            icon={Coins}
            tone={row.owed > 0 ? 'warning' : 'muted'}
          />
        </div>
      </div>
      <Facts
        items={[
          [
            'Where it dwells',
            <Ref key='place' node={row.place} empty='nowhere now' />,
          ],
          [
            'Its community',
            <Ref key='community' node={row.community} empty='none' />,
          ],
          [
            'Last offering',
            row.last_offering_epoch !== null
              ? `epoch ${row.last_offering_epoch}`
              : 'none yet',
          ],
        ]}
      />
    </Held>
  )
}

function SpiritForge({
  nodeId,
  kind,
  blocked,
}: {
  nodeId: number
  kind: string | null
  blocked: string | null
}) {
  const home = (SPIRIT_HOMES as readonly string[]).includes(kind ?? '')
  const [place, setPlace] = useState<number | null>(home ? nodeId : null)
  const [spiritKind, setSpiritKind] = useState<string>('')
  const [community, setCommunity] = useState<number | null>(
    kind === 'settlement' ? nodeId : null
  )
  const raising = useSacredAction(
    'genius_locus:create',
    (_: void) => ({
      place_id: place ?? 0,
      kind: spiritKind === '' ? null : (spiritKind as Spirit['kind']),
      community_id: community,
    }),
    'A spirit comes to dwell there'
  )
  const busy = why(
    blocked ??
      (place === null
        ? 'Choose a place, town or house for it to dwell in'
        : null),
    raising.isPending
  )
  return (
    <ForgeCard
      icon={Landmark}
      tone='success'
      title='Raise a place spirit'
      note='A spirit comes to dwell in a place, a town or a house. Its kind follows from the place unless you choose one, its community is the nearest town unless you name it, and it takes an office among the spirit offices under the god its community worships.'
      columns={3}
      action={
        <Button
          act={raising}
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => raising.mutate()}
        >
          <Landmark />
          Raise it
        </Button>
      }
    >
      <NodePicker
        label='Where it dwells'
        value={place}
        onChange={setPlace}
        blocked={blocked}
        types={SPIRIT_HOMES}
      />
      <MindPicker
        label='Spirit of the'
        value={spiritKind}
        table={table(SPIRIT_KINDS)}
        placeholder='Read from the place'
        blocked={blocked}
        onPick={setSpiritKind}
      />
      <NodePicker
        label='Its community'
        value={community}
        onChange={setCommunity}
        blocked={blocked}
        types={TOWN_TYPES}
      />
    </ForgeCard>
  )
}

export function SpiritsPanel({
  nodeId,
  kind,
  data,
  blocked,
}: {
  nodeId: number
  kind: string | null
  data: SacredNodeView
  blocked: string | null
}) {
  return (
    <div data-surface='SpiritsPanel' className='flex min-w-0 flex-col gap-4'>
      <Bars
        chart='chart-spirit-favour'
        title='Contentment and favour of each spirit'
        legend={[
          { text: 'Contentment', variant: 'success' },
          { text: 'The gold mark is its favour', variant: 'outline' },
        ]}
        rows={data.spirits.map((row) => ({
          key: row.spirit.id,
          caption: `${row.spirit.name}: contentment ${row.contentment}, favour ${row.favour}${row.offended ? `, offended by ${OFFENCES[row.offended].label.toLowerCase()}` : ''}`,
          segments: [
            {
              value: row.contentment,
              fill: row.offended ? 'fill-destructive' : 'fill-success',
            },
          ],
          mark: row.favour,
        }))}
        max={SPAN}
        noun={['spirit', 'spirits']}
        empty='No place spirit dwells here or keeps this community.'
      />
      <Listed
        title='Place spirits'
        items={data.spirits}
        empty='No place spirit dwells here or keeps this community.'
        noun={['spirit', 'spirits']}
        itemKey={(item) => item.spirit.id}
      >
        {(item) => <SpiritCard row={item} blocked={blocked} />}
      </Listed>
      <SpiritForge nodeId={nodeId} kind={kind} blocked={blocked} />
    </div>
  )
}

function OfficeCard({ row, blocked }: { row: Office; blocked: string | null }) {
  const action = useSacredRow(
    'spirit_office:edit',
    'spirit_office:delete',
    { spirit_id: row.spirit.id },
    blocked
  )
  const rank = RANKS[row.rank]
  return (
    <Held
      icon={rank.icon}
      tone={
        row.dismissed
          ? 'muted'
          : row.corruption >= ROGUE_AT
            ? 'danger'
            : rank.tone
      }
      title={row.spirit.name}
      caption={`${rank.label} office · appointed in epoch ${row.appointed_epoch}${row.dismissed ? ' · dismissed' : ''}`}
      removeLabel='Strip the office'
      editTitle='Set the spirit office'
      note='A spirit office reads the petitions of its jurisdiction after a delay that gifts shorten, grants them by its merit and gifts and denies them by its corruption. A denied petitioner may appeal to the office above. Merit promotes an office and neglected petitions demote it. Offices the overseeing god watches stay honest; unwatched ones grow corrupt and in the end answer to no one.'
      fields={[
        { key: 'rank', label: 'Rank', kind: 'pick', table: table(RANKS) },
        {
          key: 'superior_spirit_id',
          label: 'The office above',
          kind: 'node',
          types: SPIRIT_TYPES,
        },
        {
          key: 'overseer_node_id',
          label: 'Overseeing god',
          kind: 'node',
          types: [],
          kinds: GOD_KINDS,
        },
        {
          key: 'jurisdiction_entity_id',
          label: 'Jurisdiction',
          kind: 'node',
          types: JURISDICTIONS,
        },
        { key: 'merit', label: 'Merit', kind: 'number', min: 0, max: MANY },
        {
          key: 'corruption',
          label: 'Corruption',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'resolved',
          label: 'Petitions settled',
          kind: 'number',
          min: 0,
          max: MANY,
        },
        {
          key: 'neglected',
          label: 'Petitions neglected',
          kind: 'number',
          min: 0,
          max: MANY,
        },
        { key: 'dismissed', label: 'Dismissed', kind: 'pick', table: YES_NO },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
      extra={<Tag item={rank} />}
    >
      <Meter
        label={`Corruption (${row.corruption} of ${SPAN})`}
        value={row.corruption}
        tone='destructive'
        icon={Coins}
      />
      <div className='@container/tiles min-w-0'>
        <div className='grid min-w-0 grid-cols-3 gap-2'>
          <KpiTile
            label='Merit'
            value={row.merit}
            icon={Sparkles}
            tone='gold'
          />
          <KpiTile
            label='Settled'
            value={row.resolved}
            icon={ThumbsUp}
            tone='success'
          />
          <KpiTile
            label='Neglected'
            value={row.neglected}
            icon={ThumbsDown}
            tone={row.neglected > 0 ? 'warning' : 'muted'}
          />
        </div>
      </div>
      <Facts
        items={[
          [
            'The office above',
            <Ref
              key='superior'
              node={row.superior}
              empty='answers to no one'
            />,
          ],
          [
            'Overseeing god',
            <Ref key='overseer' node={row.overseer} empty='none watches it' />,
          ],
          [
            'Jurisdiction',
            <Ref key='jurisdiction' node={row.jurisdiction} empty='none' />,
          ],
        ]}
      />
    </Held>
  )
}

function PetitionCard({
  row,
  blocked,
}: {
  row: Petition
  blocked: string | null
}) {
  const action = useSacredRow(
    'petition:edit',
    'petition:delete',
    { petition_id: row.id },
    blocked
  )
  const open = OPEN.has(row.status)
  const granting = useSacredStep(
    'petition:judge',
    { petition_id: row.id, granted: true },
    open ? blocked : SETTLED,
    'The petition is granted'
  )
  const denying = useSacredStep(
    'petition:judge',
    { petition_id: row.id, granted: false },
    open ? blocked : SETTLED,
    'The petition is denied'
  )
  const kind = PETITION_KINDS[row.kind]
  const status = PETITION_STATUS[row.status]
  return (
    <Held
      icon={kind.icon}
      tone={status.tone}
      title={`${row.petitioner.name} asks for ${kind.label.toLowerCase()}`}
      caption={`${status.label} · filed in epoch ${row.filed_epoch}, due by epoch ${row.due_epoch}${row.resolved_epoch !== null ? `, settled in epoch ${row.resolved_epoch}` : ''}`}
      removeLabel='Strike the petition'
      editTitle='Set the petition'
      note='A petition waits before its office until it falls due. Granted, a petition for healing restores health, for children grants fertility, for safe passage lifts stress, for the harvest or prosperity enriches the town, for rain wets the land, for protection strengthens the town, for vengeance lays a curse on the one it names, and a suit humbles the spirit it is brought against.'
      fields={[
        {
          key: 'office_spirit_id',
          label: 'Before the office of',
          kind: 'node',
          types: SPIRIT_TYPES,
        },
        {
          key: 'kind',
          label: 'What it asks for',
          kind: 'pick',
          table: table(PETITION_KINDS),
        },
        {
          key: 'defendant_spirit_id',
          label: 'Brought against',
          kind: 'node',
          types: SPIRIT_TYPES,
        },
        {
          key: 'target_node_id',
          label: 'Vengeance sought on',
          kind: 'node',
          types: PETITIONERS,
        },
        {
          key: 'bribe',
          label: 'Offerings slipped with it',
          kind: 'number',
          min: 0,
          max: MANY,
        },
        {
          key: 'status',
          label: 'Standing',
          kind: 'pick',
          table: table(PETITION_STATUS),
        },
        {
          key: 'due_epoch',
          label: 'Due by epoch',
          kind: 'number',
          min: 0,
          max: MANY,
        },
        {
          key: 'appealed_to_id',
          label: 'Appealed to',
          kind: 'node',
          types: SPIRIT_TYPES,
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
      extra={
        <div className='flex min-w-0 flex-wrap gap-2'>
          <Tag item={status} />
          <StepButton
            icon={ThumbsUp}
            label='Grant it'
            busy={granting.busy}
            onClick={granting.run}
          />
          <StepButton
            icon={ThumbsDown}
            label='Deny it'
            busy={denying.busy}
            onClick={denying.run}
          />
        </div>
      }
    >
      <Facts
        items={[
          [
            'Petitioner',
            <Ref key='petitioner' node={row.petitioner} empty='someone' />,
          ],
          ['Before', <Ref key='office' node={row.office} empty='no office' />],
          [
            'Brought against',
            <Ref key='defendant' node={row.defendant} empty='no one' />,
          ],
          [
            'Vengeance sought on',
            <Ref key='target' node={row.target} empty='no one' />,
          ],
          [
            'Appealed to',
            <Ref key='appealed' node={row.appealed_to} empty='not appealed' />,
          ],
          ['Gifts slipped with it', String(row.bribe)],
        ]}
      />
    </Held>
  )
}

function OfficeForge({
  nodeId,
  kind,
  blocked,
}: {
  nodeId: number
  kind: string | null
  blocked: string | null
}) {
  const [spirit, setSpirit] = useState<number | null>(
    kind === 'spirit' ? nodeId : null
  )
  const [rank, setRank] = useState<keyof typeof RANKS>('local')
  const [superior, setSuperior] = useState<number | null>(null)
  const [overseer, setOverseer] = useState<number | null>(
    kind === 'son' || kind === 'foreign_god' ? nodeId : null
  )
  const [place, setPlace] = useState<number | null>(
    kind === 'settlement' ? nodeId : null
  )
  const setting = useSacredAction(
    'spirit_office:set',
    (_: void) => ({
      spirit_id: spirit ?? 0,
      rank,
      superior_id: superior,
      overseer_id: overseer,
      jurisdiction_id: place,
    }),
    'The spirit holds its office'
  )
  const busy = why(
    blocked ?? (spirit === null ? 'Choose the spirit' : null),
    setting.isPending
  )
  return (
    <ForgeCard
      icon={Scale}
      tone='gold'
      title='Set a spirit’s office'
      note='Give a spirit its rank among the offices, the office it answers to, the god that oversees it and the place it judges for.'
      columns={3}
      action={
        <Button
          act={setting}
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => setting.mutate()}
        >
          <Scale />
          Set the office
        </Button>
      }
    >
      <NodePicker
        label='Spirit'
        value={spirit}
        onChange={setSpirit}
        blocked={blocked}
        types={SPIRIT_TYPES}
      />
      <MindPicker
        label='Rank'
        value={rank}
        table={table(RANKS)}
        blocked={blocked}
        onPick={(value) => setRank(value as keyof typeof RANKS)}
      />
      <NodePicker
        label='The office above'
        value={superior}
        onChange={setSuperior}
        blocked={blocked}
        types={SPIRIT_TYPES}
      />
      <NodePicker
        label='Overseeing god'
        value={overseer}
        onChange={setOverseer}
        blocked={blocked}
        kinds={GOD_KINDS}
      />
      <NodePicker
        label='Jurisdiction'
        value={place}
        onChange={setPlace}
        blocked={blocked}
        types={JURISDICTIONS}
      />
    </ForgeCard>
  )
}

function PetitionForge({
  nodeId,
  kind,
  blocked,
}: {
  nodeId: number
  kind: string | null
  blocked: string | null
}) {
  const [petitioner, setPetitioner] = useState<number | null>(
    kind === 'mortal' || kind === 'settlement' ? nodeId : null
  )
  const [office, setOffice] = useState<number | null>(
    kind === 'spirit' ? nodeId : null
  )
  const [ask, setAsk] = useState<keyof typeof PETITION_KINDS>('healing')
  const [defendant, setDefendant] = useState<number | null>(null)
  const [wrongdoer, setWrongdoer] = useState<number | null>(null)
  const [bribe, setBribe] = useState('0')
  const filing = useSacredAction(
    'petition:create',
    (_: void) => ({
      petitioner_id: petitioner ?? 0,
      office_id: office ?? 0,
      kind: ask,
      defendant_id: ask === 'suit' ? defendant : null,
      target_id: ask === 'vengeance' ? wrongdoer : null,
      bribe: Number(bribe) || 0,
    }),
    'The petition is filed'
  )
  const busy = why(
    blocked ??
      (petitioner === null
        ? 'Choose who petitions'
        : office === null
          ? 'Choose the office it goes before'
          : ask === 'suit' && defendant === null
            ? 'A suit names the spirit it is brought against'
            : ask === 'vengeance' && wrongdoer === null
              ? 'A petition for vengeance names the wrongdoer'
              : null),
    filing.isPending
  )
  return (
    <ForgeCard
      icon={FileText}
      tone='info'
      title='File a petition'
      note='A mortal or a town petitions a spirit office. Gifts slipped with it shorten the wait and sway the office.'
      columns={3}
      action={
        <Button
          act={filing}
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => filing.mutate()}
        >
          <Gavel />
          File it
        </Button>
      }
    >
      <NodePicker
        label='Who petitions'
        value={petitioner}
        onChange={setPetitioner}
        blocked={blocked}
        types={PETITIONERS}
      />
      <NodePicker
        label='Before the office of'
        value={office}
        onChange={setOffice}
        blocked={blocked}
        types={SPIRIT_TYPES}
      />
      <MindPicker
        label='What it asks for'
        value={ask}
        table={table(PETITION_KINDS)}
        blocked={blocked}
        onPick={(value) => setAsk(value as keyof typeof PETITION_KINDS)}
      />
      <NodePicker
        label='Brought against'
        value={defendant}
        onChange={setDefendant}
        blocked={
          ask === 'suit' ? blocked : 'Only a suit is brought against a spirit'
        }
        types={SPIRIT_TYPES}
      />
      <NodePicker
        label='Vengeance sought on'
        value={wrongdoer}
        onChange={setWrongdoer}
        blocked={
          ask === 'vengeance'
            ? blocked
            : 'Only a petition for vengeance names a wrongdoer'
        }
        types={PETITIONERS}
      />
      <NumberField
        label='Offerings slipped with it'
        value={bribe}
        min={0}
        max={MANY}
        blocked={blocked}
        onChange={setBribe}
      />
    </ForgeCard>
  )
}

export function PetitionsPanel({
  nodeId,
  kind,
  data,
  blocked,
}: {
  nodeId: number
  kind: string | null
  data: SacredNodeView
  blocked: string | null
}) {
  const counts = Object.entries(PETITION_STATUS).map(([status, look]) => ({
    status,
    look,
    total: data.petitions.filter((item) => item.status === status).length,
  }))
  return (
    <div data-surface='PetitionsPanel' className='flex min-w-0 flex-col gap-4'>
      <Listed
        title='Spirit offices'
        items={data.offices}
        empty='No spirit office sits here, answers here or is overseen from here.'
        noun={['office', 'offices']}
        itemKey={(item) => item.spirit.id}
      >
        {(item) => <OfficeCard row={item} blocked={blocked} />}
      </Listed>
      <OfficeForge nodeId={nodeId} kind={kind} blocked={blocked} />
      <Bars
        chart='chart-petitions'
        title='Petitions by their standing'
        legend={[
          {
            text: 'Each bar counts the petitions in that standing',
            variant: 'outline',
          },
        ]}
        rows={counts.map((item) => ({
          key: item.status,
          caption: `${item.look.label}: ${item.total}`,
          segments: [
            {
              value: item.total,
              fill:
                item.status === 'granted'
                  ? 'fill-success'
                  : item.status === 'denied'
                    ? 'fill-destructive'
                    : 'fill-info',
            },
          ],
        }))}
        noun={['standing', 'standings']}
        empty='No petition is recorded.'
      />
      <Listed
        title='Petitions'
        items={data.petitions}
        empty='No petition was filed by, before or against this.'
        noun={['petition', 'petitions']}
        itemKey={(item) => item.id}
      >
        {(item) => <PetitionCard row={item} blocked={blocked} />}
      </Listed>
      <PetitionForge nodeId={nodeId} kind={kind} blocked={blocked} />
    </div>
  )
}
