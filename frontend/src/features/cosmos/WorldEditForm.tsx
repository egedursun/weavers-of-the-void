import { useState } from 'react'
import { Orbit as OrbitIcon, RefreshCw, Save } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { type components } from '@/api/generated/schema'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { FormRow } from '@/components/domain'
import { Muted } from '@/components/typography'
import { CosmicActionButton } from './CosmicActionButton'
import { StarOptions } from './StarOptions'
import {
  type Atmosphere,
  type CosmosWorld,
  type Discovery,
  type Gravity,
  type SonPublic,
  type WorldType,
} from './api'
import { type CosmosIndex } from './model/cosmosModel'
import {
  ATMOSPHERES,
  ATMOSPHERE_LABEL,
  DISCOVERIES,
  DISCOVERY_LABEL,
  GRAVITIES,
  GRAVITY_LABEL,
  STAR_TYPE_LABEL,
  WORLD_TYPES,
} from './model/labels'
import { type RuleBook, ruleText } from './model/rules'
import { useCosmicAction } from './useCosmicAction'

const AUTOMATIC = 'auto'
const KEEP = 'keep'
const LEAK_MAX = 100
const PERCENT = 100
const SEED_MAX = 64

type WorldEditFormProps = {
  item: CosmosWorld
  index: CosmosIndex
  rules: RuleBook
  sons: SonPublic[]
  isHome: boolean
}

type Draft = {
  name: string
  worldType: WorldType
  gravity: Gravity
  atmosphere: Atmosphere
  timeFactor: string
  discovery: Discovery
  leakage: string
  agents: string
  guardian: string
  twin: string
  description: string
  cosmology: string
  imagePrompt: string
  terrainSeed: string
  sea: string
  mountains: string
  moisture: string
}

function draftOf(item: CosmosWorld): Draft {
  const world = item.world
  return {
    name: world.name,
    worldType: world.world_type,
    gravity: world.gravity,
    atmosphere: world.atmosphere,
    timeFactor: String(world.time_factor),
    discovery: world.discovery,
    leakage: String(world.leakage),
    agents:
      world.mortal_agents === null ? AUTOMATIC : String(world.mortal_agents),
    guardian: KEEP,
    twin: KEEP,
    description: world.description ?? '',
    cosmology: world.cosmology ?? '',
    imagePrompt: world.image_prompt ?? '',
    terrainSeed: world.terrain_seed,
    sea: String(percentOf(world.terrain_sea)),
    mountains: String(percentOf(world.terrain_mountains)),
    moisture: String(percentOf(world.terrain_humidity)),
  }
}

function percentOf(share: number): number {
  return Math.round(share * PERCENT)
}

type EditBody = components['schemas']['PatchWorldsWorldIdBody']

function changes(item: CosmosWorld, draft: Draft): EditBody {
  const world = item.world
  const body: EditBody = { automatic_mortal_agents: false }
  if (draft.name.trim() !== world.name) body.name = draft.name.trim()
  if (draft.worldType !== world.world_type) body.world_type = draft.worldType
  if (draft.gravity !== world.gravity) body.gravity = draft.gravity
  if (draft.atmosphere !== world.atmosphere) body.atmosphere = draft.atmosphere
  if (Number(draft.timeFactor) !== world.time_factor)
    body.time_factor = Number(draft.timeFactor)
  if (draft.discovery !== world.discovery) body.discovery = draft.discovery
  if (Number(draft.leakage) !== world.leakage)
    body.leakage = Number(draft.leakage)
  if (draft.agents === AUTOMATIC && world.mortal_agents !== null)
    body.automatic_mortal_agents = true
  if (
    draft.agents !== AUTOMATIC &&
    Number(draft.agents) !== world.mortal_agents
  )
    body.mortal_agents = Number(draft.agents)
  if (draft.guardian !== KEEP) body.guardian_son_id = Number(draft.guardian)
  if (draft.twin !== KEEP) body.mirror_twin_id = Number(draft.twin)
  if (draft.description !== (world.description ?? ''))
    body.description = draft.description
  if (draft.cosmology !== (world.cosmology ?? ''))
    body.cosmology = draft.cosmology
  if (draft.imagePrompt !== (world.image_prompt ?? ''))
    body.image_prompt = draft.imagePrompt
  if (draft.terrainSeed.trim() !== world.terrain_seed)
    body.terrain_seed = draft.terrainSeed.trim()
  if (Number(draft.sea) !== percentOf(world.terrain_sea))
    body.sea_pct = Number(draft.sea)
  if (Number(draft.mountains) !== percentOf(world.terrain_mountains))
    body.mountains_pct = Number(draft.mountains)
  if (Number(draft.moisture) !== percentOf(world.terrain_humidity))
    body.moisture_pct = Number(draft.moisture)
  return body
}

