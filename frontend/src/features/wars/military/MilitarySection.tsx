import { useState } from 'react'
import { Eye, Save, Shield, Swords, Trash2, TriangleAlert } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { commanderTraitValues, spyCoverValues } from '@/api/generated/schema'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import { EmptyState, Section, StatBar } from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { MindPicker } from '@/features/entity/mind/parts'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { ArmyPanel, NumberBox } from './ArmyPanel'
import { CohortRow, OccupationRow } from './WarRoom'
import {
  type CommanderTrait,
  type MilitaryOverview,
  type SpyNetwork,
  table,
  useArmyCard,
  useMilitary,
  words,
} from './api'

const PERCENT = 100
const WORKING = 'Working…'
const NETWORK_NUMBERS = ['agents', 'depth', 'exposure', 'intel'] as const
type NetworkNumber = (typeof NETWORK_NUMBERS)[number]

function NetworkRow({
  network,
  blocked,
}: {
  network: SpyNetwork
  blocked: string | null
}) {
  const [numbers, setNumbers] = useState<Record<NetworkNumber, string>>(
    () =>
      Object.fromEntries(
        NETWORK_NUMBERS.map((key) => [key, String(network[key])])
      ) as Record<NetworkNumber, string>
  )
  const [cover, setCover] = useState<string>(network.cover)
  const save = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/spy:edit_network', {
          body: {
            network_id: network.id,
            values: {
              ...Object.fromEntries(
                NETWORK_NUMBERS.map((key) => [
                  key,
                  Math.max(
                    0,
                    Math.min(
                      key === 'agents' ? Number.MAX_SAFE_INTEGER : PERCENT,
                      Math.round(Number(numbers[key]) || 0)
                    )
                  ),
                ])
              ),
              cover,
            },
            dismantle: false,
          },
        })
      ),
  })
  const roll = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/spy:edit_network', {
          body: { network_id: network.id, dismantle: true },
        })
      ),
  })
  const busy = blocked ?? (save.isPending || roll.isPending ? WORKING : null)
  return (
    <li
      data-surface='SpyNetwork'
      className='flex min-w-0 flex-col gap-2 rounded-lg border bg-muted/30 p-3'
    >
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Eye
          aria-hidden='true'
          className='size-icon-sm text-muted-foreground'
        />
        <Text as='span'>{`${network.owner?.name ?? ''} → ${network.target?.name ?? ''}`}</Text>
        <Badge variant='outline'>{`as ${words(network.cover)}`}</Badge>
        {network.spymaster && (
          <Badge variant='outline'>{`Spymaster ${network.spymaster.name}`}</Badge>
        )}
        {network.last_operation && (
          <Badge variant='info'>{`${words(network.last_operation)} (${network.last_epoch ?? ''})`}</Badge>
        )}
      </div>
      <div className='grid min-w-0 grid-cols-1 gap-3 md:grid-cols-3'>
        <StatBar label='Depth' value={network.depth} max={PERCENT} />
        <StatBar
          label='Exposure'
          value={network.exposure}
          max={PERCENT}
          tone='warning'
        />
        <StatBar
          label='Intelligence'
          value={network.intel}
          max={PERCENT}
          tone='info'
        />
      </div>
      <div className='flex min-w-0 flex-wrap items-end gap-2'>
        {NETWORK_NUMBERS.map((key) => (
          <NumberBox
            key={key}
            label={words(key)}
            value={numbers[key]}
            onChange={(value) =>
              setNumbers((current) => ({ ...current, [key]: value }))
            }
          />
        ))}
        <MindPicker
          label='Cover'
          value={cover}
          table={table(spyCoverValues)}
          blocked={busy}
          onPick={setCover}
        />
        <Button
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => save.mutate(undefined)}
        >
          <Save />
          Save
        </Button>
        <Button
          size='sm'
          variant='outline'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => roll.mutate(undefined)}
        >
          <Trash2 />
          Roll it up
        </Button>
      </div>
    </li>
  )
}

