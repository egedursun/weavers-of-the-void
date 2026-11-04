import { useState } from 'react'
import {
  Ban,
  Biohazard,
  Crosshair,
  Gem,
  Pin,
  Plus,
  RotateCcw,
  Save,
  ShieldCheck,
  Sparkles,
  Trash2,
  Unlock,
} from 'lucide-react'
import { speciesUseValues } from '@/api/generated/schema'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Switch } from '@/components/ui/switch'
import { EmptyState, Medallion, Paged } from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { EntityPicker } from '@/features/cosmos/EntityPicker'
import { busyOf } from '../lore/model'
import { MindPicker } from '../mind/parts'
import {
  type SpeciesCard,
  type UseKind,
  useUseKinds,
  useWildAction,
} from './api'
import { USE, named } from './labels'
import { Group, Name, NumberField, type Ref } from './parts'
import { type Link, linkOf } from './wildsModel'

type Blocked = { id: number; card: SpeciesCard; blocked: string | null }

const LINKS: Record<
  Link,
  { label: string; badge: 'default' | 'destructive' | 'secondary' }
> = {
  pinned: { label: 'Held by you', badge: 'default' },
  barred: { label: 'Forbidden', badge: 'destructive' },
  derived: { label: 'By nature', badge: 'secondary' },
}

export function LinkBadge({ link }: { link: Link }) {
  const spec = LINKS[link]
  return (
    <Badge size='sm' variant={spec.badge}>
      {link === 'pinned' ? (
        <Pin />
      ) : link === 'barred' ? (
        <Ban />
      ) : (
        <Crosshair />
      )}
      {spec.label}
    </Badge>
  )
}

function PreyRow({
  prey,
  link,
  busy,
  onSet,
}: {
  prey: Ref
  link: Link
  busy: string | null
  onSet: (link: Link) => void
}) {
  return (
    <li className='flex min-w-0 flex-wrap items-center gap-2 rounded-lg border bg-muted/30 p-2'>
      <Medallion
        icon={link === 'barred' ? Ban : link === 'pinned' ? Pin : Crosshair}
        tone={
          link === 'barred' ? 'danger' : link === 'pinned' ? 'gold' : 'muted'
        }
        size='sm'
      />
      <div className='flex min-w-0 flex-1 flex-col gap-1'>
        <Name item={prey} />
        <LinkBadge link={link} />
      </div>
      <div className='flex flex-wrap gap-1'>
        <Button
          size='sm'
          variant={link === 'pinned' ? 'default' : 'outline'}
          disabled={busy !== null || link === 'pinned'}
          disabledReason={busy ?? undefined}
          onClick={() => onSet('pinned')}
        >
          <Pin />
          Hunt it always
        </Button>
        <Button
          size='sm'
          variant={link === 'barred' ? 'destructive' : 'outline'}
          disabled={busy !== null || link === 'barred'}
          disabledReason={busy ?? undefined}
          onClick={() => onSet('barred')}
        >
          <Ban />
          Forbid
        </Button>
        <Button
          size='sm'
          variant='ghost'
          disabled={busy !== null || link === 'derived'}
          disabledReason={busy ?? undefined}
          onClick={() => onSet('derived')}
        >
          <RotateCcw />
          Let nature decide
        </Button>
      </div>
    </li>
  )
}