const TERRAIN_FIELDS: readonly (keyof EditBody)[] = [
  'terrain_seed',
  'sea_pct',
  'mountains_pct',
  'moisture_pct',
  'world_type',
]

function reshapesLand(body: EditBody): boolean {
  return TERRAIN_FIELDS.some((field) => body[field] !== undefined)
}

function outOfRange(value: string, low: number): boolean {
  const number = Number(value)
  return !Number.isInteger(number) || number < low || number > PERCENT
}

function problem(draft: Draft, cap: number | undefined): string | undefined {
  const time = Number(draft.timeFactor)
  const leak = Number(draft.leakage)
  if (!draft.name.trim()) return 'A world needs a name.'
  if (!Number.isFinite(time) || time <= 0)
    return 'Time factor must be greater than zero.'
  if (!Number.isInteger(leak) || leak < 0 || leak > LEAK_MAX)
    return 'Leakage runs from 0 to 100.'
  if (!draft.terrainSeed.trim()) return 'The terrain needs a seed.'
  if (outOfRange(draft.sea, 0)) return 'Sea runs from 0 to 100 percent.'
  if (outOfRange(draft.mountains, 0))
    return 'Mountains run from 0 to 100 percent.'
  if (outOfRange(draft.moisture, -PERCENT))
    return 'Moisture runs from -100 to 100 percent.'
  if (
    draft.agents !== AUTOMATIC &&
    cap !== undefined &&
    Number(draft.agents) > cap
  )
    return `At most ${cap} mortal agents per world.`
  return undefined
}

