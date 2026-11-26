import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  Compass,
  Eye,
  Footprints,
  Gem,
  Ghost,
  Lock,
  Map as MapIcon,
  Mountain,
  Plus,
  Save,
  ScrollText,
  ShieldAlert,
  Skull,
  Sparkles,
  Trash2,
  TriangleAlert,
  Undo2,
  Unlock,
  Waves,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import {
  type components,
  dangerSourceValues,
  regionMemoryKindValues,
} from '@/api/generated/schema'
import { plural } from '@/lib/units'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import {
  EmptyState,
  FieldTile,
  KpiTile,
  LoadingBlock,
  Medallion,
  Paged,
  Section,
  StatBar,
} from '@/components/domain'
import { MultiSelect } from '@/components/domain/MultiSelect'
import { Label, Muted, Text } from '@/components/typography'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { loreKeys } from '../api/keys'
import { MindPicker } from '../mind/parts'
import {
  AdjustPanel,
  Card,
  Name,
  NumberField,
  SwitchField,
  Tile,
  TileGrid,
} from '../wilds/parts'
import { RIVER, named, plain } from './labels'
import {
  DANGER_SOURCE,
  HARM,
  HAZARD,
  MEMORY,
  ORIGIN,
  dangerTone,
  sacredTone,
} from './regionLabels'

type Terrain = components['schemas']['RegionTerrainView']
type Danger = components['schemas']['RegionDangerView']
type Memory = components['schemas']['RegionMemoryView']
type Knowledge = components['schemas']['MapKnowledgeView']
type DangerSource = components['schemas']['DangerSource']
type MemoryKind = components['schemas']['RegionMemoryKind']
type Harm = components['schemas']['DangerHarm']

const PERCENT = 100
const WORKING = 'Working…'
const DEFAULT_STRENGTH = 40
const DEFAULT_MAGNITUDE = 50
const DEFAULT_LEVEL = 60

const SOURCE_CHOICES = Object.fromEntries(
  dangerSourceValues.map((key) => [key, named(DANGER_SOURCE, key).label])
)
const MEMORY_CHOICES = Object.fromEntries(
  regionMemoryKindValues.map((key) => [key, named(MEMORY, key).label])
)

function percent(raw: string): number {
  const value = Number(raw)
  if (!Number.isFinite(value)) return 0
  return Math.max(0, Math.min(PERCENT, Math.round(value)))
}

function terrainKey(regionId: number) {
  return [...loreKeys.entity(regionId), 'environment', 'terrain'] as const
}

function useBusy(...pending: boolean[]): string | null {
  const { reason } = useGodGate()
  return reason() ?? (pending.some(Boolean) ? WORKING : null)
}

function DangerRow({ danger, busy }: { danger: Danger; busy: string | null }) {
  const [strength, setStrength] = useState(String(danger.strength))
  const [targets, setTargets] = useState<string[]>(danger.targets)
  const edit = useGodAction({
    writes: [{ lever: 'region:danger_edit' }],
    run: (body: { strength?: number; hold?: boolean; targets?: Harm[] }) =>
      unwrap(
        api.POST('/api/actions/region:danger_edit', {
          body: { danger_id: danger.id, ...body },
        })
      ),
    success: 'The danger is reshaped',
  })
  const release = useGodAction({
    writes: [{ lever: 'region:danger_release' }],
    run: () =>
      unwrap(
        api.POST('/api/actions/region:danger_release', {
          body: { danger_id: danger.id },
        })
      ),
    success: 'The danger follows the land again',
  })
  const remove = useGodAction({
    writes: [{ lever: 'region:danger_delete' }],
    run: () =>
      unwrap(
        api.POST('/api/actions/region:danger_delete', {
          body: { danger_id: danger.id },
        })
      ),
    success: 'The danger is driven out',
  })
  const blocked =
    busy ??
    (edit.isPending || release.isPending || remove.isPending ? WORKING : null)
  const spec = named(DANGER_SOURCE, danger.source)
  return (
    <div className='flex min-w-0 flex-wrap items-end gap-3 rounded-md border surface-sheen border-gild/60 bg-card p-2'>
      <div className='flex min-w-40 flex-1 items-center gap-2'>
        <Medallion icon={spec.icon} tone={spec.tone} size='sm' />
        <Text as='span' weight='medium' truncate>
          {spec.label}
        </Text>
      </div>
      <div className='w-28'>
        <NumberField
          label='Strength'
          value={strength}
          min={0}
          max={PERCENT}
          disabled={blocked !== null}
          onChange={setStrength}
        />
      </div>
      <div className='min-w-48'>
        <MultiSelect
          label='Harms only (none chosen: all it reaches)'
          size='sm'
          options={danger.reachable.map((harm) => ({
            value: harm,
            label: named(HARM, harm).label,
          }))}
          value={targets}
          onChange={setTargets}
        />
      </div>
      <Button
        act={edit}
        size='sm'
        disabled={blocked !== null}
        disabledReason={blocked ?? undefined}
        onClick={() =>
          edit.mutate({
            strength: percent(strength),
            hold: true,
            targets: targets as Harm[],
          })
        }
      >
        <Save />
        Set and hold
      </Button>
      {danger.held ? (
        <Button
          act={release}
          size='sm'
          variant='outline'
          disabled={blocked !== null}
          disabledReason={blocked ?? undefined}
          onClick={() => release.mutate()}
        >
          <Unlock />
          Let the land decide
        </Button>
      ) : (
        <Button
          act={edit}
          size='sm'
          variant='outline'
          disabled={blocked !== null}
          disabledReason={blocked ?? undefined}
          onClick={() => edit.mutate({ hold: true })}
        >
          <Lock />
          Hold
        </Button>
      )}
      <Button
        act={remove}
        size='sm'
        variant='outline'
        disabled={blocked !== null}
        disabledReason={blocked ?? undefined}
        onClick={() => remove.mutate()}
      >
        <Trash2 />
        Drive out
      </Button>
    </div>
  )
}

