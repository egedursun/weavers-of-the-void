import {
  type ReactNode,
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
} from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  Baby,
  BookOpen,
  Brain,
  CalendarDays,
  Check,
  Coins,
  Database,
  Flame,
  Globe2,
  GraduationCap,
  HeartPulse,
  ImageIcon,
  Landmark,
  Link2,
  Lock,
  MessageCircle,
  Orbit,
  Pencil,
  Plus,
  Scale,
  ScrollText,
  Search,
  Shield,
  Ship,
  Sparkles,
  Swords,
  Tag,
  Trash2,
  TriangleAlert,
  type LucideIcon,
  X,
  Zap,
} from 'lucide-react'
import { postAction } from '@/api/actions'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { formatInteger } from '@/lib/format'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import { Skeleton } from '@/components/ui/skeleton'
import { Switch } from '@/components/ui/switch'
import { Textarea } from '@/components/ui/textarea'
import {
  ConfirmDialog,
  EmptyState,
  EntityLink,
  FormRow,
  KpiTile,
  Medallion,
  Paged,
  Section,
} from '@/components/domain'
import { type KpiTone } from '@/components/domain/KpiTile'
import { RecordCombobox } from '@/components/domain/RecordCombobox'
import { ShowMore } from '@/components/domain/ShowMore'
import { useShowMore } from '@/components/domain/useShowMore'
import { type DrawerKind } from '@/components/layout/drawer/drawerEntries'
import { Label, Muted, Text } from '@/components/typography'
import { useNames } from '@/features/entity/api/queries'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { loreKeys } from '../api/keys'
import {
  RECORD_LEVERS,
  type RecordFamily,
  type RowLevers,
} from './recordLevers'

type TableView = components['schemas']['ThingRecordTableView']
type ColumnView = components['schemas']['ThingRecordColumnView']
type RowView = components['schemas']['ThingRecordRowView']
type Names = Record<string, components['schemas']['ThingRecordNodeView']>
type Value =
  string | number | boolean | null | unknown[] | Record<string, unknown>
type Draft = Record<string, Value>
type RowKey = Record<string, string | number | null>
type Look = { icon: LucideIcon; tone: KpiTone; family: string }

