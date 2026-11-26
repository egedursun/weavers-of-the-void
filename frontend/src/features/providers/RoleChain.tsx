import { useId, useState } from 'react'
import {
  ArrowDown,
  ArrowUp,
  CircleCheck,
  CircleHelp,
  CircleX,
  CloudCog,
  Eye,
  EyeOff,
  List,
  ListRestart,
  LoaderCircle,
  Plus,
  Save,
  ScanSearch,
  Trash2,
  ImageOff,
  ImagePlus,
  TriangleAlert,
} from 'lucide-react'
import { toast } from 'sonner'
import { formatSince } from '@/lib/format'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Medallion, ShowMore, useShowMore } from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { useCheckChain, useConnectionModels, useSetChain } from './api'
import { ROLE_LOOK } from './providerLook'
import {
  type ChainEntry,
  type ChainLink,
  type ModelRole,
  type ProviderConnection,
  type ProviderKindView,
  type ProviderScope,
  type RoleView,
} from './types'

const MODEL_MAX = 200
const CHAIN_SHOWN = 12

function DrawingBadge({ entry }: { entry: ChainEntry }) {
  if (entry.tools_work === null)
    return (
      <Badge variant='outline' size='sm'>
        <CircleHelp />
        Not checked yet
      </Badge>
    )
  return entry.tools_work ? (
    <Badge variant='success' size='sm'>
      <ImagePlus />
      Draws pictures
    </Badge>
  ) : (
    <Badge variant='destructive' size='sm'>
      <ImageOff />
      Skipped: drew no picture
    </Badge>
  )
}

function CheckBadges({
  entry,
  pictures,
  drawing,
}: {
  entry: ChainEntry | null
  pictures: boolean
  drawing: boolean
}) {
  if (entry === null)
    return (
      <Badge variant='outline' size='sm'>
        <CircleHelp />
        Not saved yet
      </Badge>
    )
  return (
    <span className='flex min-w-0 flex-wrap items-center gap-1.5'>
      {drawing ? (
        <DrawingBadge entry={entry} />
      ) : entry.tools_work === null ? (
        <Badge variant='outline' size='sm'>
          <CircleHelp />
          Not checked yet
        </Badge>
      ) : entry.tools_work ? (
        <Badge variant='success' size='sm'>
          <CircleCheck />
          Uses tools
        </Badge>
      ) : (
        <Badge variant='destructive' size='sm'>
          <CircleX />
          Skipped: failed the check
        </Badge>
      )}
      {pictures && entry.sees_images !== null && (
        <Badge variant={entry.sees_images ? 'success' : 'warning'} size='sm'>
          {entry.sees_images ? <Eye /> : <EyeOff />}
          {entry.sees_images ? 'Sees pictures' : 'Does not see pictures'}
        </Badge>
      )}
      {entry.checked_at && (
        <Muted as='span' variant='caption'>
          {`Checked ${formatSince(entry.checked_at)}`}
        </Muted>
      )}
    </span>
  )
}