function CreateDanger({
  regionId,
  busy,
}: {
  regionId: number
  busy: string | null
}) {
  const [source, setSource] = useState<string>('')
  const [strength, setStrength] = useState(String(DEFAULT_STRENGTH))
  const [hold, setHold] = useState(true)
  const create = useGodAction({
    writes: [{ lever: 'region:danger_create' }],
    run: () =>
      unwrap(
        api.POST('/api/actions/region:danger_create', {
          body: {
            region_id: regionId,
            source: source as DangerSource,
            strength: percent(strength),
            hold,
          },
        })
      ),
    success: 'A new danger walks this land',
  })
  const blocked = busy ?? (create.isPending ? WORKING : null)
  return (
    <div className='flex min-w-0 flex-wrap items-end gap-3'>
      <div className='min-w-48 flex-1'>
        <MindPicker
          label='Loose a danger'
          value={source}
          table={SOURCE_CHOICES}
          blocked={blocked}
          placeholder='Choose a danger'
          onPick={setSource}
        />
      </div>
      <div className='w-28'>
        <NumberField
          label='Strength'
          value={strength}
          min={0}
          max={PERCENT}
          disabled={blocked !== null}
          onChange={setStrength}
        />
      </div>
      <SwitchField
        permission='lock_canon'
        label='Hold it'
        checked={hold}
        disabled={blocked !== null}
        onChange={setHold}
      />
      <Button
        act={create}
        size='sm'
        disabled={blocked !== null || source === ''}
        disabledReason={
          blocked ?? (source === '' ? 'Choose a danger first' : undefined)
        }
        onClick={() => create.mutate()}
      >
        <Plus />
        Loose it
      </Button>
    </div>
  )
}