export function FoodLinkControls({ id, card, blocked }: Blocked) {
  const [fresh, setFresh] = useState<number | null>(null)
  const set = useWildAction<{ prey: number; link: Link }>(
    'species:prey',
    ({ prey, link }) => ({ hunter_id: id, prey_id: prey, link }),
    () => setFresh(null)
  )
  const busy = busyOf(blocked, set.isPending)
  const shown = new Map<number, Ref>()
  for (const item of [...card.hunts, ...card.pinned_prey, ...card.barred_prey])
    if (item) shown.set(item.id, item)
  const prey = [...shown.values()]
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      <Group title='What it hunts' icon={Crosshair}>
        <Muted variant='caption'>
          Each epoch it hunts every kind it shares a land with and can take by
          diet and size. Hold a hunt so it never ends, forbid one so it never
          begins, or let nature decide again.
        </Muted>
        {prey.length === 0 ? (
          <EmptyState
            icon={Crosshair}
            title='It hunts no kind'
            description='It shares no land with a kind it can take, and you have set no hunt.'
          />
        ) : (
          <ul className='flex min-w-0 flex-col gap-2'>
            {prey.map((item) => (
              <PreyRow
                key={item?.id}
                prey={item}
                link={linkOf(card, item?.id ?? 0)}
                busy={busy}
                onSet={(link) => set.mutate({ prey: item?.id ?? 0, link })}
              />
            ))}
          </ul>
        )}
        <div className='flex min-w-0 flex-wrap items-end gap-2'>
          <div className='flex min-w-0 flex-1 basis-60 flex-col gap-1'>
            <Label>Set it on a new prey</Label>
            <EntityPicker
              types={['species']}
              value={fresh}
              onChange={setFresh}
              placeholder='Choose a kind…'
            />
          </div>
          <Button
            size='sm'
            variant='outline'
            disabled={busy !== null || fresh === null || fresh === id}
            disabledReason={
              busy ??
              (fresh === null
                ? 'Choose a kind'
                : fresh === id
                  ? 'A kind does not hunt itself'
                  : undefined)
            }
            onClick={() =>
              fresh !== null && set.mutate({ prey: fresh, link: 'pinned' })
            }
          >
            <Pin />
            Make it hunt this
          </Button>
        </div>
      </Group>
      <Group title='Hunted by' icon={Ban}>
        {card.hunted_by.length === 0 ? (
          <Muted>No kind preys on it.</Muted>
        ) : (
          <div className='flex min-w-0 flex-wrap gap-2'>
            <Paged items={card.hunted_by}>
              {(item) => (
                <Badge key={item.id} variant='secondary'>
                  <Crosshair />
                  {item.name}
                </Badge>
              )}
            </Paged>
          </div>
        )}
        <Muted variant='caption'>
          To spare it from a hunter, open that hunter and forbid the hunt.
        </Muted>
      </Group>
    </div>
  )
}

export function HostControls({ id, card, blocked }: Blocked) {
  const [fresh, setFresh] = useState<number | null>(null)
  const set = useWildAction<{
    disease: number
    carried: boolean
    immune: boolean
    release?: boolean
  }>(
    'species:host',
    ({ disease, carried, immune, release }) => ({
      species_id: id,
      disease_id: disease,
      carried,
      immune,
      release: release ?? false,
    }),
    () => setFresh(null)
  )
  const busy = busyOf(blocked, set.isPending)
  return (
    <Group title='Sicknesses it carries' icon={Biohazard}>
      <Muted variant='caption'>
        A carrier spreads its sickness where it ranges and loses numbers where
        it rages. A carrier that lives through it may grow immune. Setting
        immunity holds it until you let the world decide again.
      </Muted>
      {card.hosts.length === 0 ? (
        <EmptyState
          icon={ShieldCheck}
          title='It carries no sickness'
          description='Choose a sickness below to make it a carrier.'
        />
      ) : (
        <ul className='flex min-w-0 flex-col gap-2'>
          <Paged items={card.hosts} as='li'>
            {(row) => {
              const disease = row.disease?.id ?? 0
              const held = row.locked.includes('immune')
              return (
                <li
                  key={disease}
                  className='flex min-w-0 flex-wrap items-center gap-2 rounded-lg border bg-muted/30 p-2'
                >
                  <Medallion
                    icon={row.immune ? ShieldCheck : Biohazard}
                    tone={row.immune ? 'success' : 'danger'}
                    size='sm'
                  />
                  <div className='flex min-w-0 flex-1 flex-col gap-1'>
                    <Name item={row.disease} />
                    <div className='flex flex-wrap gap-1'>
                      <Badge
                        size='sm'
                        variant={row.immune ? 'success' : 'destructive'}
                      >
                        {row.immune ? 'Immune' : 'Carries it'}
                      </Badge>
                      {held && (
                        <Badge size='sm' variant='default'>
                          Held by you
                        </Badge>
                      )}
                    </div>
                  </div>
                  <label className='flex items-center gap-2'>
                    <Text as='span' variant='caption'>
                      Immune
                    </Text>
                    <Switch
                      checked={row.immune}
                      disabled={busy !== null}
                      aria-label={`Immune to ${row.disease?.name ?? 'this sickness'}`}
                      onCheckedChange={(immune) =>
                        set.mutate({ disease, carried: true, immune })
                      }
                    />
                  </label>
                  {held && (
                    <Button
                      size='sm'
                      variant='outline'
                      disabled={busy !== null}
                      disabledReason={busy ?? undefined}
                      onClick={() =>
                        set.mutate({
                          disease,
                          carried: true,
                          immune: row.immune,
                          release: true,
                        })
                      }
                    >
                      <Unlock />
                      Let the world decide
                    </Button>
                  )}
                  <Button
                    size='icon-sm'
                    variant='ghost'
                    aria-label={`No longer carries ${row.disease?.name ?? 'it'}`}
                    disabled={busy !== null}
                    disabledReason={busy ?? undefined}
                    onClick={() =>
                      set.mutate({ disease, carried: false, immune: false })
                    }
                  >
                    <Trash2 />
                  </Button>
                </li>
              )
            }}
          </Paged>
        </ul>
      )}
      <div className='flex min-w-0 flex-wrap items-end gap-2'>
        <div className='flex min-w-0 flex-1 basis-60 flex-col gap-1'>
          <Label>Make it carry a sickness</Label>
          <EntityPicker
            types={['disease']}
            value={fresh}
            onChange={setFresh}
            placeholder='Choose a sickness…'
          />
        </div>
        <Button
          size='sm'
          variant='outline'
          disabled={busy !== null || fresh === null}
          disabledReason={
            busy ?? (fresh === null ? 'Choose a sickness' : undefined)
          }
          onClick={() =>
            fresh !== null &&
            set.mutate({ disease: fresh, carried: true, immune: false })
          }
        >
          <Biohazard />
          It carries this
        </Button>
      </div>
    </Group>
  )
}