function ChainRow({
  scope,
  role,
  position,
  link,
  saved,
  choices,
  kinds,
  pictures,
  locked,
  lockReason,
  first,
  last,
  onChange,
  onMove,
  onRemove,
}: {
  scope: ProviderScope
  role: ModelRole
  position: number
  link: ChainLink
  saved: ChainEntry | null
  choices: ProviderConnection[]
  kinds: Map<string, ProviderKindView>
  pictures: boolean
  locked: boolean
  lockReason: string
  first: boolean
  last: boolean
  onChange: (link: ChainLink) => void
  onMove: (step: number) => void
  onRemove: () => void
}) {
  const listId = useId()
  const [asked, setAsked] = useState(false)
  const models = useConnectionModels(scope, link.connection_id, role, asked)
  const chosen = choices.find((item) => item.id === link.connection_id)
  const worker = chosen
    ? kinds.get(chosen.kind)?.kind === 'image_worker'
    : false
  return (
    <li className='flex min-w-0 flex-col gap-2 rounded-md surface-sheen px-3 py-2.5'>
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Badge variant='secondary' size='sm' className='tabular-nums'>
          {position + 1}
        </Badge>
        <Select
          value={String(link.connection_id)}
          disabled={locked}
          onValueChange={(value) =>
            onChange({ connection_id: Number(value), model: '' })
          }
        >
          <SelectTrigger
            size='sm'
            aria-label={`Connection of entry ${position + 1}`}
            title={locked ? lockReason : undefined}
            className='min-w-0 flex-1 basis-48'
          >
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {choices.map((item) => (
              <SelectItem key={item.id} value={String(item.id)}>
                {item.from_server ? <CloudCog aria-hidden='true' /> : null}
                {item.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Input
          aria-label={`Model of entry ${position + 1}`}
          value={link.model}
          maxLength={MODEL_MAX}
          list={listId}
          disabled={locked || worker}
          title={
            worker
              ? 'The local worker draws with the model it was started with.'
              : locked
                ? lockReason
                : undefined
          }
          placeholder={worker ? 'Its own model' : 'Model name'}
          className='min-w-0 flex-1 basis-48'
          onChange={(event) =>
            onChange({
              connection_id: link.connection_id,
              model: event.target.value,
            })
          }
        />
        <datalist id={listId}>
          {(models.data?.models ?? []).map((model) => (
            <option key={model} value={model} />
          ))}
        </datalist>
        {!worker && (
          <Button
            type='button'
            variant='ghost'
            size='icon-sm'
            aria-label={`List the models of ${chosen?.label ?? 'this connection'}`}
            disabled={locked || models.isFetching}
            disabledReason={locked ? lockReason : 'Asking for the models.'}
            onClick={() => {
              if (asked) void models.refetch()
              else setAsked(true)
            }}
          >
            {models.isFetching ? (
              <LoaderCircle className='animate-spin motion-reduce:animate-none' />
            ) : (
              <List />
            )}
          </Button>
        )}
        <Button
          type='button'
          variant='ghost'
          size='icon-sm'
          aria-label={`Move entry ${position + 1} up`}
          disabled={locked || first}
          disabledReason={first ? 'It is already tried first.' : lockReason}
          onClick={() => onMove(-1)}
        >
          <ArrowUp />
        </Button>
        <Button
          type='button'
          variant='ghost'
          size='icon-sm'
          aria-label={`Move entry ${position + 1} down`}
          disabled={locked || last}
          disabledReason={last ? 'It is already tried last.' : lockReason}
          onClick={() => onMove(1)}
        >
          <ArrowDown />
        </Button>
        <Button
          type='button'
          variant='ghost'
          size='icon-sm'
          aria-label={`Remove entry ${position + 1}`}
          disabled={locked}
          disabledReason={lockReason}
          onClick={onRemove}
        >
          <Trash2 />
        </Button>
      </div>
      <CheckBadges
        entry={saved}
        pictures={pictures}
        drawing={role === 'images'}
      />
      {saved?.check_note && (
        <Muted as='span' variant='caption'>
          {saved.check_note}
        </Muted>
      )}
      {models.isSuccess && models.data.models.length === 0 && (
        <Muted as='span' variant='caption'>
          {role === 'images'
            ? 'The provider listed no picture models for this key; type the model name.'
            : 'The provider listed no models for this key; type the model name.'}
        </Muted>
      )}
      {models.isError && (
        <Muted as='span' variant='caption' className='text-warning'>
          {`The models could not be listed: ${models.error.message}`}
        </Muted>
      )}
    </li>
  )
}

function linksOf(entries: ChainEntry[]): ChainLink[] {
  return entries.map((entry) => ({
    connection_id: entry.connection_id,
    model: entry.model,
  }))
}

function same(first: ChainLink[], second: ChainLink[]): boolean {
  return (
    first.length === second.length &&
    first.every(
      (link, index) =>
        link.connection_id === second[index].connection_id &&
        link.model.trim() === second[index].model
    )
  )
}

export function RoleChain({
  scope,
  role,
  connections,
  kinds,
  editable,
  readOnlyReason,
}: {
  scope: ProviderScope
  role: RoleView
  connections: ProviderConnection[]
  kinds: Map<string, ProviderKindView>
  editable: boolean
  readOnlyReason: string
}) {
  const save = useSetChain(scope)
  const check = useCheckChain(scope)
  const [draft, setDraft] = useState<ChainLink[]>(() => linksOf(role.entries))
  const page = useShowMore(draft, CHAIN_SHOWN)
  const serverPage = useShowMore(role.server_entries, CHAIN_SHOWN)
  const look = ROLE_LOOK[role.role]
  const pictures = role.role === 'conversation'
  const choices = connections.filter((item) =>
    kinds.get(item.kind)?.roles.includes(role.role)
  )
  const dirty = !same(draft, role.entries)
  const named = (id: number) =>
    connections.find((item) => item.id === id)?.label ?? 'A removed connection'
  const savedOf = (link: ChainLink) =>
    role.entries.find(
      (entry) =>
        entry.connection_id === link.connection_id &&
        entry.model === link.model.trim()
    ) ?? null
  const locked = !editable
  const missingModel = draft.some((link) => {
    const kind = kinds.get(
      connections.find((item) => item.id === link.connection_id)?.kind ?? ''
    )
    return kind?.kind !== 'image_worker' && link.model.trim() === ''
  })
  const saveReason = locked
    ? readOnlyReason
    : missingModel
      ? 'Every entry needs the name of its model.'
      : 'Saving the chain.'
  const checkReason = locked ? readOnlyReason : 'Checking every model.'
  const update = (index: number, link: ChainLink) =>
    setDraft((items) => items.map((item, at) => (at === index ? link : item)))
  const move = (index: number, step: number) =>
    setDraft((items) => {
      const next = [...items]
      const target = index + step
      ;[next[index], next[target]] = [next[target], next[index]]
      return next
    })
  return (
    <section
      aria-label={role.label}
      className='flex min-w-0 flex-col gap-3 rounded-md border surface-framed border-gild/60 bg-card p-3'
    >
      <div className='flex min-w-0 flex-wrap items-center gap-3'>
        <Medallion icon={look.icon} tone={look.tone} size='sm' />
        <div className='flex min-w-0 flex-1 basis-40 flex-col'>
          <Text as='span' weight='semibold'>
            {role.label}
          </Text>
          <Muted as='span' variant='caption'>
            {role.description}
          </Muted>
        </div>
        {draft.length === 0 && role.server_entries.length > 0 && (
          <Badge variant='info' size='sm'>
            <CloudCog />
            Uses the server default
          </Badge>
        )}
        {draft.length === 0 && role.server_entries.length === 0 && (
          <Badge variant='warning' size='sm'>
            <TriangleAlert />
            No model
          </Badge>
        )}
      </div>
      {draft.length > 0 ? (
        <>
          <ol
            aria-label={`Models for ${role.label}, tried in order`}
            className='flex min-w-0 flex-col gap-2'
          >
            {page.visible.map((link, index) => (
              <ChainRow
                key={`${index}-${link.connection_id}`}
                scope={scope}
                role={role.role}
                position={index}
                link={link}
                saved={savedOf(link)}
                choices={choices}
                kinds={kinds}
                pictures={pictures}
                locked={locked}
                lockReason={readOnlyReason}
                first={index === 0}
                last={index === draft.length - 1}
                onChange={(next) => update(index, next)}
                onMove={(step) => move(index, step)}
                onRemove={() =>
                  setDraft((items) => items.filter((_, at) => at !== index))
                }
              />
            ))}
          </ol>
          <ShowMore state={page} noun={['model', 'models']} />
        </>
      ) : role.server_entries.length > 0 ? (
        <>
          <ul
            aria-label={`Server models for ${role.label}`}
            className='flex min-w-0 flex-col gap-1.5 rounded-md p-3 sealed-well'
          >
            {serverPage.visible.map((entry, index) => (
              <li key={entry.id} className='flex min-w-0 items-center gap-2'>
                <Badge variant='secondary' size='sm' className='tabular-nums'>
                  {index + 1}
                </Badge>
                <Text as='span' truncate>
                  {entry.model
                    ? `${entry.model} · ${named(entry.connection_id)}`
                    : named(entry.connection_id)}
                </Text>
              </li>
            ))}
          </ul>
          <ShowMore state={serverPage} noun={['model', 'models']} />
        </>
      ) : (
        <Muted variant='caption' className='rounded-md p-3 sealed-well'>
          {`${scope === 'server' ? 'No model serves this role yet' : 'Neither this workspace nor the server has a model for this role'}, so what needs it waits. ${choices.length > 0 ? 'Add one below.' : 'Connect a provider that serves it first.'}`}
        </Muted>
      )}
      <div className='flex min-w-0 flex-wrap items-center justify-between gap-2'>
        <span className='flex min-w-0 flex-wrap items-center gap-2'>
          <Button
            type='button'
            variant='outline'
            disabled={locked || choices.length === 0}
            disabledReason={
              locked
                ? readOnlyReason
                : 'Connect a provider that serves this role first.'
            }
            onClick={() =>
              setDraft((items) => [
                ...items,
                { connection_id: choices[0].id, model: '' },
              ])
            }
          >
            <Plus />
            Add a model
          </Button>
          {dirty && (
            <Button
              type='button'
              variant='ghost'
              onClick={() => setDraft(linksOf(role.entries))}
            >
              <ListRestart />
              Undo the changes
            </Button>
          )}
        </span>
        <span className='flex min-w-0 flex-wrap items-center gap-2'>
          {!dirty && role.entries.length > 0 && (
            <Button
              act={check}
              type='button'
              variant='outline'
              disabled={locked || check.isPending}
              disabledReason={checkReason}
              onClick={() =>
                check.mutate(role.role, {
                  onSuccess: () => toast.success(`${role.label} is checked`),
                  onError: (error) => toast.error(error.message),
                })
              }
            >
              {check.isPending ? (
                <LoaderCircle className='animate-spin motion-reduce:animate-none' />
              ) : (
                <ScanSearch />
              )}
              Check the models
            </Button>
          )}
          {dirty && (
            <Button
              act={save}
              type='button'
              disabled={locked || missingModel || save.isPending}
              disabledReason={saveReason}
              onClick={() =>
                save.mutate(
                  {
                    role: role.role,
                    entries: draft.map((link) => ({
                      connection_id: link.connection_id,
                      model: link.model.trim(),
                    })),
                  },
                  {
                    onSuccess: () => toast.success(`${role.label} is saved`),
                    onError: (error) => toast.error(error.message),
                  }
                )
              }
            >
              {save.isPending ? (
                <LoaderCircle className='animate-spin motion-reduce:animate-none' />
              ) : (
                <Save />
              )}
              Save the chain
            </Button>
          )}
        </span>
      </div>
    </section>
  )
}