function DangerCard({ regionId, view }: { regionId: number; view: Terrain }) {
  const busy = useBusy()
  return (
    <div id='section-region-dangers' className='min-w-0'>
      <Card
        title='Dangers of the land'
        icon={ShieldAlert}
        tone={dangerTone(view.danger)}
        hint='Each source harms what it can reach by its own weight; set which of those it harms on each danger'
      >
        {view.dangers.length === 0 ? (
          <Muted>
            This land is safe: nothing here preys on those who pass.
          </Muted>
        ) : (
          <TileGrid>
            <Paged items={view.dangers}>
              {(danger) => {
                const spec = named(DANGER_SOURCE, danger.source)
                return (
                  <Tile
                    key={danger.id}
                    spec={spec}
                    caption={
                      danger.source_node_name
                        ? `${danger.strength} · ${danger.source_node_name}`
                        : `${danger.strength} · ${DANGER_SOURCE[danger.source]?.hint ?? ''}`
                    }
                    aside={
                      <Badge
                        size='sm'
                        variant={
                          danger.held ? 'default' : ORIGIN[danger.origin]?.tone
                        }
                      >
                        {danger.held ? 'Held' : ORIGIN[danger.origin]?.label}
                      </Badge>
                    }
                  />
                )
              }}
            </Paged>
          </TileGrid>
        )}
        <div className='grid min-w-0 grid-cols-1 gap-2 @md/card:grid-cols-2 @2xl/card:grid-cols-3'>
          {Object.entries(HARM).map(([key, spec]) => (
            <StatBar
              key={key}
              label={spec.label}
              value={view.harms[key as keyof typeof view.harms] ?? 0}
              max={PERCENT}
              icon={spec.icon}
              tone='destructive'
            />
          ))}
        </div>
        <AdjustPanel
          writes={[
            { lever: 'region:danger_create' },
            { lever: 'region:danger_delete' },
            { lever: 'region:danger_edit' },
            { lever: 'region:danger_release' },
          ]}
          title='Shape the dangers'
          note='Loose a danger of any kind, set its strength, hold it against the land or drive it out. A danger the land still breeds returns unless you hold it at nothing.'
        >
          <CreateDanger regionId={regionId} busy={busy} />
          <Paged items={view.dangers}>
            {(danger) => (
              <DangerRow key={danger.id} danger={danger} busy={busy} />
            )}
          </Paged>
        </AdjustPanel>
      </Card>
    </div>
  )
}

function MemoryRow({ memory, busy }: { memory: Memory; busy: string | null }) {
  const [magnitude, setMagnitude] = useState(String(memory.magnitude))
  const [kind, setKind] = useState<string>(memory.kind)
  const edit = useGodAction({
    writes: [{ lever: 'region:memory_edit' }],
    run: (hold: boolean) =>
      unwrap(
        api.POST('/api/actions/region:memory_edit', {
          body: {
            memory_id: memory.id,
            magnitude: percent(magnitude),
            kind: kind as MemoryKind,
            hold,
          },
        })
      ),
    success: 'The memory is reshaped',
  })
  const remove = useGodAction({
    writes: [{ lever: 'region:memory_delete' }],
    run: () =>
      unwrap(
        api.POST('/api/actions/region:memory_delete', {
          body: { memory_id: memory.id },
        })
      ),
    success: 'The land forgets',
  })
  const blocked = busy ?? (edit.isPending || remove.isPending ? WORKING : null)
  return (
    <div className='flex min-w-0 flex-wrap items-end gap-3 rounded-md border surface-sheen border-gild/60 bg-card p-2'>
      <Text as='span' weight='medium' className='min-w-40 flex-1' truncate>
        {memory.title}
      </Text>
      <div className='w-40'>
        <MindPicker
          label='Kind'
          value={kind}
          table={MEMORY_CHOICES}
          blocked={blocked}
          onPick={setKind}
        />
      </div>
      <div className='w-28'>
        <NumberField
          label='Magnitude'
          value={magnitude}
          min={0}
          max={PERCENT}
          disabled={blocked !== null}
          onChange={setMagnitude}
        />
      </div>
      <Button
        act={edit}
        size='sm'
        disabled={blocked !== null}
        disabledReason={blocked ?? undefined}
        onClick={() => edit.mutate(true)}
      >
        <Save />
        Set and hold
      </Button>
      {memory.held && (
        <Button
          act={edit}
          size='sm'
          variant='outline'
          disabled={blocked !== null}
          disabledReason={blocked ?? undefined}
          onClick={() => edit.mutate(false)}
        >
          <Unlock />
          Let it fade
        </Button>
      )}
      <Button
        act={remove}
        size='sm'
        variant='outline'
        disabled={blocked !== null}
        disabledReason={blocked ?? undefined}
        onClick={() => remove.mutate()}
      >
        <Trash2 />
        Forget
      </Button>
    </div>
  )
}