const USE_TABLE = Object.fromEntries(
  speciesUseValues.map((key) => [key, named(USE, key).label])
)

function KindRow({
  kind,
  held,
  busy,
  onToggle,
  onSave,
  onRelease,
  onDrop,
}: {
  kind: UseKind
  held: boolean
  busy: string | null
  onToggle: (held: boolean) => void
  onSave: (values: Record<string, unknown>) => void
  onRelease: () => void
  onDrop: () => void
}) {
  const [output, setOutput] = useState(String(kind.output_pct))
  const [base, setBase] = useState<string>(kind.base_use)
  const spec = named(USE, kind.base_use)
  return (
    <li className='flex min-w-0 flex-col gap-2 rounded-lg border bg-muted/30 p-2'>
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Medallion icon={spec.icon} tone={spec.tone} size='sm' />
        <div className='flex min-w-0 flex-1 flex-col'>
          <Text as='span' weight='medium' truncate>
            {kind.name}
          </Text>
          <Muted as='span' variant='caption' truncate>
            {`Works as ${spec.label.toLowerCase()} at ${kind.output_pct}% yield · kept for ${kind.species.length} ${kind.species.length === 1 ? 'kind' : 'kinds'}`}
          </Muted>
        </div>
        <label className='flex items-center gap-2'>
          <Text as='span' variant='caption'>
            Kept so
          </Text>
          <Switch
            checked={held}
            disabled={busy !== null}
            aria-label={`Keep this kind as ${kind.name}`}
            onCheckedChange={onToggle}
          />
        </label>
      </div>
      <div className='grid min-w-0 grid-cols-1 items-end gap-2 @md/wild:grid-cols-3'>
        <MindPicker
          label='Works as'
          value={base}
          table={USE_TABLE}
          blocked={busy}
          onPick={setBase}
        />
        <NumberField
          label='Yield (%)'
          value={output}
          min={0}
          max={1000}
          disabled={busy !== null}
          onChange={setOutput}
        />
        <div className='flex flex-wrap gap-1'>
          <Button
            size='sm'
            variant='outline'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() =>
              onSave({
                output_pct: Math.round(Number(output) || 0),
                base_use: base,
              })
            }
          >
            <Save />
            Set it so
          </Button>
          {kind.locked.length > 0 && (
            <Button
              size='sm'
              variant='ghost'
              disabled={busy !== null}
              disabledReason={busy ?? undefined}
              onClick={onRelease}
            >
              <Unlock />
              Release
            </Button>
          )}
          <Button
            size='icon-sm'
            variant='ghost'
            aria-label={`Forget ${kind.name}`}
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={onDrop}
          >
            <Trash2 />
          </Button>
        </div>
      </div>
    </li>
  )
}

