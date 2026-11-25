import { useState } from 'react'
import { Check, Eraser, Gem, ShieldAlert, TriangleAlert } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  AttributeTile,
  EmptyState,
  Medallion,
  Section,
  Paged,
  LoadingBlock,
} from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { useGodAction } from '@/features/pantheon/godAction'
import { AdjustPanel, PartHeader } from './EntityEconomy'
import { ECONOMY_REFRESH, useNodeMaterials } from './api'
import {
  FOE_NATURE,
  MATERIAL_FAMILY,
  MATERIAL_PROPERTIES,
  MATERIAL_SLOT,
  type MaterialSlot,
  slotEffect,
} from './labels'
import { iconTone, materialKey, materialRef, useBusy } from './model'
import { HeldBadge, MaterialSelect, ReleaseButton } from './parts'

type Slot = components['schemas']['MaterialSlotView']

const PERCENT = 100
const SLOT_PROPERTIES = MATERIAL_PROPERTIES.filter(
  (property) => property.key !== 'edge' && property.key !== 'conductivity'
)

function propertyTone(key: string) {
  if (key === 'corruption' || key === 'decay') return 'destructive'
  if (key === 'sanctity') return 'verdigris'
  return 'default'
}

function SlotEditor({
  nodeId,
  worldId,
  slot,
  current,
  held,
  busy,
}: {
  nodeId: number
  worldId: number | null
  slot: MaterialSlot
  current: string
  held: boolean
  busy: string | null
}) {
  const spec = MATERIAL_SLOT[slot]
  const [choice, setChoice] = useState(current)
  const [hold, setHold] = useState(held || current === '')
  const set = useGodAction({
    writes: [{ lever: 'node_material:set' }],
    invalidate: ECONOMY_REFRESH,
    run: () =>
      unwrap(
        api.POST('/api/actions/node_material:set', {
          body: { node_id: nodeId, slot, ...materialRef(choice), hold },
        })
      ),
  })
  const blocked =
    busy ??
    (set.isPending ? 'Working…' : null) ??
    (choice === '' ? 'Choose a material first.' : null)
  return (
    <AdjustPanel
      acts={[set]}
      label={`Set the ${spec.label.toLowerCase()}`}
      title={`${spec.label}: ${spec.note.toLowerCase()}`}
      note='Pick any material of the world or a substance only this world knows. Held, the makers keep to it.'
      hold={hold}
      onHold={setHold}
    >
      <MaterialSelect
        label={`${spec.label} material`}
        worldId={worldId}
        value={choice}
        blocked={busy}
        onPick={setChoice}
      />
      <Button
        act={set}
        size='sm'
        className='self-start'
        disabled={blocked !== null}
        disabledReason={blocked ?? undefined}
        onClick={() => set.mutate(undefined)}
      >
        <Check />
        {`Make the ${spec.label.toLowerCase()} of it`}
      </Button>
    </AdjustPanel>
  )
}

function SlotCard({
  nodeId,
  worldId,
  slot,
  readOnlyReason,
}: {
  nodeId: number
  worldId: number | null
  slot: Slot
  readOnlyReason?: string | null
}) {
  const release = useGodAction({
    writes: [{ lever: 'node_material:release' }],
    invalidate: ECONOMY_REFRESH,
    run: () =>
      unwrap(
        api.POST('/api/actions/node_material:release', {
          body: { node_id: nodeId, slot: slot.slot },
        })
      ),
  })
  const clear = useGodAction({
    writes: [{ lever: 'node_material:clear' }],
    invalidate: ECONOMY_REFRESH,
    run: () =>
      unwrap(
        api.POST('/api/actions/node_material:clear', {
          body: { node_id: nodeId, slot: slot.slot },
        })
      ),
  })
  const busy = useBusy(readOnlyReason, release.isPending, clear.isPending)
  const spec = MATERIAL_SLOT[slot.slot]
  const family = MATERIAL_FAMILY[slot.family]
  const effects = Object.entries(slot.effects)
  return (
    <li
      data-slot={slot.slot}
      className='@container/slot flex h-full min-w-0 flex-col gap-3 rounded-md border surface-framed border-gild/70 bg-card p-4'
    >
      <div className='flex min-w-0 items-start gap-3'>
        <Medallion icon={spec.icon} tone={family.tone} />
        <div className='flex min-w-0 flex-1 flex-col gap-1.5'>
          <Text weight='semibold' truncate>
            {`${spec.label} of ${slot.label.toLowerCase()}`}
          </Text>
          <div className='flex min-w-0 flex-wrap gap-1.5'>
            <Badge size='sm' variant='outline'>
              <family.icon />
              {family.label}
            </Badge>
            <HeldBadge held={slot.held} />
          </div>
        </div>
      </div>
      {effects.length > 0 && (
        <ul className='grid min-w-0 grid-cols-1 gap-1.5 @lg/slot:grid-cols-2'>
          <Paged items={effects} as='li'>
            {([key, value]) => {
              const effect = slotEffect(key, value)
              return (
                <li
                  key={key}
                  data-effect={key}
                  className='flex min-w-0 items-center gap-2 rounded-md border surface-well border-gild/20 bg-muted/60 px-2 py-1.5'
                >
                  <effect.icon
                    aria-hidden='true'
                    className={cn(
                      'size-icon-xs shrink-0',
                      iconTone(effect.tone)
                    )}
                  />
                  <Text as='span' variant='caption'>
                    {effect.text}
                  </Text>
                </li>
              )
            }}
          </Paged>
        </ul>
      )}
      <div className='grid min-w-0 grid-cols-2 gap-1.5 @md/slot:grid-cols-4'>
        {SLOT_PROPERTIES.map((property) => (
          <AttributeTile
            key={property.key}
            icon={property.icon}
            abbr={property.abbr}
            label={property.label}
            value={slot[property.key as keyof Slot] as number}
            max={PERCENT}
            hint={property.hint}
            tone={propertyTone(property.key)}
          />
        ))}
      </div>
      <div className='mt-auto flex min-w-0 flex-col gap-3'>
        <div className='flex min-w-0 flex-wrap gap-2'>
          <ReleaseButton
            act={release}
            held={slot.held}
            busy={busy}
            onRelease={() => release.mutate(undefined)}
          />
          <Button
            act={clear}
            size='sm'
            variant='outline'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => clear.mutate(undefined)}
          >
            <Eraser />
            Let its makers choose
          </Button>
        </div>
        <SlotEditor
          key={`${slot.material ?? ''}-${slot.world_material_id ?? ''}-${slot.held}`}
          nodeId={nodeId}
          worldId={worldId}
          slot={slot.slot}
          current={materialKey(slot)}
          held={slot.held}
          busy={busy}
        />
      </div>
    </li>
  )
}