const WORKING = 'Working on it.'
const ROWS_SHOWN = 25
const NONE = '__none__'
const LOOKS: { words: string[]; look: Look }[] = [
  {
    words: [
      'research',
      'institution',
      'great_',
      'polity_era',
      'world_era',
      'era_deed',
      'blueprint',
      'artifact_stud',
      'banned_work',
      'holder_',
    ],
    look: { icon: GraduationCap, tone: 'info', family: 'Knowledge' },
  },
  {
    words: ['bod', 'injur', 'condition', 'prosthes', 'afflict', 'maimed'],
    look: { icon: HeartPulse, tone: 'danger', family: 'Body' },
  },
  {
    words: [
      'mind',
      'memor',
      'skill',
      'trait',
      'need',
      'personality',
      'value',
      'dream',
    ],
    look: { icon: Brain, tone: 'verdigris', family: 'Mind' },
  },
  {
    words: ['bond', 'relation', 'marriage', 'member', 'oath', 'house', 'kin'],
    look: { icon: Link2, tone: 'info', family: 'Ties' },
  },
  {
    words: ['war', 'army', 'battle', 'siege', 'captive', 'feud', 'campaign'],
    look: { icon: Swords, tone: 'danger', family: 'War' },
  },
  {
    words: [
      'stock',
      'market',
      'trade',
      'goods',
      'loan',
      'treasur',
      'labour',
      'workshop',
      'resource',
      'production',
    ],
    look: { icon: Coins, tone: 'gold', family: 'Economy' },
  },
  {
    words: [
      'cult',
      'faith',
      'soul',
      'rite',
      'reverence',
      'relic',
      'heres',
      'spirit',
    ],
    look: { icon: Sparkles, tone: 'verdigris', family: 'Faith' },
  },
  {
    words: [
      'chronicle',
      'incident',
      'legend',
      'rumour',
      'language',
      'lexeme',
      'meaning',
      'tradition',
      'book',
      'thread',
    ],
    look: { icon: BookOpen, tone: 'info', family: 'Lore' },
  },
  {
    words: [
      'polity',
      'law',
      'office',
      'treaty',
      'vassal',
      'claim',
      'realm',
      'title',
      'de_jure',
    ],
    look: { icon: Landmark, tone: 'gold', family: 'Rule' },
  },
  {
    words: [
      'region',
      'place',
      'environment',
      'world',
      'star',
      'route',
      'ley',
      'species',
      'herd',
    ],
    look: { icon: Globe2, tone: 'success', family: 'Land' },
  },
]
LOOKS.push(
  {
    words: ['calendar', 'season', 'epoch', 'year', 'sky'],
    look: { icon: CalendarDays, tone: 'info', family: 'Time' },
  },
  {
    words: ['cosmos', 'creator', 'son', 'god'],
    look: { icon: Orbit, tone: 'gold', family: 'Cosmos' },
  },
  {
    words: ['event', 'happening', 'disaster', 'footprint', 'gathering'],
    look: { icon: Zap, tone: 'warning', family: 'Events' },
  },
  {
    words: ['message', 'belief', 'prayer', 'voice', 'command'],
    look: { icon: MessageCircle, tone: 'verdigris', family: 'Voices' },
  },
  {
    words: ['flag', 'tag'],
    look: { icon: Tag, tone: 'gold', family: 'Marks' },
  },
  {
    words: ['image', 'motif', 'portrait'],
    look: { icon: ImageIcon, tone: 'verdigris', family: 'Images and motifs' },
  }
)
const PLAIN_LOOK: Look = { icon: Database, tone: 'muted', family: 'Other' }
const CROWDS_LOOK: Look = { icon: Flame, tone: 'warning', family: 'Crowds' }
const MEMORY_LOOK: Look = { icon: ScrollText, tone: 'gold', family: 'Memory' }
const CUSTOMS_LOOK: Look = { icon: Scale, tone: 'verdigris', family: 'Customs' }
const PEOPLE_LOOK: Look = { icon: Baby, tone: 'info', family: 'Generations' }
const CRAFT_LOOK: Look = { icon: Ship, tone: 'info', family: 'Craft' }
const TABLE_LOOKS: Record<string, Look> = {
  crowd_moods: CROWDS_LOOK,
  cascades: CROWDS_LOOK,
  mobs: CROWDS_LOOK,
  movements: CROWDS_LOOK,
  accounts: MEMORY_LOOK,
  record_keepers: MEMORY_LOOK,
  account_stances: MEMORY_LOOK,
  memory_strikes: MEMORY_LOOK,
  founding_myths: MEMORY_LOOK,
  commemorations: MEMORY_LOOK,
  lost_lands: MEMORY_LOOK,
  storylet_runs: MEMORY_LOOK,
  dating_systems: MEMORY_LOOK,
  social_norms: CUSTOMS_LOOK,
  norm_changes: CUSTOMS_LOOK,
  learning_biases: CUSTOMS_LOOK,
  learning_events: CUSTOMS_LOOK,
  role_norms: CUSTOMS_LOOK,
  generations: PEOPLE_LOOK,
  diasporas: PEOPLE_LOOK,
  demographic_transitions: PEOPLE_LOOK,
  sex_ratios: PEOPLE_LOOK,
  arms: { icon: Shield, tone: 'gold', family: 'Arms' },
  designs: CRAFT_LOOK,
  design_components: CRAFT_LOOK,
  component_wear: CRAFT_LOOK,
  courts: { icon: Landmark, tone: 'gold', family: 'Rule' },
  credit_profiles: { icon: Coins, tone: 'gold', family: 'Economy' },
}

function lookOf(table: string): Look {
  return (
    TABLE_LOOKS[table] ??
    LOOKS.find((item) => item.words.some((word) => table.includes(word)))
      ?.look ??
    PLAIN_LOOK
  )
}

function title(name: string) {
  const plain = name.replace(/_(node|entity)_id$/, '').replace(/_id$/, '')
  return plain
    .replaceAll('_', ' ')
    .replace(/^./, (first) => first.toUpperCase())
}

