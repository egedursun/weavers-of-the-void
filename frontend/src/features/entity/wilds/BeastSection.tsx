import { useState } from 'react'
import {
  ArrowRight,
  Check,
  Coins,
  Crosshair,
  Flame,
  Footprints,
  Gem,
  HeartPulse,
  Hourglass,
  Link as LinkIcon,
  MapPin,
  Moon,
  PawPrint,
  ShieldAlert,
  Sun,
  Swords,
  TriangleAlert,
  Unlock,
  Wheat,
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
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { Progress } from '@/components/ui/progress'
import {
  EmptyState,
  KpiTile,
  Medallion,
  MiniStat,
  Section,
  StatBar,
  Timeline,
  TimelineItem,
  Paged,
  LoadingBlock,
} from '@/components/domain'
import { Label, Muted, Stat, Text } from '@/components/typography'
import { EntityPicker } from '@/features/cosmos/EntityPicker'
import { AdjustStats } from '@/features/pantheon/AdjustStats'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { INJURIES, PLANS, STATES } from '../body/labels'
import { COMMODITY } from '../economy/labels'
import { PERCENT, busyOf } from '../lore/model'
import { MindPicker } from '../mind/parts'
import {
  Abilities,
  SlayControl,
  TreasureControls,
  Treasures,
} from './BeastExtras'
import { FoodWebGraph } from './FoodWebGraph'
import { HerdDrop } from './WildControls'
import {
  type BeastCard,
  type HerdView,
  useBeast,
  useBeastEdit,
  useFoodWeb,
  useHerds,
} from './api'
import {
  BADGE_OF,
  BEAST_ICON,
  DIET,
  HERDS_ICON,
  MIGHT,
  SIZE,
  STAGE,
  TEMPER,
  WEB_ICON,
  barTone,
  fieldLabel,
  named,
  titled,
} from './labels'
import {
  AdjustPanel,
  Card,
  Group,
  Held,
  Name,
  NumberField,
  ShareEditor,
  StageTrack,
  SwitchField,
} from './parts'

type Blocked = { id: number; card: BeastCard; blocked: string | null }

const HOARD = COMMODITY as Record<string, (typeof COMMODITY)['grain']>
const MASTERS = [
  'mortal',
  'settlement',
  'people',
  'cult',
  'army',
  'place',
] as const

function pickTable(
  values: readonly string[],
  table: Record<string, { label: string }>
): Record<string, string> {
  return Object.fromEntries(
    values.map((key) => [key, table[key]?.label ?? titled(key)])
  )
}

function editBeast(id: number, key: string, value: number) {
  return unwrap(
    api.POST('/api/actions/beast:edit', {
      body: {
        beast_id: id,
        values: { [key]: value } as Record<string, never>,
        release: [],
      },
    })
  )
}

function BeastHero({ card }: { card: BeastCard }) {
  const temper = named(TEMPER, card.temper)
  const size = named(SIZE, card.size_class)
  const plan = card.body_plan ? named(PLANS, card.body_plan) : null
  return (
    <div className='flex min-w-0 items-center gap-3 rounded-lg border bg-background p-3'>
      <Medallion icon={temper.icon} tone={temper.tone ?? 'warning'} />
      <div className='flex min-w-0 flex-1 flex-col gap-1.5'>
        <Text weight='semibold'>
          {[size.label, plan?.label.toLowerCase(), 'great beast']
            .filter(Boolean)
            .join(' ')}
        </Text>
        <Muted variant='caption'>{TEMPER[card.temper]?.hint ?? ''}</Muted>
        <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
          <Badge size='sm' variant={BADGE_OF[temper.tone ?? 'warning']}>
            <temper.icon />
            {temper.label}
          </Badge>
          <Badge size='sm' variant='secondary'>
            <size.icon />
            {size.label}
          </Badge>
          <Badge size='sm' variant='destructive'>
            <HeartPulse />
            {`${card.hp} hit points`}
          </Badge>
          {card.woke_epoch !== null && card.temper !== 'sleeping' && (
            <Badge size='sm' variant='warning'>
              <Sun />
              {`Awake since epoch ${card.woke_epoch}`}
            </Badge>
          )}
        </div>
      </div>
    </div>
  )
}

function BeastVitals({ card }: { card: BeastCard }) {
  const left = Math.max(0, card.lifespan - card.age)
  return (
    <div className='grid min-w-0 grid-cols-1 gap-3 @xs/wild:grid-cols-2 @lg/wild:grid-cols-4'>
      <KpiTile
        label='Terror'
        value={card.terror}
        icon={TriangleAlert}
        tone='danger'
        hint='How much the land fears it'
        meter={{ value: card.terror, max: PERCENT, label: 'Terror' }}
      />
      <KpiTile
        label='Renown'
        value={card.renown}
        icon={Gem}
        tone='gold'
        hint='How far its tale has spread'
        meter={{ value: card.renown, max: PERCENT, label: 'Renown' }}
      />
      <KpiTile
        label='Raids'
        value={card.raids}
        icon={Flame}
        tone='warning'
        hint='Times it has fallen on herds and towns'
      />
      <KpiTile
        label='Age'
        value={card.age}
        icon={Hourglass}
        tone='muted'
        hint={`Of ${card.lifespan} years; ${left} left`}
        meter={{
          value: card.age,
          max: Math.max(1, card.lifespan),
          label: 'Age against its lifespan',
        }}
      />
    </div>
  )
}

function Might({ card }: { card: BeastCard }) {
  return (
    <Card title='Its might' icon={Swords} tone='danger'>
      {MIGHT.map((item) => (
        <StatBar
          key={item.key}
          label={item.label}
          value={card[item.key]}
          max={PERCENT}
          icon={item.icon}
          tone={item.tone}
        />
      ))}
    </Card>
  )
}

function Domain({ card }: { card: BeastCard }) {
  const rows = [
    { icon: PawPrint, label: 'Of the kind', item: card.species, empty: 'None' },
    { icon: MapPin, label: 'Lairs at', item: card.lair, empty: 'Roams free' },
    {
      icon: LinkIcon,
      label: 'Bound to',
      item: card.bound_to,
      empty: 'No master',
    },
  ]
  return (
    <Card title='Lair and masters' icon={MapPin} tone='info'>
      <ul className='flex min-w-0 flex-col gap-2'>
        <Paged items={rows} as='li'>
          {(row) => (
            <li
              key={row.label}
              className='flex min-w-0 items-center gap-2 rounded-lg border bg-muted/30 p-2'
            >
              <Medallion icon={row.icon} tone='info' size='sm' />
              <div className='flex min-w-0 flex-1 flex-col'>
                <Label truncate>{row.label}</Label>
                <Name item={row.item} fallback={row.empty} />
              </div>
            </li>
          )}
        </Paged>
      </ul>
    </Card>
  )
}

function Hoard({ card }: { card: BeastCard }) {
  const rows = Object.entries(card.hoard).sort(([, a], [, b]) => b - a)
  const total = rows.reduce((sum, [, amount]) => sum + amount, 0)
  return (
    <Card
      title='Its hoard'
      icon={Coins}
      tone='gold'
      hint={rows.length > 0 ? `${total} goods heaped in its lair` : undefined}
      wide
    >
      {rows.length === 0 ? (
        <Muted>It hoards nothing.</Muted>
      ) : (
        <div className='grid min-w-0 grid-cols-1 gap-2 @sm/card:grid-cols-2 @xl/card:grid-cols-3'>
          <Paged items={rows}>
            {([key, amount]) => {
              const goods = named(HOARD, key)
              return (
                <MiniStat
                  key={key}
                  icon={goods.icon}
                  label={goods.label}
                  value={amount}
                  tone='gold'
                />
              )
            }}
          </Paged>
        </div>
      )}
    </Card>
  )
}

function Wounds({ card }: { card: BeastCard }) {
  return (
    <Card
      title='Wounds and foes'
      icon={HeartPulse}
      tone='danger'
      hint={`${card.injuries.length} ${card.injuries.length === 1 ? 'wound' : 'wounds'} on its body, ${card.wounds.length} ${card.wounds.length === 1 ? 'blow' : 'blows'} remembered`}
      wide
    >
      <div className='grid min-w-0 grid-cols-1 gap-3 @lg/card:grid-cols-2'>
        <div className='flex min-w-0 flex-col gap-2'>
          <Label variant='overline'>On its body</Label>
          {card.injuries.length === 0 ? (
            <Muted>It bears no wounds.</Muted>
          ) : (
            <ul
              data-surface='BeastBody'
              className='flex min-w-0 flex-col gap-2'
            >
              <Paged items={card.injuries} as='li'>
                {(row, index) => {
                  const kind = named(INJURIES, row.kind)
                  const state = STATES[row.state]
                  return (
                    <li
                      key={`${row.part}.${index}`}
                      className='flex min-w-0 flex-col gap-2 rounded-lg border bg-muted/30 p-2'
                    >
                      <div className='flex min-w-0 items-center gap-2'>
                        <Medallion
                          icon={kind.icon}
                          tone={kind.tone ?? 'danger'}
                          size='sm'
                        />
                        <div className='flex min-w-0 flex-1 flex-col'>
                          <Text as='span' weight='medium' truncate>
                            {`${kind.label} on the ${titled(row.part).toLowerCase()}`}
                          </Text>
                          <Muted as='span' variant='caption'>
                            {`Severity ${row.severity} of 100`}
                          </Muted>
                        </div>
                        <Badge size='sm' variant={state?.badge ?? 'secondary'}>
                          {state?.label ?? titled(row.state)}
                        </Badge>
                      </div>
                      <StatBar
                        label='Use lost'
                        value={row.function_loss}
                        max={PERCENT}
                        tone='destructive'
                      />
                    </li>
                  )
                }}
              </Paged>
            </ul>
          )}
        </div>
        <div data-surface='BeastWounds' className='flex min-w-0 flex-col gap-2'>
          <Label variant='overline'>Who drew its blood</Label>
          {card.wounds.length === 0 ? (
            <Muted>No one has drawn its blood.</Muted>
          ) : (
            <Timeline label='Wounds'>
              <Paged items={card.wounds} as='li'>
                {(row, index) => (
                  <TimelineItem
                    key={`${row.epoch}.${index}`}
                    icon={Swords}
                    tone='destructive'
                    title={row.by?.name ?? 'Someone unknown'}
                    timestamp={`Epoch ${row.epoch}`}
                    last={index === card.wounds.length - 1}
                  />
                )}
              </Paged>
            </Timeline>
          )}
        </div>
      </div>
    </Card>
  )
}

function BeastControls({ id, card, blocked }: Blocked) {
  const edit = useBeastEdit(id)
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
  const busy = busyOf(
    blocked,
    edit.isPending,
    rouse.isPending,
    bind.isPending,
    move.isPending
  )
  return (
    <AdjustPanel
      title='Command the beast'
      note='Wake or lull it, bind it to a master, move its lair, fill its hoard or set any of its values. What you set is held until you let the world decide again.'
      head={
        <Held
          keys={card.locked}
          label={fieldLabel}
          busy={busy}
          onRelease={() =>
            edit.mutate({ values: {}, release: [...card.locked] })
          }
        />
      }
    >
      <div data-surface='BeastControls' className='flex min-w-0 flex-col gap-3'>
        <Group title='Temper and size' icon={ShieldAlert}>
          <div className='flex min-w-0 flex-wrap items-end gap-3'>
            <MindPicker
              label='Temper'
              value={card.temper}
              table={pickTable(beastTemperValues, TEMPER)}
              blocked={busy}
              onPick={(value) => edit.mutate({ values: { temper: value } })}
            />
            <MindPicker
              label='Size'
              value={card.size_class}
              table={pickTable(sizeClassValues, SIZE)}
              blocked={busy}
              onPick={(value) => edit.mutate({ values: { size_class: value } })}
            />
          </div>
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
          </div>
        </Group>
        <Group title='Masters and lair' icon={LinkIcon}>
          <div className='grid min-w-0 grid-cols-1 gap-3 @xl/wild:grid-cols-2'>
            <div className='flex min-w-0 flex-col gap-2'>
              <Label>Bind it to a master</Label>
              <EntityPicker
                types={MASTERS}
                value={holder}
                onChange={setHolder}
                placeholder='Choose a master…'
              />
              <div className='flex min-w-0 flex-wrap items-end gap-3'>
                <SwitchField
                  label='Tamed as a mount'
                  checked={tamed}
                  onChange={setTamed}
                />
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
                {card.bound_to && (
                  <Button
                    size='sm'
                    variant='outline'
                    disabled={busy !== null}
                    disabledReason={busy ?? undefined}
                    onClick={() => bind.mutate(null)}
                  >
                    <Unlock />
                    Loose it
                  </Button>
                )}
              </div>
            </div>
            <div className='flex min-w-0 flex-col gap-2'>
              <Label>Move its lair</Label>
              <EntityPicker
                types={['place', 'region']}
                value={lair}
                onChange={setLair}
                placeholder='Choose a place…'
              />
              <Button
                size='sm'
                variant='outline'
                className='self-start'
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
        </Group>
        <Group title='Its hoard' icon={Coins}>
          <ShareEditor
            key={JSON.stringify(card.hoard)}
            table={HOARD}
            value={card.hoard}
            amount='how many goods it heaps'
            busy={busy}
            addLabel='Add goods'
            onSave={(next) => edit.mutate({ values: { hoard: next } })}
          />
        </Group>
        <TreasureControls id={id} card={card} blocked={blocked} />
        <SlayControl id={id} blocked={blocked} />
      </div>
      <AdjustStats
        id={`beast-${id}`}
        groups={[
          {
            title: 'Might',
            fields: MIGHT.map((item) => ({
              key: item.key,
              label: item.label,
              value: card[item.key],
              min: 0,
              max: PERCENT,
            })),
          },
          {
            title: 'Life and deeds',
            fields: [
              { key: 'age', label: fieldLabel('age'), value: card.age, min: 0 },
              {
                key: 'lifespan',
                label: fieldLabel('lifespan'),
                value: card.lifespan,
                min: 1,
              },
              {
                key: 'raids',
                label: fieldLabel('raids'),
                value: card.raids,
                min: 0,
              },
            ],
          },
        ]}
        note='Might runs from 0 to 100. Terror and renown are stats: set them in the Stats section.'
        run={({ key, value }) => editBeast(id, key, value)}
      />
    </AdjustPanel>
  )
}

function Body({ id, card, blocked }: Blocked) {
  return (
    <div
      data-surface='BeastCard'
      className='@container/wild flex min-w-0 flex-col gap-4'
    >
      <BeastHero card={card} />
      <BeastVitals card={card} />
      <div className='grid min-w-0 grid-cols-1 gap-3 @xl/wild:grid-cols-2'>
        <Might card={card} />
        <Domain card={card} />
        <Hoard card={card} />
        <Wounds card={card} />
        <Abilities card={card} />
        <Treasures card={card} />
      </div>
      <BeastControls id={id} card={card} blocked={blocked} />
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
      description='A named terror of the wilds: its might and temper, the lair it guards, the hoard it heaps and the wounds it remembers.'
      icon={BEAST_ICON}
      tone='danger'
    >
      {view.isPending && <LoadingBlock label='Reading the beast' />}
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

function HerdCard({
  community,
  row,
  blocked,
}: {
  community: number
  row: HerdView
  blocked: string | null
}) {
  const [head, setHead] = useState(String(row.head))
  const [fed, setFed] = useState(String(row.fed_epochs))
  const [stage, setStage] = useState<string>(row.stage)
  const save = useGodAction<{
    values: Record<string, unknown>
    release?: string[]
  }>({
    run: ({ values, release }) =>
      unwrap(
        api.POST('/api/actions/herd:edit', {
          body: {
            community_id: community,
            species_id: row.species?.id ?? 0,
            values: values as Record<string, never>,
            release: release ?? [],
          },
        })
      ),
  })
  const busy = busyOf(blocked, save.isPending)
  const spec = named(STAGE, row.stage)
  const whole = (value: string) => Math.max(0, Math.round(Number(value) || 0))
  return (
    <li
      data-surface='HerdRow'
      className='flex min-w-0 flex-col gap-3 rounded-lg border bg-background p-3'
    >
      <div className='flex min-w-0 items-center gap-2'>
        <Medallion icon={spec.icon} tone={spec.tone ?? 'gold'} size='sm' />
        <div className='flex min-w-0 flex-1 flex-col'>
          <Name item={row.species} fallback='A lost kind' />
          <Muted as='span' variant='caption' truncate>
            {`Kept since epoch ${row.since_epoch}`}
          </Muted>
        </div>
        <Badge size='sm' variant={BADGE_OF[spec.tone ?? 'gold']}>
          {spec.label}
        </Badge>
        <HerdDrop
          communityId={community}
          speciesId={row.species?.id ?? 0}
          name={row.species?.name ?? 'this kind'}
          blocked={blocked}
        />
      </div>
      <div className='grid min-w-0 grid-cols-2 gap-2'>
        <MiniStat
          icon={PawPrint}
          label='Head'
          value={row.head}
          tone='verdigris'
        />
        <MiniStat
          icon={Wheat}
          label={row.fed_epochs === 1 ? 'Epoch fed' : 'Epochs fed'}
          value={row.fed_epochs}
          tone='gold'
        />
      </div>
      <StageTrack stage={row.stage} />
      {row.locked.length > 0 && (
        <Badge size='sm' variant='default'>
          {`Held: ${row.locked.map(fieldLabel).join(', ').toLowerCase()}`}
        </Badge>
      )}
      <Collapsible className='flex min-w-0 flex-col gap-3 border-t pt-3'>
        <CollapsibleTrigger asChild>
          <Button variant='ghost' size='sm' className='group self-start'>
            <ArrowRight className='transition-transform group-aria-expanded:rotate-90' />
            Adjust this herd
          </Button>
        </CollapsibleTrigger>
        <CollapsibleContent className='flex min-w-0 flex-col gap-3'>
          <div className='grid min-w-0 grid-cols-1 items-end gap-3 @sm/herd:grid-cols-3'>
            <NumberField
              label='Head count'
              value={head}
              min={0}
              disabled={busy !== null}
              onChange={setHead}
            />
            <MindPicker
              label='Taming stage'
              value={stage}
              table={pickTable(domesticationStageValues, STAGE)}
              blocked={busy}
              onPick={setStage}
            />
            <NumberField
              label='Epochs fed'
              value={fed}
              min={0}
              disabled={busy !== null}
              onChange={setFed}
            />
          </div>
          <div className='flex min-w-0 flex-wrap gap-2'>
            <Button
              size='sm'
              aria-label='Set the herd'
              disabled={busy !== null}
              disabledReason={busy ?? undefined}
              onClick={() =>
                save.mutate({
                  values: {
                    head: whole(head),
                    stage,
                    fed_epochs: whole(fed),
                  },
                })
              }
            >
              <Check />
              Set it so
            </Button>
            {row.locked.length > 0 && (
              <Button
                size='sm'
                variant='outline'
                disabled={busy !== null}
                disabledReason={busy ?? undefined}
                onClick={() =>
                  save.mutate({ values: {}, release: [...row.locked] })
                }
              >
                <Unlock />
                Let the world decide again
              </Button>
            )}
          </div>
        </CollapsibleContent>
      </Collapsible>
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
  const heads = view.data.reduce((sum, row) => sum + row.head, 0)
  return (
    <Section
      id='section-herds'
      title='Herds'
      description='The beasts this community keeps, feeds and breeds, and how far each is tamed.'
      icon={HERDS_ICON}
      tone='verdigris'
      actions={
        <Badge variant='secondary'>
          <PawPrint />
          {`${heads} head in ${view.data.length} ${view.data.length === 1 ? 'herd' : 'herds'}`}
        </Badge>
      }
    >
      <ul className='@container/herd grid min-w-0 grid-cols-1 gap-3 @2xl/herd:grid-cols-2'>
        <Paged items={view.data} as='li'>
          {(row) => (
            <HerdCard
              key={`${row.species?.id}-${row.head}-${row.stage}-${row.fed_epochs}`}
              community={communityId}
              row={row}
              blocked={blocked}
            />
          )}
        </Paged>
      </ul>
    </Section>
  )
}

export function FoodWebSection({ regionId }: { regionId: number }) {
  const view = useFoodWeb(regionId)
  if (!view.data || view.data.nodes.length === 0) return null
  const web = view.data
  const hunters = new Set(web.links.map((link) => link.hunter_id))
  const top = web.nodes.reduce((best, node) =>
    node.abundance > best.abundance ? node : best
  )
  const grazers = web.nodes.filter((node) =>
    ['herbivore', 'filter', 'photosynthetic'].includes(node.diet)
  ).length
  return (
    <Section
      id='section-food-web'
      title='Food web'
      description='The kinds of this land, how many of each, and who eats whom.'
      icon={WEB_ICON}
      tone='success'
    >
      <div className='@container/wild flex min-w-0 flex-col gap-4'>
        <div className='grid min-w-0 grid-cols-1 gap-3 @xs/wild:grid-cols-2 @lg/wild:grid-cols-4'>
          <KpiTile
            label='Kinds'
            value={web.nodes.length}
            icon={PawPrint}
            tone='success'
            hint='Living in this land'
          />
          <KpiTile
            label='Grazers'
            value={grazers}
            icon={DIET.herbivore.icon}
            tone='verdigris'
            hint='Feeding on plants, water and light'
          />
          <KpiTile
            label='Hunters'
            value={hunters.size}
            icon={Crosshair}
            tone='danger'
            hint={`${web.links.length} ${web.links.length === 1 ? 'hunt' : 'hunts'} between kinds`}
          />
          <KpiTile
            label='Most numerous'
            value={top.abundance}
            icon={Gem}
            tone='gold'
            hint={top.species.name}
            meter={{ value: top.abundance, max: PERCENT, label: 'Abundance' }}
          />
        </div>
        <Card
          title='Who eats whom'
          icon={Crosshair}
          tone='danger'
          aside={
            <Badge size='sm' variant='secondary'>
              {web.links.length}
            </Badge>
          }
        >
          {web.links.length === 0 ? (
            <Muted>
              No kind here hunts another: the land lives on grass, carrion and
              light.
            </Muted>
          ) : (
            <FoodWebGraph web={web} />
          )}
        </Card>
        <ul
          data-surface='FoodWebNodes'
          className='grid min-w-0 grid-cols-1 gap-2 @xl/wild:grid-cols-2'
        >
          <Paged items={web.nodes} as='li'>
            {(node) => {
              const diet = named(DIET, node.diet)
              const size = named(SIZE, node.size_class)
              return (
                <li
                  key={node.species.id}
                  className='flex min-w-0 flex-col gap-2 rounded-lg border bg-background p-2.5'
                >
                  <div className='flex min-w-0 items-center gap-2'>
                    <Medallion icon={diet.icon} tone={diet.tone} size='sm' />
                    <div className='flex min-w-0 flex-1 flex-col'>
                      <span className='min-w-0 truncate'>
                        <Name item={node.species} />
                      </span>
                      <Muted as='span' variant='caption' truncate>
                        {`${size.label} ${diet.label.toLowerCase()}`}
                      </Muted>
                    </div>
                    {hunters.has(node.species.id) && (
                      <Badge size='sm' variant='destructive'>
                        <Crosshair />
                        Hunter
                      </Badge>
                    )}
                    <Stat value={node.abundance} unit='/ 100' />
                  </div>
                  <Progress
                    size='sm'
                    value={node.abundance}
                    tone={barTone(node.abundance, 'success')}
                    aria-label={`${node.species.name} abundance`}
                  />
                </li>
              )
            }}
          </Paged>
        </ul>
      </div>
    </Section>
  )
}