function OpenSlot({
  nodeId,
  worldId,
  slot,
  readOnlyReason,
}: {
  nodeId: number
  worldId: number | null
  slot: MaterialSlot
  readOnlyReason?: string | null
}) {
  const busy = useBusy(readOnlyReason)
  const spec = MATERIAL_SLOT[slot]
  return (
    <li
      data-slot={slot}
      className='flex h-full min-w-0 flex-col gap-3 rounded-md p-4 sealed-well'
    >
      <div className='flex min-w-0 items-start gap-3'>
        <Medallion icon={spec.icon} tone='muted' />
        <div className='flex min-w-0 flex-1 flex-col gap-0.5'>
          <Text weight='semibold'>{spec.label}</Text>
          <Muted variant='caption'>
            {`${spec.note}: not chosen yet. Its makers pick from what their stores hold.`}
          </Muted>
        </div>
      </div>
      <SlotEditor
        nodeId={nodeId}
        worldId={worldId}
        slot={slot}
        current=''
        held={false}
        busy={busy}
      />
    </li>
  )
}

export function NodeMaterials({
  nodeId,
  readOnlyReason,
}: {
  nodeId: number
  readOnlyReason?: string | null
}) {
  const view = useNodeMaterials(nodeId)
  return (
    <Section
      id='section-node-materials'
      title='What it is made of'
      description='The material of each part sets its worth, its wear, how it cuts and guards, and how holy weapons fare against what it faces.'
      icon={Gem}
    >
      {view.isPending && <LoadingBlock label='Reading its materials' />}
      {view.isError && (
        <EmptyState
          icon={TriangleAlert}
          title='Its materials could not be read'
          description={view.error.message}
        />
      )}
      {view.data && (
        <div
          data-surface='NodeMaterials'
          className='@container/nodemat flex min-w-0 flex-col gap-4'
        >
          {view.data.foe_natures.length > 0 && (
            <PartHeader
              icon={ShieldAlert}
              tone='danger'
              title='Unholy foe'
              note='Holy weapons harm it more; sanctity in a blade bites deeper.'
              aside={
                <div className='flex min-w-0 flex-wrap gap-1.5'>
                  <Paged items={view.data.foe_natures}>
                    {(nature) => {
                      const look = FOE_NATURE[nature]
                      return (
                        <Badge key={nature} variant='destructive'>
                          <look.icon />
                          {look.label}
                        </Badge>
                      )
                    }}
                  </Paged>
                </div>
              }
            />
          )}
          {view.data.slots.length === 0 && view.data.open_slots.length === 0 ? (
            <EmptyState
              icon={Gem}
              title='No parts to make'
              description='Nothing about it is made of a material.'
            />
          ) : (
            <ul className='grid min-w-0 grid-cols-1 gap-3 @3xl/nodemat:grid-cols-2'>
              <Paged items={view.data.slots} as='li'>
                {(slot) => (
                  <SlotCard
                    key={slot.slot}
                    nodeId={nodeId}
                    worldId={view.data.world_id}
                    slot={slot}
                    readOnlyReason={readOnlyReason}
                  />
                )}
              </Paged>
              <Paged items={view.data.open_slots}>
                {(slot) => (
                  <OpenSlot
                    key={slot}
                    nodeId={nodeId}
                    worldId={view.data.world_id}
                    slot={slot}
                    readOnlyReason={readOnlyReason}
                  />
                )}
              </Paged>
            </ul>
          )}
        </div>
      )}
    </Section>
  )
}