function SanctityControls({
  regionId,
  view,
  busy,
}: {
  regionId: number
  view: Terrain
  busy: string | null
}) {
  const [sacredness, setSacredness] = useState(String(view.sacredness))
  const [kind, setKind] = useState<string>('')
  const [magnitude, setMagnitude] = useState(String(DEFAULT_MAGNITUDE))
  const [title, setTitle] = useState('')
  const sanctify = useGodAction({
    writes: [{ lever: 'region:sanctify' }],
    run: () =>
      unwrap(
        api.POST('/api/actions/region:sanctify', {
          body: {
            region_id: regionId,
            sacredness: percent(sacredness),
            hold: true,
          },
        })
      ),
    success: 'The land is sanctified',
  })
  const release = useGodAction({
    writes: [{ lever: 'environment:unlock' }],
    run: () =>
      unwrap(
        api.POST('/api/actions/environment:unlock', {
          body: {
            region_id: regionId,
            field: 'sacredness',
          },
        })
      ),
    success: 'Sacredness follows the land again',
  })
  const remember = useGodAction({
    writes: [{ lever: 'region:memory_add' }],
    run: () =>
      unwrap(
        api.POST('/api/actions/region:memory_add', {
          body: {
            region_id: regionId,
            kind: kind as MemoryKind,
            magnitude: percent(magnitude),
            title: title.trim(),
            hold: true,
          },
        })
      ),
    success: 'The land remembers',
    onDone: () => setTitle(''),
  })
  const blocked =
    busy ??
    (sanctify.isPending || release.isPending || remember.isPending
      ? WORKING
      : null)
  return (
    <AdjustPanel
      acts={[sanctify, release, remember]}
      title='Hallow, remember and forget'
      note='Sanctify the land or release its holiness to what stands on it; write an event into its memory, reshape or erase one. Held memories never fade.'
    >
      <div className='flex min-w-0 flex-wrap items-end gap-3'>
        <div className='w-32'>
          <NumberField
            label='Sacredness'
            value={sacredness}
            min={0}
            max={PERCENT}
            disabled={blocked !== null}
            onChange={setSacredness}
          />
        </div>
        <Button
          act={sanctify}
          size='sm'
          disabled={blocked !== null}
          disabledReason={blocked ?? undefined}
          onClick={() => sanctify.mutate()}
        >
          <Sparkles />
          Sanctify and hold
        </Button>
        {view.sacredness_held && (
          <Button
            act={release}
            size='sm'
            variant='outline'
            disabled={blocked !== null}
            disabledReason={blocked ?? undefined}
            onClick={() => release.mutate()}
          >
            <Unlock />
            Let the land decide
          </Button>
        )}
      </div>
      <div className='flex min-w-0 flex-wrap items-end gap-3'>
        <div className='min-w-40 flex-1'>
          <MindPicker
            label='Remember'
            value={kind}
            table={MEMORY_CHOICES}
            blocked={blocked}
            placeholder='What happened'
            onPick={setKind}
          />
        </div>
        <FieldTile
          id={`memory-title-${regionId}`}
          label='Called'
          className='min-w-48 flex-1'
        >
          <Input
            id={`memory-title-${regionId}`}
            value={title}
            maxLength={200}
            placeholder='The name of the happening'
            disabled={blocked !== null}
            onChange={(event) => setTitle(event.target.value)}
          />
        </FieldTile>
        <div className='w-28'>
          <NumberField
            label='Magnitude'
            value={magnitude}
            min={0}
            max={PERCENT}
            disabled={blocked !== null}
            onChange={setMagnitude}
          />
        </div>
        <Button
          act={remember}
          size='sm'
          disabled={blocked !== null || kind === '' || title.trim() === ''}
          disabledReason={
            blocked ??
            (kind === '' || title.trim() === ''
              ? 'Name what happened first'
              : undefined)
          }
          onClick={() => remember.mutate()}
        >
          <Plus />
          Write it into the land
        </Button>
      </div>
      <Paged items={view.memories}>
        {(memory) => (
          <MemoryRow key={memory.id} memory={memory} busy={blocked} />
        )}
      </Paged>
    </AdjustPanel>
  )
}