export function WorldEditForm({
  item,
  index,
  rules,
  sons,
  isHome,
}: WorldEditFormProps) {
  const [draft, setDraft] = useState<Draft>(() => draftOf(item))
  const [orbit, setOrbit] = useState(KEEP)
  const [orbitOpen, setOrbitOpen] = useState(false)
  const set = <K extends keyof Draft>(key: K, value: Draft[K]) =>
    setDraft((current) => ({ ...current, [key]: value }))
  const world = item.world
  const cap = rules.get('mortalAgentsCap')
  const body = changes(item, draft)
  const invalid = problem(draft, cap)
  const [redrawDue, setRedrawDue] = useState(false)
  const edit = useCosmicAction({
    run: (sent: EditBody) =>
      unwrap(
        api.PATCH('/api/worlds/{world_id}', {
          params: { path: { world_id: world.id } },
          body: sent,
        })
      ),
    success: `${world.name} reshaped`,
    onDone: (_response, sent) => {
      setDraft((current) => ({ ...current, guardian: KEEP, twin: KEEP }))
      if (reshapesLand(sent)) setRedrawDue(true)
    },
  })
  const redraw = useCosmicAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/world:map', { body: { world_id: world.id } })
      ),
    success: `The map of ${world.name} was redrawn`,
    onDone: () => setRedrawDue(false),
  })
  const move = useCosmicAction({
    run: () => {
      const [kind, id] = orbit.split(':')
      return unwrap(
        api.PUT('/api/worlds/{world_id}/orbit', {
          params: { path: { world_id: world.id } },
          body:
            kind === 'star'
              ? { star_id: Number(id) }
              : { parent_world_id: Number(id) },
        })
      )
    },
    success: `${world.name} moved to a new orbit`,
    onDone: () => setOrbit(KEEP),
  })
  const parent = index.world(world.parent_world_id)
  const host = index.star(world.star_id)
  const currentOrbit = parent
    ? `currently a moon of ${parent.world.name}`
    : host
      ? `currently around ${host.name}`
      : 'currently starless'
  const agentOptions = Array.from(
    { length: (cap ?? 0) + 1 },
    (_, value) => value
  )
  const livingSons = sons.filter((son) => son.son.status !== 'dead')
  return (
    <div className='flex min-w-0 flex-col gap-4'>
      <FormRow label='Name'>
        {(id) => (
          <Input
            id={id}
            value={draft.name}
            maxLength={80}
            onChange={(event) => set('name', event.target.value)}
          />
        )}
      </FormRow>
      <FormRow label='Type'>
        {(id) => (
          <Select
            value={draft.worldType}
            onValueChange={(value) => set('worldType', value as WorldType)}
          >
            <SelectTrigger id={id} className='w-full'>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {WORLD_TYPES.map((type) => (
                <SelectItem key={type} value={type}>
                  {index.look(type)?.label ?? type}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
      </FormRow>
      <FormRow label='Gravity'>
        {(id) => (
          <Select
            value={draft.gravity}
            onValueChange={(value) => set('gravity', value as Gravity)}
          >
            <SelectTrigger id={id} className='w-full'>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {GRAVITIES.map((value) => (
                <SelectItem key={value} value={value}>
                  {GRAVITY_LABEL[value]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
      </FormRow>
      <FormRow label='Atmosphere'>
        {(id) => (
          <Select
            value={draft.atmosphere}
            onValueChange={(value) => set('atmosphere', value as Atmosphere)}
          >
            <SelectTrigger id={id} className='w-full'>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {ATMOSPHERES.map((value) => (
                <SelectItem key={value} value={value}>
                  {ATMOSPHERE_LABEL[value]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
      </FormRow>
      <FormRow
        label='Time factor'
        description='1 is normal flow; 2 twice as fast, 0.5 half speed.'
      >
        {(id) => (
          <Input
            id={id}
            type='number'
            min={0.01}
            step='any'
            inputMode='decimal'
            value={draft.timeFactor}
            onChange={(event) => set('timeFactor', event.target.value)}
          />
        )}
      </FormRow>
      <FormRow label='Discovery'>
        {(id) => (
          <Select
            value={draft.discovery}
            onValueChange={(value) => set('discovery', value as Discovery)}
          >
            <SelectTrigger id={id} className='w-full'>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {DISCOVERIES.filter(
                (value) => !(isHome && value === 'forgotten')
              ).map((value) => (
                <SelectItem key={value} value={value}>
                  {DISCOVERY_LABEL[value]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
      </FormRow>
      <FormRow label='Leakage' description='0 to 100.'>
        {(id) => (
          <Input
            id={id}
            type='number'
            min={0}
            max={LEAK_MAX}
            inputMode='numeric'
            value={draft.leakage}
            onChange={(event) => set('leakage', event.target.value)}
          />
        )}
      </FormRow>
      <FormRow
        label='Mortal agents'
        description='Communities that play their own turn each epoch.'
      >
        {(id) => (
          <Select
            value={draft.agents}
            onValueChange={(value) => set('agents', value)}
          >
            <SelectTrigger id={id} className='w-full'>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={AUTOMATIC}>
                Automatic, by population
              </SelectItem>
              {agentOptions.map((value) => (
                <SelectItem key={value} value={String(value)}>
                  {`${value} communities`}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
      </FormRow>
      <FormRow
        label='Guardian son'
        description='Declaring a guardian makes this world sacred to that son.'
      >
        {(id) => (
          <Select
            value={draft.guardian}
            onValueChange={(value) => set('guardian', value)}
          >
            <SelectTrigger id={id} className='w-full'>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={KEEP}>Keep as it is</SelectItem>
              {livingSons.map((son) => (
                <SelectItem key={son.son.id} value={String(son.son.id)}>
                  {son.son.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
      </FormRow>
      <FormRow label='Mirror twin'>
        {(id) => (
          <Select
            value={draft.twin}
            onValueChange={(value) => set('twin', value)}
          >
            <SelectTrigger id={id} className='w-full'>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={KEEP}>Keep as it is</SelectItem>
              {index.worlds
                .filter((other) => other.world.id !== world.id)
                .map((other) => (
                  <SelectItem
                    key={other.world.id}
                    value={String(other.world.id)}
                  >
                    {other.world.name}
                  </SelectItem>
                ))}
            </SelectContent>
          </Select>
        )}
      </FormRow>
      <FormRow
        label='Terrain seed'
        description='The same seed always raises the same coasts and peaks.'
      >
        {(id) => (
          <Input
            id={id}
            value={draft.terrainSeed}
            maxLength={SEED_MAX}
            onChange={(event) => set('terrainSeed', event.target.value)}
          />
        )}
      </FormRow>
      <FormRow label='Sea' description='Percent of the surface under water.'>
        {(id) => (
          <Input
            id={id}
            type='number'
            min={0}
            max={PERCENT}
            inputMode='numeric'
            value={draft.sea}
            onChange={(event) => set('sea', event.target.value)}
          />
        )}
      </FormRow>
      <FormRow label='Mountains' description='Percent of the land raised high.'>
        {(id) => (
          <Input
            id={id}
            type='number'
            min={0}
            max={PERCENT}
            inputMode='numeric'
            value={draft.mountains}
            onChange={(event) => set('mountains', event.target.value)}
          />
        )}
      </FormRow>
      <FormRow
        label='Moisture'
        description='From -100 parched to 100 drenched.'
      >
        {(id) => (
          <Input
            id={id}
            type='number'
            min={-PERCENT}
            max={PERCENT}
            inputMode='numeric'
            value={draft.moisture}
            onChange={(event) => set('moisture', event.target.value)}
          />
        )}
      </FormRow>
      <FormRow label='Description'>
        {(id) => (
          <Textarea
            id={id}
            value={draft.description}
            onChange={(event) => set('description', event.target.value)}
          />
        )}
      </FormRow>
      <FormRow label='Cosmology'>
        {(id) => (
          <Textarea
            id={id}
            value={draft.cosmology}
            onChange={(event) => set('cosmology', event.target.value)}
          />
        )}
      </FormRow>
      <FormRow
        label='Image prompt'
        description='Used when drawing its picture; leave blank to delete.'
      >
        {(id) => (
          <Textarea
            id={id}
            value={draft.imagePrompt}
            onChange={(event) => set('imagePrompt', event.target.value)}
          />
        )}
      </FormRow>
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <CosmicActionButton
          actionId='world:edit'
          label='Reshape the world'
          icon={Save}
          variant='default'
          pending={edit.isPending}
          blockedReason={
            invalid ??
            (Object.keys(body).length <= 1 && !body.automatic_mortal_agents
              ? 'Nothing has changed yet.'
              : undefined)
          }
          onRun={() => edit.mutate(body)}
        />
      </div>
      {redrawDue && (
        <div className='flex min-w-0 flex-wrap items-center gap-2'>
          <CosmicActionButton
            actionId='world:map'
            label='Redraw the map now'
            icon={RefreshCw}
            pending={redraw.isPending}
            onRun={() => redraw.mutate()}
          />
          <Muted variant='caption'>
            The land changed; its map follows the new terrain once redrawn.
          </Muted>
        </div>
      )}
      <FormRow
        label='Orbit'
        description={`The world moves only if you choose a new orbit; ${currentOrbit}.`}
      >
        {(id) => (
          <>
            <Select
              value={orbit}
              onValueChange={setOrbit}
              open={orbitOpen}
              onOpenChange={setOrbitOpen}
            >
              <SelectTrigger id={id} className='w-full'>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={KEEP}>Do not move</SelectItem>
                <StarOptions
                  stars={index.data.stars}
                  selected={orbit}
                  open={orbitOpen}
                  valueOf={(star) => `star:${star.id}`}
                  label={(star) =>
                    `Around ${star.name} · ${STAR_TYPE_LABEL[star.star_type]}`
                  }
                  disabled={(star) => !parent && star.id === world.star_id}
                />
                {index.worlds
                  .filter(
                    (other) =>
                      other.world.id !== world.id &&
                      other.world.parent_world_id === null
                  )
                  .map((other) => (
                    <SelectItem
                      key={`moon-${other.world.id}`}
                      value={`moon:${other.world.id}`}
                      disabled={other.world.id === world.parent_world_id}
                    >
                      {`Moon of ${other.world.name}`}
                    </SelectItem>
                  ))}
              </SelectContent>
            </Select>
            <CosmicActionButton
              actionId='world:orbit'
              label='Move'
              icon={OrbitIcon}
              pending={move.isPending}
              blockedReason={
                orbit === KEEP ? 'Choose a new orbit first.' : undefined
              }
              onRun={() => move.mutate()}
            />
          </>
        )}
      </FormRow>
      <Muted variant='caption'>{`Mortal agents are capped at ${ruleText(cap)} per world (World rules › Intervention).`}</Muted>
    </div>
  )
}