function plural(count: number, noun: string) {
  return `${formatInteger(count)} ${noun}${count === 1 ? '' : 's'}`
}

function heldCount(table: TableView) {
  return table.rows.reduce((total, row) => total + row.held.length, 0)
}

function visibleColumns(table: TableView, nodeId: number) {
  return table.columns.filter(
    (column) =>
      !(
        column.owner &&
        table.rows.every((row) => row.values[column.name] === nodeId)
      )
  )
}

const LINKS = new Set([
  'entity',
  'son',
  'foreign-god',
  'creator',
  'world',
  'star',
])

function NodeCell({ value, names }: { value: unknown; names: Names }) {
  const known = typeof value === 'number' ? names[String(value)] : undefined
  if (typeof value !== 'number' || !known) return <Cell value={value} />
  return LINKS.has(known.link) ? (
    <EntityLink kind={known.link as DrawerKind} id={String(value)} showIcon>
      {known.name}
    </EntityLink>
  ) : (
    <Text as='span' truncate>
      {known.name}
    </Text>
  )
}

function empty(value: unknown) {
  return (
    value === null ||
    value === undefined ||
    value === '' ||
    (Array.isArray(value) && value.length === 0)
  )
}

function Cell({ value }: { value: unknown }) {
  if (value === null || value === undefined) return <Muted as='span'>—</Muted>
  if (typeof value === 'boolean')
    return value ? (
      <Check aria-label='yes' className='size-icon-sm text-success' />
    ) : (
      <X aria-label='no' className='size-icon-sm text-muted-foreground' />
    )
  if (typeof value === 'number')
    return (
      <Text as='span' className='tabular-nums'>
        {Number.isInteger(value) ? formatInteger(value) : value.toFixed(2)}
      </Text>
    )
  if (Array.isArray(value))
    return (
      <Badge size='sm' variant='outline'>
        {value.length === 0 ? 'Empty' : plural(value.length, 'item')}
      </Badge>
    )
  if (typeof value === 'object')
    return (
      <Badge size='sm' variant='outline'>
        {plural(Object.keys(value).length, 'field')}
      </Badge>
    )
  return (
    <Text as='span' truncate>
      {title(String(value))}
    </Text>
  )
}

function jsonText(value: Value) {
  return value === null || value === undefined
    ? ''
    : JSON.stringify(value, null, 2)
}

