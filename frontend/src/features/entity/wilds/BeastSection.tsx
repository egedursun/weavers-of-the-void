import { useState } from 'react'
import {
  Check,
  Footprints,
  Gem,
  Moon,
  Network,
  Sun,
  TriangleAlert,
  Users,
  Link as LinkIcon,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import {
  beastTemperValues,
  domesticationStageValues,
  sizeClassValues,
} from '@/api/generated/schema'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Switch } from '@/components/ui/switch'
import {
  EmptyState,
  EntityLink,
  KpiTile,
  Section,
  StatBar,
  Timeline,
  TimelineItem,
} from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { EntityPicker } from '@/features/cosmos/EntityPicker'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { DictField, type FieldSpec, LoreFields } from '../lore/LoreFields'
import { table, words } from '../lore/api'
import { PERCENT, busyOf } from '../lore/model'
import { MindPicker } from '../mind/parts'
import {
  type BeastCard,
  type HerdView,
  useBeast,
  useBeastEdit,
  useFoodWeb,
  useHerds,
} from './api'

type Ref = { id: number; name: string } | null | undefined

function Name({ item }: { item: Ref }) {
  if (!item) return <Muted as='span'>none</Muted>
  return (
    <EntityLink kind='entity' id={String(item.id)}>
      {item.name}
    </EntityLink>
  )
}

const FIELDS: FieldSpec[] = [
  { key: 'temper', kind: 'enum', values: beastTemperValues },
  { key: 'size_class', kind: 'enum', values: sizeClassValues },
  { key: 'endurance', kind: 'number', min: 0, max: PERCENT },
  { key: 'perception', kind: 'number', min: 0, max: PERCENT },
  { key: 'willpower', kind: 'number', min: 0, max: PERCENT },
  { key: 'intelligence', kind: 'number', min: 0, max: PERCENT },
  { key: 'age', kind: 'number', min: 0 },
  { key: 'lifespan', kind: 'number', min: 1 },
  { key: 'raids', kind: 'number', min: 0 },
]

function Controls({
  id,
  card,
  blocked,
}: {
  id: number
  card: BeastCard
  blocked: string | null
}) {
  const [holder, setHolder] = useState<number | null>(null)
  const [tamed, setTamed] = useState(false)
  const [lair, setLair] = useState<number | null>(null)
  const rouse = useGodAction<boolean>({
    run: (awake) =>
      unwrap(
        api.POST('/api/actions/beast:rouse', { body: { beast_id: id, awake } })
      ),
  })
  const bind = useGodAction<number | null>({
    run: (node) =>
      unwrap(
        api.POST('/api/actions/beast:bind', {
          body: { beast_id: id, node_id: node, tamed },
        })
      ),
  })
  const move = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/beast:lair', {
          body: { beast_id: id, place_id: lair ?? 0 },
        })
      ),
  })
  const busy = busyOf(blocked, rouse.isPending, bind.isPending, move.isPending)
  return (
    <div data-surface='BeastControls' className='flex min-w-0 flex-col gap-2'>
      <div className='flex min-w-0 flex-wrap gap-2'>
        <Button
          size='sm'
          variant='outline'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => rouse.mutate(true)}
        >
          <Sun />
          Wake it
        </Button>
        <Button
          size='sm'
          variant='outline'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => rouse.mutate(false)}
        >
          <Moon />
          Lull it
        </Button>
        {card.bound_to && (
          <Button
            size='sm'
            variant='outline'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => bind.mutate(null)}
          >
            Loose it
          </Button>
        )}
      </div>
      <div className='flex min-w-0 flex-wrap items-end gap-2'>
        <EntityPicker
          types={['mortal', 'settlement', 'people', 'cult', 'army', 'place']}
          value={holder}
          onChange={setHolder}
          placeholder='Bind it to…'
        />
        <label className='flex items-center gap-2'>
          <Switch
            checked={tamed}
            aria-label='Tamed as a mount'
            onCheckedChange={setTamed}
          />
          <Text as='span'>as a mount</Text>
        </label>
        <Button
          size='sm'
          variant='outline'
          disabled={busy !== null || holder === null}
          disabledReason={
            busy ?? (holder === null ? 'Choose a master' : undefined)
          }
          onClick={() => bind.mutate(holder)}
        >
          <LinkIcon />
          Bind
        </Button>
        <EntityPicker
          types={['place', 'region']}
          value={lair}
          onChange={setLair}
          placeholder='Move its lair to…'
        />
        <Button
          size='sm'
          variant='outline'
          disabled={busy !== null || lair === null}
          disabledReason={
            busy ?? (lair === null ? 'Choose a place' : undefined)
          }
          onClick={() => move.mutate(undefined)}
        >
          <Footprints />
          Shift the lair
        </Button>
      </div>
    </div>
  )
}