export function KeepingControls({ id, card, blocked }: Blocked) {
  const kinds = useUseKinds()
  const [name, setName] = useState('')
  const [base, setBase] = useState('')
  const [output, setOutput] = useState('100')
  const toggle = useWildAction<{ kind: number; held: boolean }>(
    'species:custom_use',
    ({ kind, held }) => ({ species_id: id, kind_id: kind, held })
  )
  const create = useWildAction<void>(
    'use_kind:create',
    () => ({
      name: name.trim(),
      base_use: base,
      output_pct: Math.round(Number(output) || 0),
    }),
    () => {
      setName('')
      setBase('')
      setOutput('100')
    }
  )
  const edit = useWildAction<{
    kind: number
    values: Record<string, unknown>
    release: string[]
  }>('use_kind:edit', ({ kind, values, release }) => ({
    kind_id: kind,
    values,
    release,
  }))
  const drop = useWildAction<number>('use_kind:drop', (kind) => ({
    kind_id: kind,
  }))
  const busy = busyOf(
    blocked,
    toggle.isPending,
    create.isPending,
    edit.isPending,
    drop.isPending
  )
  const mine = new Set(card.custom_uses.map((item) => item.kind_id))
  return (
    <Group title='Ways of keeping of your own' icon={Sparkles}>
      <Muted variant='caption'>
        A way of keeping you devise works as one of the eight uses and scales
        what herds of it yield. Keeping a kind this way also keeps it for that
        use.
      </Muted>
      {(kinds.data ?? []).length === 0 ? (
        <Muted>No way of keeping has been devised yet.</Muted>
      ) : (
        <ul className='flex min-w-0 flex-col gap-2'>
          {(kinds.data ?? []).map((kind) => (
            <KindRow
              key={`${kind.id}-${kind.output_pct}-${kind.base_use}`}
              kind={kind}
              held={mine.has(kind.id)}
              busy={busy}
              onToggle={(held) => toggle.mutate({ kind: kind.id, held })}
              onSave={(values) =>
                edit.mutate({ kind: kind.id, values, release: [] })
              }
              onRelease={() =>
                edit.mutate({
                  kind: kind.id,
                  values: {},
                  release: [...kind.locked],
                })
              }
              onDrop={() => drop.mutate(kind.id)}
            />
          ))}
        </ul>
      )}
      <div className='grid min-w-0 grid-cols-1 items-end gap-2 @md/wild:grid-cols-4'>
        <div className='flex min-w-0 flex-col gap-1'>
          <Label as='label' htmlFor={`keeping-name-${id}`}>
            Name
          </Label>
          <Input
            id={`keeping-name-${id}`}
            value={name}
            placeholder='Grave-guarding, falconry…'
            onChange={(event) => setName(event.target.value)}
          />
        </div>
        <MindPicker
          label='Works as'
          value={base}
          table={USE_TABLE}
          blocked={busy}
          placeholder='Choose a use'
          onPick={setBase}
        />
        <NumberField
          label='Yield (%)'
          value={output}
          min={0}
          max={1000}
          disabled={busy !== null}
          onChange={setOutput}
        />
        <Button
          size='sm'
          variant='outline'
          disabled={busy !== null || name.trim() === '' || base === ''}
          disabledReason={
            busy ??
            (name.trim() === '' || base === ''
              ? 'Name it and choose what it works as'
              : undefined)
          }
          onClick={() => create.mutate()}
        >
          <Plus />
          Devise it
        </Button>
      </div>
    </Group>
  )
}

export function CustomUseBadges({ card }: { card: SpeciesCard }) {
  if (card.custom_uses.length === 0) return null
  return (
    <div className='flex min-w-0 flex-wrap gap-1.5'>
      <Paged items={card.custom_uses}>
        {(item) => {
          const spec = named(USE, item.base_use)
          return (
            <Badge key={item.kind_id} variant='default'>
              <Sparkles />
              {`${item.name} · ${spec.label} ${item.output_pct}%`}
              <spec.icon />
            </Badge>
          )
        }}
      </Paged>
    </div>
  )
}

export function WorldMaterialBadge({
  name,
}: {
  name: string | null | undefined
}) {
  if (!name) return null
  return (
    <Badge size='sm' variant='info'>
      <Gem />
      {name}
    </Badge>
  )
}

export function HerdDrop({
  communityId,
  speciesId,
  name,
  blocked,
}: {
  communityId: number
  speciesId: number
  name: string
  blocked: string | null
}) {
  const drop = useWildAction<void>('herd:drop', () => ({
    community_id: communityId,
    species_id: speciesId,
  }))
  const busy = busyOf(blocked, drop.isPending)
  return (
    <Button
      size='icon-sm'
      variant='ghost'
      aria-label={`Scatter the herd of ${name}`}
      disabled={busy !== null}
      disabledReason={busy ?? undefined}
      onClick={() => drop.mutate()}
    >
      <Trash2 />
    </Button>
  )
}