function RowField({
  column,
  value,
  onChange,
  disabled,
}: {
  column: ColumnView
  value: Value
  onChange: (value: Value | undefined) => void
  disabled: boolean
}) {
  const [raw, setRaw] = useState(jsonText(value))
  const label = title(column.name)
  const known = useNames(column.owner)
  const people = (known.data ?? []).map((entry) => ({
    value: String(entry.id),
    label: entry.name,
    hint: title(entry.type),
  }))
  return (
    <FormRow
      label={label}
      description={column.required ? 'Required' : undefined}
    >
      {(id) => {
        if (column.kind === 'flag')
          return (
            <Switch
              id={id}
              checked={value === true}
              disabled={disabled}
              onCheckedChange={onChange}
              aria-label={label}
            />
          )
        if (column.kind === 'choice')
          return (
            <Select
              value={
                value === null || value === undefined ? NONE : String(value)
              }
              disabled={disabled}
              onValueChange={(next) => onChange(next === NONE ? null : next)}
            >
              <SelectTrigger id={id} aria-label={label} className='w-full'>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {column.nullable && <SelectItem value={NONE}>None</SelectItem>}
                {column.options.map((option) => (
                  <SelectItem key={option} value={option}>
                    {title(option)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )
        if (column.owner && column.kind === 'integer')
          return (
            <RecordCombobox
              id={id}
              options={people}
              value={
                value === null || value === undefined ? null : String(value)
              }
              onChange={(next) =>
                onChange(
                  next === null
                    ? column.nullable
                      ? null
                      : undefined
                    : Number(next)
                )
              }
              placeholder='Choose a record'
              searchPlaceholder='Find by name'
              disabled={disabled}
              clearable={column.nullable}
              aria-label={label}
            />
          )
        if (column.kind === 'json')
          return (
            <Textarea
              id={id}
              value={raw}
              disabled={disabled}
              rows={3}
              aria-label={label}
              onChange={(event) => {
                setRaw(event.target.value)
                const text = event.target.value.trim()
                if (text === '') {
                  onChange(column.nullable ? null : undefined)
                  return
                }
                try {
                  onChange(JSON.parse(text) as Value)
                } catch {
                  onChange(undefined)
                }
              }}
            />
          )
        const numeric = column.kind === 'integer' || column.kind === 'number'
        return (
          <Input
            id={id}
            type={numeric ? 'number' : 'text'}
            step={column.kind === 'integer' ? 1 : 'any'}
            value={value === null || value === undefined ? '' : String(value)}
            disabled={disabled}
            aria-label={label}
            onChange={(event) => {
              const text = event.target.value
              if (text === '') onChange(column.nullable ? null : undefined)
              else onChange(numeric ? Number(text) : text)
            }}
          />
        )
      }}
    </FormRow>
  )
}

function changedValues(draft: Draft, row: RowView) {
  return Object.fromEntries(
    Object.entries(draft).filter(
      ([name, value]) =>
        JSON.stringify(value) !== JSON.stringify(row.values[name] ?? null)
    )
  )
}

function RowEditor({
  table,
  row,
  nodeId,
  onClose,
  blocked,
}: {
  table: TableView
  row: RowView | null
  nodeId: number
  onClose: () => void
  blocked: string | null
}) {
  const look = lookOf(table.table)
  const keys = table.columns.filter(
    (column) => column.primary && !column.editable
  )
  const fields = table.columns.filter(
    (column) => column.editable || (row === null && column.required)
  )
  const owner = table.columns.find((column) => column.owner)
  const [draft, setDraft] = useState<Draft>(() =>
    Object.fromEntries(
      fields.map((column) => [
        column.name,
        row !== null
          ? ((row.values[column.name] ?? null) as Value)
          : column.name === owner?.name
            ? nodeId
            : null,
      ])
    )
  )
  const [invalid, setInvalid] = useState<string[]>([])
  const [hold, setHold] = useState(false)
  const levers = useContext(LeversContext)(table.table)
  const save = useGodAction({
    run: () =>
      row !== null
        ? postAction(levers.edit, {
            table: table.table,
            key: row.key as RowKey,
            values: changedValues(draft, row),
            hold,
          } as never)
        : postAction(levers.create, {
            table: table.table,
            values: Object.fromEntries(
              Object.entries(draft).filter(([, value]) => value !== null)
            ),
          } as never),
    onDone: onClose,
  })
  const missing =
    row === null
      ? fields.find(
          (column) =>
            column.required &&
            (draft[column.name] === null || draft[column.name] === undefined)
        )
      : undefined
  const unchanged =
    row !== null && Object.keys(changedValues(draft, row)).length === 0
  const reason =
    blocked ??
    (save.isPending ? WORKING : null) ??
    (invalid.length > 0
      ? `Fix ${invalid.map((name) => title(name).toLowerCase()).join(', ')}.`
      : null) ??
    (missing ? `Fill in ${title(missing.name).toLowerCase()}.` : null) ??
    (unchanged ? 'Change a value first.' : null)
  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent className='max-h-dvh overflow-y-auto sm:max-w-2xl'>
        <DialogHeader>
          <div className='flex min-w-0 items-center gap-3'>
            <Medallion icon={look.icon} tone={look.tone} />
            <div className='flex min-w-0 flex-col gap-0.5'>
              <DialogTitle>
                {row !== null
                  ? `Reshape ${table.label.toLowerCase()}`
                  : `Make ${table.label.toLowerCase()}`}
              </DialogTitle>
              <DialogDescription>
                Every change goes into the ledger and can be undone.
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>
        {row !== null && keys.length > 0 && (
          <div className='flex min-w-0 flex-wrap items-center gap-1.5 rounded-md border surface-well border-gild/20 bg-muted/60 p-2'>
            <Label variant='overline'>Row</Label>
            {keys.map((column) => (
              <Badge key={column.name} size='sm' variant='outline'>
                {`${title(column.name)} ${String(row.key[column.name] ?? '')}`}
              </Badge>
            ))}
          </div>
        )}
        {fields.length === 0 ? (
          <Muted>This record has nothing to reshape by hand.</Muted>
        ) : (
          <div className='grid min-w-0 grid-cols-1 gap-4 sm:grid-cols-2'>
            {fields.map((column) => (
              <RowField
                key={column.name}
                column={column}
                value={draft[column.name] ?? null}
                disabled={save.isPending}
                onChange={(value) => {
                  setInvalid((items) =>
                    value === undefined
                      ? [...new Set([...items, column.name])]
                      : items.filter((item) => item !== column.name)
                  )
                  if (value !== undefined)
                    setDraft((current) => ({
                      ...current,
                      [column.name]: value,
                    }))
                }}
              />
            ))}
          </div>
        )}
        {row !== null && fields.length > 0 && (
          <label className='flex min-w-0 items-start gap-3 rounded-md border surface-framed border-gild/70 bg-card p-3'>
            <Switch
              checked={hold}
              onCheckedChange={setHold}
              aria-label='Hold what I set'
            />
            <div className='flex min-w-0 flex-col gap-0.5'>
              <Text as='span' weight='medium'>
                Hold what I set
              </Text>
              <Muted variant='caption'>
                The world can no longer change these values until you release
                them.
              </Muted>
            </div>
          </label>
        )}
        <DialogFooter>
          <Button size='sm' variant='ghost' onClick={onClose}>
            Cancel
          </Button>
          <Button
            size='sm'
            disabled={reason !== null}
            disabledReason={reason ?? undefined}
            onClick={() => save.mutate()}
          >
            {row !== null ? <Pencil /> : <Plus />}
            {row !== null ? 'Reshape it' : 'Make it'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function RowActions({
  table,
  row,
  onEdit,
  blocked,
}: {
  table: TableView
  row: RowView
  onEdit: () => void
  blocked: string | null
}) {
  const [confirming, setConfirming] = useState(false)
  const levers = useContext(LeversContext)(table.table)
  const remove = useGodAction({
    run: () =>
      postAction(levers.remove, {
        table: table.table,
        key: row.key as RowKey,
      } as never),
  })
  const step = levers.step
  const stepping = useGodAction({
    run: () =>
      step
        ? postAction(step.action, {
            [step.field]: (row.key as RowKey).id,
          } as never)
        : Promise.resolve(null),
  })
  const reason =
    blocked ?? (remove.isPending || stepping.isPending ? WORKING : null)
  const stepReason = reason ?? (step ? step.ready(row.values) : null)
  return (
    <div className='flex items-center justify-end gap-1'>
      {step && (
        <Button
          size='icon-sm'
          variant='ghost'
          aria-label={step.label}
          disabled={stepReason !== null}
          disabledReason={stepReason ?? undefined}
          onClick={() => stepping.mutate()}
        >
          <step.icon />
        </Button>
      )}
      <Button
        size='icon-sm'
        variant='ghost'
        aria-label='Reshape this row'
        disabled={reason !== null}
        disabledReason={reason ?? undefined}
        onClick={onEdit}
      >
        <Pencil />
      </Button>
      <Button
        size='icon-sm'
        variant='ghost'
        aria-label='Unmake this row'
        disabled={reason !== null}
        disabledReason={reason ?? undefined}
        onClick={() => setConfirming(true)}
      >
        <Trash2 />
      </Button>
      <ConfirmDialog
        open={confirming}
        onOpenChange={setConfirming}
        title='Unmake this row?'
        desc={`It leaves the ${table.label.toLowerCase()} of this thing; the ledger can bring it back.`}
        destructive
        confirmText='Unmake it'
        isLoading={remove.isPending}
        handleConfirm={() => {
          setConfirming(false)
          remove.mutate()
        }}
      />
    </div>
  )
}

function RowCard({
  table,
  row,
  index,
  columns,
  nodeId,
  names,
  onEdit,
  blocked,
}: {
  table: TableView
  row: RowView
  index: number
  columns: ColumnView[]
  nodeId: number
  names: Names
  onEdit: () => void
  blocked: string | null
}) {
  const look = lookOf(table.table)
  const keys = table.columns.filter(
    (column) =>
      column.primary &&
      !column.editable &&
      !(column.owner && row.key[column.name] === nodeId)
  )
  const shown = columns.filter(
    (column) => !(column.primary && !column.editable)
  )
  const filled = shown.filter(
    (column) =>
      !empty(row.values[column.name]) || row.held.includes(column.name)
  )
  const blank = shown.length - filled.length
  return (
    <li className='flex min-w-0 flex-col gap-3 rounded-md border surface-framed border-gild/70 bg-card p-3'>
      <div className='flex min-w-0 items-center gap-2'>
        <Medallion icon={look.icon} tone={look.tone} size='sm' />
        <Text as='span' weight='semibold'>{`Row ${index + 1}`}</Text>
        {keys.map((column) => (
          <Badge key={column.name} size='sm' variant='outline'>
            {`${title(column.name)} ${String(row.key[column.name] ?? '')}`}
          </Badge>
        ))}
        {row.held.length > 0 && (
          <Badge size='sm' variant='warning'>
            <Lock />
            {`${formatInteger(row.held.length)} held`}
          </Badge>
        )}
        <div className='ml-auto'>
          <RowActions
            table={table}
            row={row}
            onEdit={onEdit}
            blocked={blocked}
          />
        </div>
      </div>
      <dl className='grid min-w-0 grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4'>
        {filled.map((column) => {
          const held = row.held.includes(column.name)
          return (
            <div
              key={column.name}
              className={
                held
                  ? 'flex min-w-0 flex-col gap-1 rounded-md border surface-sheen border-warning/50 bg-warning/10 px-2.5 py-2'
                  : 'flex min-w-0 flex-col gap-1 rounded-md border surface-well border-gild/20 bg-muted/60 px-2.5 py-2'
              }
            >
              <Label as='dt' variant='overline' truncate>
                {title(column.name)}
              </Label>
              <dd className='flex min-w-0 items-center gap-1.5'>
                {held && (
                  <Lock
                    aria-label='held'
                    className='size-icon-xs shrink-0 text-warning'
                  />
                )}
                {column.owner ? (
                  <NodeCell value={row.values[column.name]} names={names} />
                ) : (
                  <Cell value={row.values[column.name]} />
                )}
              </dd>
            </div>
          )
        })}
      </dl>
      {blank > 0 && (
        <Muted variant='caption'>
          {`${plural(blank, 'empty field')}; reshape the row to fill ${blank === 1 ? 'it' : 'them'}.`}
        </Muted>
      )}
    </li>
  )
}

function RecordSheet({
  table,
  nodeId,
  names,
  onClose,
  blocked,
}: {
  table: TableView
  nodeId: number
  names: Names
  onClose: () => void
  blocked: string | null
}) {
  const look = lookOf(table.table)
  const columns = visibleColumns(table, nodeId)
  const [editing, setEditing] = useState<RowView | 'new' | null>(null)
  const page = useShowMore(table.rows, ROWS_SHOWN)
  return (
    <Sheet open onOpenChange={(open) => !open && onClose()}>
      <SheetContent
        side='right'
        className='flex w-full flex-col gap-4 sm:max-w-3xl'
      >
        <SheetHeader>
          <div className='flex min-w-0 items-center gap-3'>
            <Medallion icon={look.icon} tone={look.tone} />
            <div className='flex min-w-0 flex-col gap-0.5'>
              <SheetTitle>{table.label}</SheetTitle>
              <SheetDescription>
                {`${look.family} · ${plural(table.rows.length, 'row')} · ${formatInteger(heldCount(table))} held`}
              </SheetDescription>
            </div>
          </div>
        </SheetHeader>
        <div className='flex min-w-0 justify-end px-4'>
          <Button
            size='sm'
            disabled={blocked !== null}
            disabledReason={blocked ?? undefined}
            onClick={() => setEditing('new')}
          >
            <Plus />
            Make a row
          </Button>
        </div>
        <ScrollArea className='min-h-0 flex-1 px-4'>
          <ul className='flex min-w-0 flex-col gap-3 pb-4'>
            {page.visible.map((row, index) => (
              <RowCard
                key={JSON.stringify(row.key)}
                table={table}
                row={row}
                index={index}
                columns={columns}
                nodeId={nodeId}
                names={names}
                onEdit={() => setEditing(row)}
                blocked={blocked}
              />
            ))}
          </ul>
          {page.total > page.initial && (
            <div className='flex min-w-0 justify-center pb-4'>
              <ShowMore state={page} noun={['row', 'rows']} />
            </div>
          )}
        </ScrollArea>
        {editing !== null && (
          <RowEditor
            table={table}
            row={editing === 'new' ? null : editing}
            nodeId={nodeId}
            onClose={() => setEditing(null)}
            blocked={blocked}
          />
        )}
      </SheetContent>
    </Sheet>
  )
}

function KindCard({ table, onOpen }: { table: TableView; onOpen: () => void }) {
  const look = lookOf(table.table)
  const held = heldCount(table)
  return (
    <li className='min-w-0'>
      <Button
        variant='outline'
        size='tile'
        aria-label={`Open ${table.label.toLowerCase()}`}
        onClick={onOpen}
      >
        <Medallion icon={look.icon} tone={look.tone} size='sm' />
        <div className='flex min-w-0 flex-1 flex-col gap-1'>
          <Text as='span' weight='medium' truncate>
            {table.label}
          </Text>
          <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
            <Badge size='sm' variant='secondary'>
              {plural(table.rows.length, 'row')}
            </Badge>
            {held > 0 && (
              <Badge size='sm' variant='warning'>
                <Lock />
                {`${formatInteger(held)} held`}
              </Badge>
            )}
            <Muted as='span' variant='caption'>
              {look.family}
            </Muted>
          </div>
        </div>
      </Button>
    </li>
  )
}

function MakeRecord({
  tables,
  nodeId,
  blocked,
}: {
  tables: TableView[]
  nodeId: number
  blocked: string | null
}) {
  const [picked, setPicked] = useState('')
  const [open, setOpen] = useState(false)
  const table = tables.find((item) => item.table === picked)
  return (
    <div className='flex min-w-0 flex-wrap items-end gap-3 rounded-md p-3 sealed-well'>
      <Medallion icon={Plus} tone='gold' size='sm' />
      <div className='flex min-w-0 flex-1 basis-60 flex-col gap-1.5'>
        <Text as='span' weight='medium'>
          Give this thing a record it does not have
        </Text>
        <Select
          value={picked}
          onValueChange={setPicked}
          disabled={blocked !== null || tables.length === 0}
        >
          <SelectTrigger aria-label='Kind of record'>
            <SelectValue
              placeholder={
                tables.length === 0
                  ? 'It already has every kind'
                  : 'Choose a kind of record'
              }
            />
          </SelectTrigger>
          <SelectContent>
            {tables.map((item) => (
              <SelectItem key={item.table} value={item.table}>
                {`${item.label} · ${lookOf(item.table).family}`}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <Button
        size='sm'
        disabled={blocked !== null || !table}
        disabledReason={
          blocked ?? (table ? undefined : 'Choose a kind of record first.')
        }
        onClick={() => setOpen(true)}
      >
        <Plus />
        Make it
      </Button>
      {table && open && (
        <RowEditor
          table={table}
          row={null}
          nodeId={nodeId}
          onClose={() => setOpen(false)}
          blocked={blocked}
        />
      )}
    </div>
  )
}

const LeversContext = createContext<(table: string) => RowLevers>(
  () => RECORD_LEVERS
)

export function RecordRowsSection({
  nodeId,
  family,
  controls,
}: {
  nodeId: number
  family?: RecordFamily
  controls?: ReactNode
}) {
  const { reason } = useGodGate()
  const [query, setQuery] = useState('')
  const [opened, setOpened] = useState<string | null>(null)
  const view = useQuery({
    queryKey: [...loreKeys.entity(nodeId), 'record-rows'],
    queryFn: () =>
      unwrap(
        api.GET('/api/records/{node_id}/rows', {
          params: { path: { node_id: nodeId } },
        })
      ),
    retry: false,
  })
  const tables = useMemo(
    () =>
      (view.data?.tables ?? []).filter(
        (table) => !family || table.table in family.tables
      ),
    [view.data, family]
  )
  const creatable = useMemo(
    () =>
      (view.data?.creatable ?? []).filter(
        (table) => !family || table.table in family.tables
      ),
    [view.data, family]
  )
  const leversFor = useCallback(
    (table: string) => family?.tables[table] ?? RECORD_LEVERS,
    [family]
  )
  const found = useMemo(() => {
    const needle = query.trim().toLowerCase()
    if (!needle) return tables
    return tables.filter(
      (table) =>
        table.label.toLowerCase().includes(needle) ||
        lookOf(table.table).family.toLowerCase().includes(needle) ||
        table.rows.some((row) =>
          Object.values(row.values).some((value) =>
            String(value).toLowerCase().includes(needle)
          )
        )
    )
  }, [tables, query])
  const rows = tables.reduce((total, table) => total + table.rows.length, 0)
  const held = tables.reduce((total, table) => total + heldCount(table), 0)
  const open = tables.find((table) => table.table === opened) ?? null
  const present = new Set(tables.map((table) => table.table))
  return (
    <LeversContext.Provider value={leversFor}>
      <Section
        id={family ? family.section : 'section-records'}
        title={family?.title ?? 'Every record'}
        description={
          family?.description ??
          'Every typed record the world keeps about this thing. Open a kind to reshape or hold any value, unmake a row or make a new one.'
        }
        icon={family?.icon ?? Database}
        tone={family?.tone ?? 'info'}
      >
        {controls}
        {view.isError ? (
          <EmptyState
            icon={TriangleAlert}
            title='The records could not be read'
            description={view.error.message}
          />
        ) : !view.data ? (
          <div className='grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-3'>
            <Skeleton className='h-control-lg w-full' />
            <Skeleton className='h-control-lg w-full' />
            <Skeleton className='h-control-lg w-full' />
          </div>
        ) : (
          <div className='@container/records flex min-w-0 flex-col gap-4'>
            <div className='grid min-w-0 grid-cols-1 gap-3 @md/records:grid-cols-3'>
              <KpiTile
                label='Kinds of record'
                value={tables.length}
                icon={Database}
                tone='info'
              />
              <KpiTile label='Rows' value={rows} icon={BookOpen} tone='gold' />
              <KpiTile
                label='Held values'
                value={held}
                icon={Lock}
                tone={held > 0 ? 'warning' : 'muted'}
              />
            </div>
            {tables.length === 0 ? (
              <EmptyState
                icon={Database}
                title='No records yet'
                description={
                  family?.empty ??
                  'The world has written nothing about this thing yet.'
                }
              />
            ) : (
              <>
                <Input
                  type='search'
                  leadingIcon={Search}
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder='Find a kind of record or a value'
                  aria-label='Find a kind of record or a value'
                />
                {found.length === 0 ? (
                  <Muted>Nothing matches that search.</Muted>
                ) : (
                  <ul className='grid min-w-0 grid-cols-1 gap-2 @md/records:grid-cols-2 @3xl/records:grid-cols-3'>
                    <Paged items={found} as='li'>
                      {(table) => (
                        <KindCard
                          key={table.table}
                          table={table}
                          onOpen={() => setOpened(table.table)}
                        />
                      )}
                    </Paged>
                  </ul>
                )}
              </>
            )}
            <MakeRecord
              tables={creatable.filter((table) => !present.has(table.table))}
              nodeId={nodeId}
              blocked={reason()}
            />
            {open && (
              <RecordSheet
                table={open}
                nodeId={nodeId}
                names={view.data.names}
                onClose={() => setOpened(null)}
                blocked={reason()}
              />
            )}
          </div>
        )}
      </Section>
    </LeversContext.Provider>
  )
}
