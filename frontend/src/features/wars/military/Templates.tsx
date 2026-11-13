import { useState } from 'react'
import {
  Archive,
  BadgeCheck,
  ClipboardList,
  History,
  PencilRuler,
  Plus,
  Swords,
  TriangleAlert,
  X,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { EmptyState, Medallion, Paged, StatBar } from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { Held, RecordButtons, TextField } from './controls'
import { type RecordRow, useRecords } from './depth'
import { useKindTable } from './kinds'
import { DOCTRINE, PERCENT, unitIcon, busyOf, cardGrid, named } from './labels'
import {
  Adjust,
  ChoiceField,
  FieldGrid,
  NumberField,
  Panel,
  Plain,
  Tag,
  ToggleField,
} from './parts'
import { type Values, useRecordActions, useRecordCreate } from './recordHooks'

type Mix = Record<string, number>

const ACTIVE = {
  label: 'In use for musters',
  icon: BadgeCheck,
  tone: 'success' as const,
}
const OUTDATED = {
  label: 'Outdated by new arms',
  icon: TriangleAlert,
  tone: 'warning' as const,
}
const RETIRED = { label: 'Set aside', icon: Archive, tone: 'muted' as const }
const DEFAULT_SHARE = 50

function mixOf(value: unknown): Mix {
  if (!value || typeof value !== 'object') return {}
  return Object.fromEntries(
    Object.entries(value as Record<string, unknown>).map(([key, share]) => [
      key,
      Number(share) || 0,
    ])
  )
}

function MixEditor({
  mix,
  onChange,
  blocked,
}: {
  mix: Mix
  onChange: (next: Mix) => void
  blocked: string | null
}) {
  const { table, specs } = useKindTable()
  const unused = specs.find((spec) => !(spec.kind in mix))
  const entries = Object.entries(mix)
  return (
    <div className='flex min-w-0 flex-col gap-2'>
      {entries.length === 0 && (
        <Muted variant='caption'>
          No kinds yet; musters would fill wholly from doctrine.
        </Muted>
      )}
      {entries.map(([kind, share]) => (
        <div key={kind} className='flex min-w-0 items-end gap-2'>
          <div className='grid min-w-0 flex-1 grid-cols-1 gap-2 @md/mil:grid-cols-2'>
            <ChoiceField
              label='Kind of soldier'
              icon={unitIcon(kind, Swords)}
              value={kind}
              table={table}
              blocked={blocked}
              onPick={(next) => {
                if (next === kind || next in mix) return
                const rest = Object.fromEntries(
                  entries.filter(([key]) => key !== kind)
                )
                onChange({ ...rest, [next]: share })
              }}
            />
            <NumberField
              label='Share'
              value={String(share)}
              onChange={(next) =>
                onChange({ ...mix, [kind]: Number(next) || 0 })
              }
            />
          </div>
          <Button
            size='icon-sm'
            variant='ghost'
            aria-label={`Drop ${named(table, kind).label}`}
            disabled={blocked !== null}
            disabledReason={blocked ?? undefined}
            onClick={() =>
              onChange(
                Object.fromEntries(entries.filter(([key]) => key !== kind))
              )
            }
          >
            <X />
          </Button>
        </div>
      ))}
      <Button
        size='sm'
        variant='outline'
        className='self-start'
        disabled={blocked !== null || !unused}
        disabledReason={
          blocked ?? (!unused ? 'Every kind is already in it' : undefined)
        }
        onClick={() =>
          unused && onChange({ ...mix, [unused.kind]: DEFAULT_SHARE })
        }
      >
        <Plus />
        Add a kind
      </Button>
    </div>
  )
}

function MixBars({ mix }: { mix: Mix }) {
  const { table } = useKindTable()
  const whole = Object.values(mix).reduce((sum, share) => sum + share, 0)
  const entries = Object.entries(mix).sort((a, b) => b[1] - a[1])
  if (entries.length === 0)
    return <Muted variant='caption'>An empty template.</Muted>
  return (
    <div className='grid min-w-0 grid-cols-1 gap-1.5 @sm/mil:grid-cols-2'>
      <Paged items={entries}>
        {([kind, share]) => {
          const item = named(table, kind)
          return (
            <StatBar
              key={kind}
              label={item.label}
              icon={item.icon}
              value={whole ? Math.round((share * PERCENT) / whole) : 0}
              max={PERCENT}
              tone='info'
            />
          )
        }}
      </Paged>
    </div>
  )
}

function TemplateCard({
  row,
  polityId,
  blocked,
}: {
  row: RecordRow
  polityId: number
  blocked: string | null
}) {
  const actions = useRecordActions('army_template', row.id, polityId)
  const [draft, setDraft] = useState<Values>({})
  const value = (key: string) => (key in draft ? draft[key] : row.values[key])
  const doctrine = named(DOCTRINE, String(row.values.doctrine))
  const active = Boolean(row.values.active)
  const outdated = Boolean(row.values.obsolete)
  const upgraded = row.values.upgraded_epoch
  return (
    <li
      data-surface='ArmyTemplate'
      className='@container/mil flex min-w-0 flex-col gap-3 rounded-xl border bg-background p-3'
    >
      <div className='flex min-w-0 items-center gap-3'>
        <Medallion
          icon={ClipboardList}
          tone={
            !active ? 'muted' : outdated ? 'warning' : (doctrine.tone ?? 'gold')
          }
        />
        <div className='flex min-w-0 flex-1 flex-col gap-0.5'>
          <Text as='span' weight='semibold' truncate>
            {String(row.values.name)}
          </Text>
          <Muted as='span' variant='caption' truncate>
            {`Drawn in epoch ${String(row.values.created_epoch)}`}
            {upgraded !== null && upgraded !== undefined
              ? ` · refitted in epoch ${String(upgraded)}`
              : ''}
          </Muted>
        </div>
        <Held locked={row.locked} />
      </div>
      <div className='flex min-w-0 flex-wrap gap-1'>
        <Tag item={doctrine} />
        <Tag item={active ? ACTIVE : RETIRED} />
        {outdated && <Tag item={OUTDATED} />}
        {upgraded !== null && upgraded !== undefined && (
          <Plain icon={History}>Refitted by the marshal</Plain>
        )}
      </div>
      <MixBars mix={mixOf(row.values.composition)} />
      <div className='mt-auto flex min-w-0 flex-col gap-2'>
        <Adjust
          title='Reshape the template'
          note='Its name, way of war, kinds of soldier and their shares; held values are never refitted by the marshal.'
        >
          <FieldGrid>
            <TextField
              label='Name'
              icon={PencilRuler}
              value={String(value('name') ?? '')}
              onChange={(next) => setDraft({ ...draft, name: next })}
            />
            <ChoiceField
              label='Way of war'
              icon={Swords}
              value={String(value('doctrine') ?? 'shieldwall')}
              table={DOCTRINE}
              blocked={blocked}
              onPick={(next) => setDraft({ ...draft, doctrine: next })}
            />
          </FieldGrid>
          <MixEditor
            mix={mixOf(value('composition'))}
            onChange={(next) => setDraft({ ...draft, composition: next })}
            blocked={blocked}
          />
          <FieldGrid>
            <ToggleField
              item={ACTIVE}
              checked={Boolean(value('active'))}
              disabled={blocked !== null}
              onChange={(next) => setDraft({ ...draft, active: next })}
            />
            <ToggleField
              item={OUTDATED}
              checked={Boolean(value('obsolete'))}
              disabled={blocked !== null}
              onChange={(next) => setDraft({ ...draft, obsolete: next })}
            />
          </FieldGrid>
          <RecordButtons
            actions={actions}
            values={draft}
            locked={row.locked}
            blocked={blocked}
            removeLabel='Tear up the template'
          />
        </Adjust>
      </div>
    </li>
  )
}

function NewTemplate({
  polityId,
  blocked,
}: {
  polityId: number
  blocked: string | null
}) {
  const create = useRecordCreate('army_template', polityId)
  const [name, setName] = useState('')
  const [doctrine, setDoctrine] = useState('shieldwall')
  const [mix, setMix] = useState<Mix>({ line_infantry: DEFAULT_SHARE })
  const busy = busyOf(blocked, create.isPending)
  const trimmed = name.trim()
  return (
    <Adjust
      title='Draw up a new template'
      note='Name the host, pick its way of war and the shares of each kind; armies raised by the realm fill from the template in use.'
      label='Draw up a template'
    >
      <FieldGrid>
        <TextField
          label='Name'
          icon={PencilRuler}
          value={name}
          onChange={setName}
        />
        <ChoiceField
          label='Way of war'
          icon={Swords}
          value={doctrine}
          table={DOCTRINE}
          blocked={blocked}
          onPick={setDoctrine}
        />
      </FieldGrid>
      <MixEditor mix={mix} onChange={setMix} blocked={blocked} />
      <Button
        size='sm'
        className='self-start'
        disabled={busy !== null || !trimmed}
        disabledReason={
          busy ?? (!trimmed ? 'Name the template first' : undefined)
        }
        onClick={() =>
          create.mutate({
            polity_entity_id: polityId,
            name: trimmed,
            doctrine,
            composition: mix,
          })
        }
      >
        <ClipboardList />
        Draw up
      </Button>
    </Adjust>
  )
}

export function ArmyTemplates({
  polityId,
  blocked,
}: {
  polityId: number
  blocked: string | null
}) {
  const templates = useRecords('army_template', polityId)
  const rows = templates.data?.rows ?? []
  return (
    <Panel
      title='Army templates'
      icon={ClipboardList}
      tone='gold'
      count={rows.length}
      hint='Named hosts its marshal keeps; raised armies fill from the one in use'
    >
      <div data-surface='ArmyTemplates' className='flex min-w-0 flex-col gap-3'>
        {templates.isPending ? (
          <Muted variant='caption'>Reading the marshal's rolls…</Muted>
        ) : templates.isError ? (
          <EmptyState
            icon={TriangleAlert}
            title='The rolls could not be read'
            description='Try again in a moment.'
          />
        ) : rows.length === 0 ? (
          <EmptyState
            icon={ClipboardList}
            title='No templates yet'
            description='Its marshal draws one the first epoch they hold office, or draw one up here.'
          />
        ) : (
          <ul className={cardGrid(rows.length)}>
            <Paged items={rows} as='li'>
              {(row) => (
                <TemplateCard
                  key={row.id}
                  row={row}
                  polityId={polityId}
                  blocked={blocked}
                />
              )}
            </Paged>
          </ul>
        )}
        <NewTemplate polityId={polityId} blocked={blocked} />
      </div>
    </Panel>
  )
}