function TraitToggle({
  mortalId,
  trait,
  held,
  blocked,
}: {
  mortalId: number
  trait: CommanderTrait
  held: boolean
  blocked: string | null
}) {
  const toggle = useGodAction<boolean>({
    run: (next) =>
      unwrap(
        api.POST('/api/actions/commander:trait', {
          body: { mortal_id: mortalId, trait, held: next },
        })
      ),
  })
  const busy = blocked ?? (toggle.isPending ? WORKING : null)
  return (
    <label className='flex items-center gap-2'>
      <Switch
        checked={held}
        disabled={busy !== null}
        aria-label={words(trait)}
        onCheckedChange={(next) => toggle.mutate(next)}
      />
      <Text as='span'>{words(trait)}</Text>
    </label>
  )
}

function Overview({
  entityId,
  data,
  mortal,
  blocked,
}: {
  entityId: number
  data: MilitaryOverview
  mortal: boolean
  blocked: string | null
}) {
  const empty =
    !mortal &&
    data.armies.length +
      data.captives_held.length +
      data.captives_lost.length +
      data.networks.length +
      data.watched_by.length +
      data.occupying.length +
      data.occupied.length ===
      0
  if (empty)
    return (
      <Muted>
        No armies, captives, spies or occupations touch this record.
      </Muted>
    )
  return (
    <div
      data-surface='MilitaryOverview'
      className='flex min-w-0 flex-col gap-4'
    >
      {mortal && (
        <div
          data-surface='CommanderTraits'
          className='flex min-w-0 flex-col gap-2'
        >
          <Label variant='overline'>Battle traits</Label>
          <div className='grid min-w-0 grid-cols-2 gap-2 md:grid-cols-5'>
            {commanderTraitValues.map((trait) => (
              <TraitToggle
                key={trait}
                mortalId={entityId}
                trait={trait}
                held={data.commander_traits.includes(trait)}
                blocked={blocked}
              />
            ))}
          </div>
        </div>
      )}
      {data.armies.map((army) => (
        <ArmyPanel key={army.army?.id} army={army} blocked={blocked} />
      ))}
      {[...data.captives_held, ...data.captives_lost].length > 0 && (
        <>
          <Label variant='overline'>Captives</Label>
          <ul className='flex min-w-0 flex-col gap-2'>
            {[...data.captives_held, ...data.captives_lost].map((cohort) => (
              <CohortRow key={cohort.id} cohort={cohort} blocked={blocked} />
            ))}
          </ul>
        </>
      )}
      {[...data.networks, ...data.watched_by].length > 0 && (
        <>
          <Label variant='overline'>Spy networks</Label>
          <ul className='flex min-w-0 flex-col gap-2'>
            {[...data.networks, ...data.watched_by].map((network) => (
              <NetworkRow
                key={network.id}
                network={network}
                blocked={blocked}
              />
            ))}
          </ul>
        </>
      )}
      {[...data.occupying, ...data.occupied].length > 0 && (
        <>
          <Label variant='overline'>Occupations</Label>
          <ul className='flex min-w-0 flex-col gap-2'>
            {[...data.occupying, ...data.occupied].map((item) => (
              <OccupationRow
                key={item.region?.id}
                occupation={item}
                blocked={blocked}
              />
            ))}
          </ul>
        </>
      )}
    </div>
  )
}

export function MilitarySection({
  entityId,
  kind,
  readOnlyReason,
}: {
  entityId: number
  kind: string
  readOnlyReason?: string | null
}) {
  const army = kind === 'army'
  const card = useArmyCard(entityId, army)
  const overview = useMilitary(entityId, !army)
  const { reason } = useGodGate()
  const blocked = readOnlyReason ?? reason()
  const query = army ? card : overview
  return (
    <Section
      id='section-military'
      title={army ? 'Army' : 'War and captivity'}
      description={
        army
          ? 'Stacks, orders, supplies and marches.'
          : 'Armies, captives, spies and occupied lands.'
      }
      icon={army ? Swords : Shield}
    >
      {query.isPending && <Muted>Reading the rolls…</Muted>}
      {query.isError && (
        <EmptyState
          icon={TriangleAlert}
          title='Nothing could be read'
          description={query.error.message}
        />
      )}
      {army && card.data && <ArmyPanel army={card.data} blocked={blocked} />}
      {!army && overview.data && (
        <Overview
          entityId={entityId}
          data={overview.data}
          mortal={kind === 'mortal'}
          blocked={blocked}
        />
      )}
    </Section>
  )
}