function SanctityCard({ regionId, view }: { regionId: number; view: Terrain }) {
  const busy = useBusy()
  return (
    <div id='section-region-sanctity' className='min-w-0'>
      <Card
        title='Holy ground and memory'
        icon={Sparkles}
        tone={sacredTone(view.sacredness, view.pilgrim_sacred_min)}
        hint='What happened here, and what makes the land holy'
        aside={
          view.draws_pilgrims ? (
            <Badge size='sm' variant='success'>
              Draws pilgrims
            </Badge>
          ) : undefined
        }
      >
        <StatBar
          label='Sacredness'
          value={view.sacredness}
          max={PERCENT}
          icon={Sparkles}
          tone='success'
        />
        <div className='grid min-w-0 grid-cols-1 gap-2 @md/card:grid-cols-2'>
          <StatBar
            label='Dark memories'
            value={view.darkness}
            max={PERCENT}
            icon={Ghost}
            tone='destructive'
          />
          <StatBar
            label='Holy memories'
            value={view.holiness}
            max={PERCENT}
            icon={Sparkles}
            tone='success'
          />
        </div>
        {view.memories.length === 0 ? (
          <Muted>The land remembers nothing yet.</Muted>
        ) : (
          <TileGrid>
            <Paged items={view.memories}>
              {(memory) => (
                <Tile
                  key={memory.id}
                  spec={named(MEMORY, memory.kind)}
                  caption={`${memory.title} · ${memory.magnitude} · epoch ${memory.epoch}${memory.fades && !memory.held ? ' · fading' : ''}`}
                  aside={
                    memory.held ? (
                      <Badge size='sm' variant='default'>
                        Held
                      </Badge>
                    ) : undefined
                  }
                />
              )}
            </Paged>
          </TileGrid>
        )}
        <SanctityControls regionId={regionId} view={view} busy={busy} />
      </Card>
    </div>
  )
}

function KnowledgeRow({
  regionId,
  row,
  busy,
}: {
  regionId: number
  row: Knowledge
  busy: string | null
}) {
  const release = useGodAction({
    writes: [{ lever: 'region:knowledge_release' }],
    run: () =>
      unwrap(
        api.POST('/api/actions/region:knowledge_release', {
          body: {
            polity_id: row.polity_id,
            region_id: regionId,
          },
        })
      ),
    success: 'The realm’s maps follow its explorers again',
  })
  const blocked = busy ?? (release.isPending ? WORKING : null)
  const reveals = [
    { known: row.terrain, icon: Mountain, label: 'terrain' },
    { known: row.sacred, icon: Sparkles, label: 'holy sites' },
    { known: row.minerals, icon: Gem, label: 'seams' },
  ]
  return (
    <div className='flex min-w-0 flex-wrap items-center gap-2 rounded-md border surface-well border-gild/20 bg-muted/60 px-2 py-1.5'>
      <div className='min-w-32 flex-1 truncate'>
        <Name item={{ id: row.polity_id, name: row.polity_name }} />
      </div>
      <Paged items={reveals}>
        {(item) => (
          <Tooltip key={item.label}>
            <TooltipTrigger asChild>
              <span
                tabIndex={0}
                aria-label={`${item.known ? 'Knows' : 'Does not know'} the ${item.label}`}
              >
                <item.icon
                  aria-hidden='true'
                  className={
                    item.known
                      ? 'size-icon-sm text-success'
                      : 'size-icon-sm text-muted-foreground/40'
                  }
                />
              </span>
            </TooltipTrigger>
            <TooltipContent>
              {`${item.known ? 'Knows' : 'Does not know'} the ${item.label}`}
            </TooltipContent>
          </Tooltip>
        )}
      </Paged>
      <Badge size='sm' variant={row.unmapped ? 'warning' : 'info'}>
        {row.unmapped ? `Unmapped ${row.level}` : `Known ${row.level}`}
      </Badge>
      {row.held && (
        <Button
          act={release}
          size='sm'
          variant='outline'
          disabled={blocked !== null}
          disabledReason={blocked ?? undefined}
          onClick={() => release.mutate()}
        >
          <Unlock />
          Release
        </Button>
      )}
    </div>
  )
}