function Body({
  id,
  card,
  blocked,
}: {
  id: number
  card: BeastCard
  blocked: string | null
}) {
  const edit = useBeastEdit(id)
  return (
    <div data-surface='BeastCard' className='flex min-w-0 flex-col gap-3'>
      <div className='grid min-w-0 grid-cols-2 gap-3 md:grid-cols-4'>
        <KpiTile
          label='Terror'
          value={card.terror}
          icon={TriangleAlert}
          tone='danger'
          meter={{ value: card.terror, max: PERCENT, label: 'terror' }}
        />
        <KpiTile label='Renown' value={card.renown} icon={Gem} tone='gold' />
        <KpiTile
          label='Raids'
          value={card.raids}
          icon={Footprints}
          tone='warning'
        />
        <KpiTile
          label='Age'
          value={`${card.age} / ${card.lifespan}`}
          icon={Moon}
          tone='muted'
        />
      </div>
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Badge variant='info'>{words(card.temper)}</Badge>
        <Text as='span'>
          of <Name item={card.species} />
        </Text>
        <Text as='span'>
          lairs at <Name item={card.lair} />
        </Text>
        {card.bound_to && (
          <Text as='span'>
            bound to <Name item={card.bound_to} />
          </Text>
        )}
      </div>
      <LoreFields
        entityId={id}
        surface='BeastForm'
        fields={FIELDS}
        current={card}
        locked={card.locked}
        blocked={blocked}
        editor={edit}
      />
      <DictField
        entityId={id}
        spec={{ key: 'hoard', label: 'Its hoard', value: card.hoard }}
        blocked={blocked}
        suggestions={[
          'luxuries',
          'livestock',
          'grain',
          'weapons',
          'sacred_goods',
        ]}
        editor={edit}
      />
      <Controls id={id} card={card} blocked={blocked} />
      <div data-surface='BeastBody' className='flex min-w-0 flex-col gap-2'>
        <Label variant='overline'>{`Body${card.body_plan ? `: ${words(card.body_plan)}` : ''}, ${card.hp} hp`}</Label>
        {card.injuries.length === 0 ? (
          <Muted>It bears no wounds.</Muted>
        ) : (
          <ul className='flex min-w-0 flex-col gap-1'>
            {card.injuries.map((row, index) => (
              <li
                key={`${row.part}.${index}`}
                className='flex min-w-0 flex-wrap items-center gap-2'
              >
                <Badge
                  variant={row.state === 'healed' ? 'outline' : 'destructive'}
                >
                  {words(row.kind)}
                </Badge>
                <Text as='span'>{words(row.part)}</Text>
                <div className='min-w-0 flex-1'>
                  <StatBar
                    label={`${words(row.state)}, severity ${row.severity}`}
                    value={row.function_loss}
                    max={PERCENT}
                  />
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
      <div data-surface='BeastWounds' className='flex min-w-0 flex-col gap-2'>
        <Label variant='overline'>Who wounded it</Label>
        {card.wounds.length === 0 ? (
          <Muted>No one has drawn its blood.</Muted>
        ) : (
          <Timeline label='Wounds'>
            {card.wounds.map((row, index) => (
              <TimelineItem
                key={`${row.epoch}.${index}`}
                icon={TriangleAlert}
                tone='destructive'
                title={row.by?.name ?? 'someone'}
                timestamp={`epoch ${row.epoch}`}
                last={index === card.wounds.length - 1}
              />
            ))}
          </Timeline>
        )}
      </div>
    </div>
  )
}

export function BeastSection({
  beastId,
  readOnlyReason,
}: {
  beastId: number
  readOnlyReason?: string | null
}) {
  const view = useBeast(beastId)
  const { reason } = useGodGate()
  const blocked = readOnlyReason ?? reason()
  return (
    <Section
      id='section-beast'
      title='The beast'
      description='Its body, temper, lair, hoard and the wounds it remembers.'
      icon={Footprints}
    >
      {view.isPending && <Muted>Reading the beast…</Muted>}
      {view.isError && (
        <EmptyState
          icon={TriangleAlert}
          title='The beast could not be read'
          description={view.error.message}
        />
      )}
      {view.data && <Body id={beastId} card={view.data} blocked={blocked} />}
    </Section>
  )
}

function HerdRow({
  community,
  row,
  blocked,
}: {
  community: number
  row: HerdView
  blocked: string | null
}) {
  const [head, setHead] = useState(String(row.head))
  const [stage, setStage] = useState<string>(row.stage)
  const save = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/herd:edit', {
          body: {
            community_id: community,
            species_id: row.species?.id ?? 0,
            values: { head: Math.max(0, Math.round(Number(head) || 0)), stage },
          },
        })
      ),
  })
  const busy = busyOf(blocked, save.isPending)
  return (
    <li
      data-surface='HerdRow'
      className='flex min-w-0 flex-wrap items-end gap-2 rounded-lg border bg-muted/30 p-2'
    >
      <Name item={row.species} />
      <Muted
        as='span'
        variant='caption'
      >{`kept since epoch ${row.since_epoch}, fed ${row.fed_epochs} epochs`}</Muted>
      <MindPicker
        label='Stage'
        value={stage}
        table={table(domesticationStageValues)}
        blocked={busy}
        onPick={setStage}
      />
      <Input
        className='w-24'
        type='number'
        min={0}
        value={head}
        aria-label='head'
        onChange={(event) => setHead(event.target.value)}
      />
      <Button
        size='icon'
        variant='ghost'
        aria-label='Set the herd'
        disabled={busy !== null}
        disabledReason={busy ?? undefined}
        onClick={() => save.mutate(undefined)}
      >
        <Check />
      </Button>
    </li>
  )
}

