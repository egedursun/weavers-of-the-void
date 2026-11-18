import { useMemo, useState } from 'react'
import {
  Feather,
  Link2,
  Pencil,
  ScrollText,
  Trash2,
  Unlink,
  UserPlus,
  Users,
  X,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { ConfirmDialog, Medallion, Paged } from '@/components/domain'
import { RecordCombobox } from '@/components/domain/RecordCombobox'
import { Label, Muted, Text } from '@/components/typography'
import { useGodAction } from '@/features/pantheon/godAction'
import { INCIDENT_ROLE } from '@/features/records/labels'
import { named } from '../environment/labels'
import { badgeVariant } from '../realm/labels'
import { NumberField, RecordField } from '../realm/parts'

type Incident = components['schemas']['IncidentRecord']
type Role = components['schemas']['IncidentRole']
type Participant = { node_id: number; role: Role; name?: string | null }

const ROLES = Object.keys(INCIDENT_ROLE) as Role[]
const BUSY = 'Another change is being applied.'

function incidentLabel(incident: Incident): string {
  const text = incident.text ?? incident.kind
  return `#${incident.id} · epoch ${incident.epoch} · ${text.length > 70 ? `${text.slice(0, 70)}…` : text}`
}

function RolePicker({
  value,
  onChange,
  label,
}: {
  value: Role
  onChange: (value: Role) => void
  label: string
}) {
  return (
    <Select value={value} onValueChange={(next) => onChange(next as Role)}>
      <SelectTrigger aria-label={label} className='w-40'>
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        {ROLES.map((role) => {
          const spec = named(INCIDENT_ROLE, role)
          const Icon = spec.icon
          return (
            <SelectItem key={role} value={role}>
              <Icon aria-hidden='true' />
              {spec.label}
            </SelectItem>
          )
        })}
      </SelectContent>
    </Select>
  )
}

export function ParticipantsEditor({
  participants,
  onChange,
  blocked,
}: {
  participants: Participant[]
  onChange: (value: Participant[]) => void
  blocked: string | null
}) {
  const [pick, setPick] = useState<number | null>(null)
  const [role, setRole] = useState<Role>('actor')
  return (
    <div className='flex min-w-0 flex-col gap-2'>
      <Label>Who took part</Label>
      {participants.length === 0 ? (
        <Muted variant='caption'>Nobody named yet.</Muted>
      ) : (
        <ul className='flex min-w-0 flex-col gap-1.5'>
          <Paged items={participants} as='li'>
            {(item, index) => {
              const spec = named(INCIDENT_ROLE, item.role)
              return (
                <li
                  key={`${item.node_id}-${item.role}`}
                  className='flex min-w-0 items-center gap-2'
                >
                  <Medallion
                    icon={spec.icon}
                    tone={spec.tone ?? 'gold'}
                    size='sm'
                  />
                  <Text as='span' className='min-w-0 flex-1' truncate>
                    {item.name ?? `Record #${item.node_id}`}
                  </Text>
                  <RolePicker
                    label='Role'
                    value={item.role}
                    onChange={(next) =>
                      onChange(
                        participants.map((other, at) =>
                          at === index ? { ...other, role: next } : other
                        )
                      )
                    }
                  />
                  <Button
                    size='sm'
                    variant='ghost'
                    aria-label='Remove participant'
                    disabled={blocked !== null}
                    disabledReason={blocked ?? undefined}
                    onClick={() =>
                      onChange(participants.filter((_, at) => at !== index))
                    }
                  >
                    <X />
                  </Button>
                </li>
              )
            }}
          </Paged>
        </ul>
      )}
      <div className='flex min-w-0 flex-wrap items-end gap-2'>
        <div className='min-w-48 flex-1'>
          <RecordField
            label='Add a record'
            types={null}
            value={pick}
            onChange={setPick}
            blocked={blocked}
          />
        </div>
        <RolePicker label='Their role' value={role} onChange={setRole} />
        <Button
          size='sm'
          variant='outline'
          disabled={pick === null || blocked !== null}
          disabledReason={
            pick === null ? 'Choose a record first.' : (blocked ?? undefined)
          }
          onClick={() => {
            if (pick === null) return
            onChange([...participants, { node_id: pick, role }])
            setPick(null)
          }}
        >
          <UserPlus />
          Add
        </Button>
      </div>
    </div>
  )
}

function CausePicker({
  incidents,
  value,
  onChange,
  exclude,
}: {
  incidents: Incident[]
  value: number | null
  onChange: (value: number | null) => void
  exclude?: number
}) {
  const options = useMemo(
    () =>
      incidents
        .filter((item) => item.id !== exclude)
        .map((item) => ({
          value: String(item.id),
          label: incidentLabel(item),
          keywords: `#${item.id} ${item.kind}`,
        })),
    [incidents, exclude]
  )
  return (
    <div className='flex min-w-0 flex-col gap-1'>
      <Label>Caused by</Label>
      <RecordCombobox
        options={options}
        value={value === null ? null : String(value)}
        onChange={(next) => onChange(next === null ? null : Number(next))}
        placeholder='Nothing recorded'
        searchPlaceholder='Find the cause'
        emptyText='No incident matches.'
        clearable
        aria-label='Caused by'
      />
    </div>
  )
}

export function IncidentForge({
  nodeId,
  incidents,
  blocked,
}: {
  nodeId: number
  incidents: Incident[]
  blocked: string | undefined
}) {
  const [text, setText] = useState('')
  const [magnitude, setMagnitude] = useState('30')
  const [year, setYear] = useState('')
  const [season, setSeason] = useState('')
  const [day, setDay] = useState('')
  const [hour, setHour] = useState('')
  const [place, setPlace] = useState<number | null>(null)
  const [origin, setOrigin] = useState<number | null>(null)
  const [destination, setDestination] = useState<number | null>(null)
  const [cause, setCause] = useState<number | null>(null)
  const [participants, setParticipants] = useState<Participant[]>([
    { node_id: nodeId, role: 'subject', name: 'This record' },
  ])
  const create = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/incident:create', {
          body: {
            text,
            kind: 'player.history',
            magnitude: Number(magnitude) || 0,
            year: year === '' ? null : Number(year),
            season: season === '' ? null : Number(season) - 1,
            day: day === '' ? null : Number(day) - 1,
            hour: hour === '' ? null : Number(hour) - 1,
            place_entity_id: place,
            origin_entity_id: origin,
            destination_entity_id: destination,
            cause_incident_id: cause,
            participants: participants.map(({ node_id, role }) => ({
              node_id,
              role,
            })),
          },
        })
      ),
    success: 'Written into history',
    onDone: () => setText(''),
  })
  const busy =
    blocked ?? (create.isPending ? 'Writing the incident.' : undefined)
  const reason =
    busy ?? (text.trim() === '' ? 'Write what happened first.' : undefined)
  return (
    <div
      data-surface='IncidentForge'
      className='@container/inc flex min-w-0 flex-col gap-3 rounded-md p-3 sealed-well'
    >
      <div className='flex min-w-0 items-center gap-2'>
        <Medallion icon={Feather} tone='gold' size='sm' />
        <div className='flex min-w-0 flex-col'>
          <Text weight='semibold'>Write an incident into history</Text>
          <Muted variant='caption'>
            Name who acted and who was struck, and what it followed from, even
            epochs ago. The chronicle, storylines and memories read it like any
            other.
          </Muted>
        </div>
      </div>
      <div className='flex min-w-0 flex-col gap-1'>
        <Label as='label' htmlFor={`incident-text-${nodeId}`}>
          What happened
        </Label>
        <Textarea
          id={`incident-text-${nodeId}`}
          value={text}
          onChange={(event) => setText(event.target.value)}
        />
      </div>
      <div className='grid min-w-0 grid-cols-1 gap-3 @lg/inc:grid-cols-3'>
        <NumberField
          label='Weight (0 to 100)'
          value={magnitude}
          min={0}
          max={100}
          blocked={busy ?? null}
          onChange={setMagnitude}
        />
        <NumberField
          label='Year'
          value={year}
          placeholder='This epoch'
          blocked={busy ?? null}
          onChange={setYear}
        />
        <CausePicker incidents={incidents} value={cause} onChange={setCause} />
        <NumberField
          label='Season (from 1)'
          value={season}
          min={1}
          max={100}
          placeholder='Not told'
          blocked={busy ?? null}
          onChange={setSeason}
        />
        <NumberField
          label='Day (from 1)'
          value={day}
          min={1}
          max={1000}
          placeholder='Not told'
          blocked={busy ?? null}
          onChange={setDay}
        />
        <NumberField
          label='Hour (from 1)'
          value={hour}
          min={1}
          max={100}
          placeholder='Not told'
          blocked={busy ?? null}
          onChange={setHour}
        />
        <RecordField
          label='Where it happened'
          types={null}
          value={place}
          onChange={setPlace}
          blocked={busy ?? null}
        />
        <RecordField
          label='Set out from'
          types={null}
          value={origin}
          onChange={setOrigin}
          blocked={busy ?? null}
        />
        <RecordField
          label='Bound for'
          types={null}
          value={destination}
          onChange={setDestination}
          blocked={busy ?? null}
        />
      </div>
      <ParticipantsEditor
        participants={participants}
        onChange={setParticipants}
        blocked={busy ?? null}
      />
      <Button
        className='self-start'
        disabled={reason !== undefined}
        disabledReason={reason}
        onClick={() => create.mutate()}
      >
        <ScrollText />
        Write it
      </Button>
    </div>
  )
}