function KnowledgeCard({
  regionId,
  view,
}: {
  regionId: number
  view: Terrain
}) {
  const busy = useBusy()
  const [realm, setRealm] = useState('')
  const [level, setLevel] = useState(String(DEFAULT_LEVEL))
  const chart = useGodAction({
    writes: [{ lever: 'region:knowledge_set' }],
    run: (value: number) =>
      unwrap(
        api.POST('/api/actions/region:knowledge_set', {
          body: {
            polity_id: Number(realm),
            region_id: regionId,
            level: value,
            hold: true,
          },
        })
      ),
    success: (_result, value: number) =>
      value === 0 ? 'The realm loses its maps' : 'The realm’s maps are redrawn',
  })
  const blocked = busy ?? (chart.isPending ? WORKING : null)
  const realms = Object.fromEntries(
    view.realms.map((item) => [String(item.id), item.name])
  )
  return (
    <div id='section-region-knowledge' className='min-w-0'>
      <Card
        title='Maps of the realms'
        icon={Compass}
        tone='info'
        hint={`Below ${view.unmapped_below} a realm's armies may lose their way here`}
      >
        {view.knowledge.length === 0 ? (
          <Muted>No realm has mapped this land.</Muted>
        ) : (
          <Paged items={view.knowledge}>
            {(row) => (
              <KnowledgeRow
                key={row.polity_id}
                regionId={regionId}
                row={row}
                busy={blocked}
              />
            )}
          </Paged>
        )}
        <AdjustPanel
          acts={[chart]}
          title='Reveal or hide this land'
          note='Draw this region onto a realm’s maps or tear it out. What you set is held until you release it.'
        >
          {view.realms.length === 0 && (
            <Muted>No realm stands on this world.</Muted>
          )}
          <div className='flex min-w-0 flex-wrap items-end gap-3'>
            <div className='min-w-48 flex-1'>
              <MindPicker
                label='Realm'
                value={realm}
                table={realms}
                blocked={blocked}
                placeholder='Choose a realm'
                onPick={setRealm}
              />
            </div>
            <div className='w-28'>
              <NumberField
                label='Known'
                value={level}
                min={0}
                max={PERCENT}
                disabled={blocked !== null}
                onChange={setLevel}
              />
            </div>
            <Button
              act={chart}
              size='sm'
              disabled={blocked !== null || realm === ''}
              disabledReason={
                blocked ??
                (view.realms.length === 0
                  ? 'No realm stands on this world'
                  : realm === ''
                    ? 'Choose a realm first'
                    : undefined)
              }
              onClick={() => chart.mutate(percent(level))}
            >
              <Eye />
              Reveal
            </Button>
            <Button
              act={chart}
              size='sm'
              variant='outline'
              disabled={blocked !== null || realm === ''}
              disabledReason={
                blocked ??
                (view.realms.length === 0
                  ? 'No realm stands on this world'
                  : realm === ''
                    ? 'Choose a realm first'
                    : undefined)
              }
              onClick={() => chart.mutate(0)}
            >
              <Undo2 />
              Forget
            </Button>
          </div>
        </AdjustPanel>
      </Card>
    </div>
  )
}

function HazardCard({ view }: { view: Terrain }) {
  return (
    <div id='section-region-hazards' className='min-w-0'>
      <Card
        title='Seasonal hazards'
        icon={Skull}
        tone='warning'
        hint='Struck in sampled years, in the season each belongs to'
      >
        {view.exposure.length === 0 ? (
          <Muted>No seasonal hazard threatens this land.</Muted>
        ) : (
          <TileGrid>
            <Paged items={view.exposure}>
              {(item) => (
                <Tile
                  key={item.hazard}
                  spec={named(HAZARD, item.hazard)}
                  caption={HAZARD[item.hazard]?.season ?? item.season}
                />
              )}
            </Paged>
          </TileGrid>
        )}
        {view.hazards.length > 0 && (
          <div className='flex min-w-0 flex-col gap-2'>
            <Label variant='overline'>Struck</Label>
            <Paged items={view.hazards}>
              {(item) => (
                <Tile
                  key={item.id}
                  spec={named(HAZARD, item.hazard)}
                  caption={`Epoch ${item.epoch}${item.year != null ? `, year ${item.year}` : ''}${item.season_name ? `, ${item.season_name}` : ''}: ${item.deaths} died, ${item.injured} hurt${item.soldiers_lost ? `, ${plural(item.soldiers_lost, 'soldier', 'soldiers')} lost` : ''}`}
                />
              )}
            </Paged>
          </div>
        )}
      </Card>
    </div>
  )
}