export function HerdsSection({
  communityId,
  readOnlyReason,
}: {
  communityId: number
  readOnlyReason?: string | null
}) {
  const view = useHerds(communityId)
  const { reason } = useGodGate()
  const blocked = readOnlyReason ?? reason()
  if (!view.data || view.data.length === 0) return null
  return (
    <Section
      id='section-herds'
      title='Herds'
      description='The beasts this community keeps, feeds and breeds.'
      icon={Users}
    >
      <ul className='flex min-w-0 flex-col gap-2'>
        {view.data.map((row) => (
          <HerdRow
            key={row.species?.id}
            community={communityId}
            row={row}
            blocked={blocked}
          />
        ))}
      </ul>
    </Section>
  )
}

export function FoodWebSection({ regionId }: { regionId: number }) {
  const view = useFoodWeb(regionId)
  if (!view.data || view.data.nodes.length === 0) return null
  const names = new Map(
    view.data.nodes.map((node) => [node.species.id, node.species.name])
  )
  return (
    <Section
      id='section-food-web'
      title='Food web'
      description='The kinds of this land, how many, and who eats whom.'
      icon={Network}
    >
      <ul
        data-surface='FoodWebNodes'
        className='grid min-w-0 grid-cols-1 gap-2 md:grid-cols-2'
      >
        {view.data.nodes.map((node) => (
          <li
            key={node.species.id}
            className='flex min-w-0 flex-col gap-1 rounded-lg border bg-muted/30 p-2'
          >
            <div className='flex min-w-0 flex-wrap items-center gap-2'>
              <Name item={node.species} />
              <Badge variant='outline'>{`${words(node.size_class)} ${words(node.diet)}`}</Badge>
            </div>
            <StatBar label='abundance' value={node.abundance} max={PERCENT} />
          </li>
        ))}
      </ul>
      <ul data-surface='FoodWebLinks' className='flex min-w-0 flex-col gap-1'>
        {view.data.links.map((link) => (
          <li key={`${link.hunter_id}.${link.prey_id}`}>
            <Text as='span'>{`${names.get(link.hunter_id) ?? '?'} hunts ${names.get(link.prey_id) ?? '?'}`}</Text>
          </li>
        ))}
      </ul>
    </Section>
  )
}