export function IncidentControls({
  incident,
  incidents,
  blocked,
}: {
  incident: Incident
  incidents: Incident[]
  blocked: string | undefined
}) {
  const [mode, setMode] = useState<'edit' | 'roles' | 'cause' | null>(null)
  const [text, setText] = useState(incident.text ?? '')
  const [magnitude, setMagnitude] = useState(String(incident.magnitude))
  const [participants, setParticipants] = useState<Participant[]>(
    incident.participants ?? []
  )
  const [confirming, setConfirming] = useState(false)
  const edit = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/incident:edit', {
          body: {
            incident_id: incident.id,
            text: text.trim() === '' ? null : text,
            magnitude: Number(magnitude) || 0,
            clear_place: false,
            clear_origin: false,
            clear_destination: false,
          },
        })
      ),
    success: 'The incident is rewritten',
    onDone: () => setMode(null),
  })
  const roles = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/incident:roles', {
          body: {
            incident_id: incident.id,
            participants: participants.map(({ node_id, role }) => ({
              node_id,
              role,
            })),
          },
        })
      ),
    success: 'Roles set',
    onDone: () => setMode(null),
  })
  const link = useGodAction({
    run: (cause: number | null) =>
      cause === null
        ? unwrap(
            api.POST('/api/actions/incident:unlink_cause', {
              body: { incident_id: incident.id },
            })
          )
        : unwrap(
            api.POST('/api/actions/incident:link_cause', {
              body: { incident_id: incident.id, cause_incident_id: cause },
            })
          ),
  })
  const remove = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/incident:delete', {
          body: { incident_id: incident.id },
        })
      ),
    success: 'Struck from history',
  })
  const busy =
    blocked ??
    ([edit, roles, link, remove].some((item) => item.isPending)
      ? BUSY
      : undefined)
  return (
    <div className='flex min-w-0 flex-col gap-2'>
      <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
        <Paged items={incident.participants ?? []}>
          {(item) => {
            const spec = named(INCIDENT_ROLE, item.role)
            const Icon = spec.icon
            return (
              <Badge
                key={`${item.node_id}-${item.role}`}
                size='sm'
                variant={badgeVariant(spec.tone)}
              >
                <Icon aria-hidden='true' />
                {`${item.name ?? 'an unnamed record'} · ${spec.label.toLowerCase()}`}
              </Badge>
            )
          }}
        </Paged>
      </div>
      <div className='flex min-w-0 flex-wrap items-center gap-1'>
        <Button
          size='sm'
          variant='ghost'
          disabled={busy !== undefined}
          disabledReason={busy}
          onClick={() => setMode(mode === 'edit' ? null : 'edit')}
        >
          <Pencil />
          Rewrite
        </Button>
        <Button
          size='sm'
          variant='ghost'
          disabled={busy !== undefined}
          disabledReason={busy}
          onClick={() => setMode(mode === 'roles' ? null : 'roles')}
        >
          <Users />
          Roles
        </Button>
        <Button
          size='sm'
          variant='ghost'
          disabled={busy !== undefined}
          disabledReason={busy}
          onClick={() => setMode(mode === 'cause' ? null : 'cause')}
        >
          <Link2 />
          Link a cause
        </Button>
        {incident.cause_incident_id !== null ? (
          <Button
            size='sm'
            variant='ghost'
            disabled={busy !== undefined}
            disabledReason={busy}
            onClick={() => link.mutate(null)}
          >
            <Unlink />
            Cut from its cause
          </Button>
        ) : null}
        <Button
          size='sm'
          variant='ghost'
          disabled={busy !== undefined}
          disabledReason={busy}
          onClick={() => setConfirming(true)}
        >
          <Trash2 />
          Strike
        </Button>
      </div>
      {mode === 'cause' && (
        <div className='flex min-w-0 flex-col gap-2 rounded-md p-2 sealed-well'>
          <CausePicker
            incidents={incidents}
            value={incident.cause_incident_id}
            exclude={incident.id}
            onChange={(next) => {
              link.mutate(next)
              setMode(null)
            }}
          />
          <Muted variant='caption'>
            A cause may lie epochs back; it cannot come after what it caused.
          </Muted>
        </div>
      )}
      {mode === 'edit' && (
        <div className='flex min-w-0 flex-col gap-2 rounded-md p-2 sealed-well'>
          <Label as='label' htmlFor={`incident-edit-${incident.id}`}>
            What happened
          </Label>
          <Textarea
            id={`incident-edit-${incident.id}`}
            value={text}
            onChange={(event) => setText(event.target.value)}
          />
          <NumberField
            label='Weight'
            value={magnitude}
            min={0}
            max={100}
            blocked={busy ?? null}
            onChange={setMagnitude}
          />
          <Button
            size='sm'
            className='self-start'
            disabled={busy !== undefined}
            disabledReason={busy}
            onClick={() => edit.mutate()}
          >
            Save
          </Button>
        </div>
      )}
      {mode === 'roles' && (
        <div className='flex min-w-0 flex-col gap-2 rounded-md p-2 sealed-well'>
          <ParticipantsEditor
            participants={participants}
            onChange={setParticipants}
            blocked={busy ?? null}
          />
          <Button
            size='sm'
            className='self-start'
            disabled={busy !== undefined}
            disabledReason={busy}
            onClick={() => roles.mutate()}
          >
            Save roles
          </Button>
        </div>
      )}
      <ConfirmDialog
        open={confirming}
        onOpenChange={setConfirming}
        title='Strike this incident from history?'
        desc='Its chronicle line is hidden and what it caused will follow from its own cause. You can undo it from the ledger.'
        confirmText='Strike it'
        destructive
        handleConfirm={() => {
          remove.mutate()
          setConfirming(false)
        }}
      />
    </div>
  )
}