function RiverCard({ regionId, view }: { regionId: number; view: Terrain }) {
  const busy = useBusy()
  const [target, setTarget] = useState('')
  const redirect = useGodAction({
    writes: [{ lever: 'region:river_redirect' }],
    run: () =>
      unwrap(
        api.POST('/api/actions/region:river_redirect', {
          body: {
            from_region_id: regionId,
            to_region_id: Number(target),
          },
        })
      ),
    success: 'The river runs a new course',
  })
  const blocked = busy ?? (redirect.isPending ? WORKING : null)
  const choices = Object.fromEntries(
    view.river_neighbours.map((item) => [
      String(item.id),
      `${item.name} (${item.river_class ? plain(RIVER, item.river_class).toLowerCase() : 'unsurveyed'})`,
    ])
  )
  const dry = view.river_class === 'none'
  return (
    <div id='section-region-river' className='min-w-0'>
      <Card
        title='The river'
        icon={Waves}
        tone='info'
        hint={
          dry
            ? 'No river runs here'
            : `A ${plain(RIVER, view.river_class).toLowerCase()} runs here`
        }
      >
        <AdjustPanel
          acts={[redirect]}
          title='Turn the river'
          note='Send this land’s river into a neighbouring region. The old valley dries to a stream or a dry bed and its places may lose their water; the new one gains it.'
        >
          {(dry || view.river_neighbours.length === 0) && (
            <Muted>
              There is no river here to turn, or no land to turn it into.
            </Muted>
          )}
          <div className='flex min-w-0 flex-wrap items-end gap-3'>
            <div className='min-w-48 flex-1'>
              <MindPicker
                label='Into'
                value={target}
                table={choices}
                blocked={blocked}
                placeholder='Choose a neighbour'
                onPick={setTarget}
              />
            </div>
            <Button
              act={redirect}
              size='sm'
              disabled={
                blocked !== null ||
                dry ||
                view.river_neighbours.length === 0 ||
                target === ''
              }
              disabledReason={
                blocked ??
                (dry
                  ? 'There is no river here to turn'
                  : view.river_neighbours.length === 0
                    ? 'There is no land to turn it into'
                    : target === ''
                      ? 'Choose a neighbour first'
                      : undefined)
              }
              onClick={() => redirect.mutate()}
            >
              <Footprints />
              Turn it
            </Button>
          </div>
        </AdjustPanel>
      </Card>
    </div>
  )
}

export function RegionTerrainSection({ regionId }: { regionId: number }) {
  const view = useQuery({
    queryKey: terrainKey(regionId),
    queryFn: () =>
      unwrap(
        api.GET('/api/regions/{region_id}/terrain', {
          params: { path: { region_id: regionId } },
        })
      ),
    retry: false,
  })
  const data = view.data
  return (
    <Section
      id='section-terrain'
      title='Dangers, holy ground and maps'
      description='What preys on those who live and pass here, what the land remembers, how holy it is, and which realms know it.'
      icon={ScrollText}
    >
      {view.isPending && <LoadingBlock label='Reading the land' />}
      {view.isError && (
        <EmptyState
          icon={TriangleAlert}
          title='The land could not be read'
          description={view.error.message}
        />
      )}
      {data === null && (
        <EmptyState
          icon={ShieldAlert}
          title='Not surveyed yet'
          description='The next epoch reads this land’s dangers and memory.'
        />
      )}
      {data && (
        <div className='@container/wild flex min-w-0 flex-col gap-4'>
          <div className='grid min-w-0 grid-cols-1 gap-3 @md/wild:grid-cols-2 @3xl/wild:grid-cols-4'>
            <KpiTile
              label='Danger'
              value={data.danger}
              icon={ShieldAlert}
              tone={dangerTone(data.danger)}
              meter={{ value: data.danger, max: PERCENT, label: 'Danger' }}
            />
            <KpiTile
              label='Sacredness'
              value={data.sacredness}
              icon={Sparkles}
              tone={sacredTone(data.sacredness, data.pilgrim_sacred_min)}
              meter={{
                value: data.sacredness,
                max: PERCENT,
                label: 'Sacredness',
              }}
            />
            <KpiTile
              label='Hauntings'
              value={`${data.haunting_pct}%`}
              icon={Ghost}
              tone='verdigris'
              hint='Of the usual chance, from dark memories and holy ground'
            />
            <KpiTile
              label='Realms that map it'
              value={data.knowledge.filter((row) => !row.unmapped).length}
              icon={MapIcon}
              tone='info'
            />
          </div>
          <div className='grid min-w-0 grid-cols-1 gap-3 @xl/wild:grid-cols-2'>
            <DangerCard regionId={regionId} view={data} />
            <SanctityCard regionId={regionId} view={data} />
            <KnowledgeCard regionId={regionId} view={data} />
            <HazardCard view={data} />
            <RiverCard regionId={regionId} view={data} />
          </div>
        </div>
      )}
    </Section>
  )
}
