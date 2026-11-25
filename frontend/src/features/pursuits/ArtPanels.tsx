import { useState } from 'react'
import {
  BookOpen,
  Coins,
  Eye,
  Gem,
  Handshake,
  MessageSquareQuote,
  Palette,
  Stamp,
} from 'lucide-react'
import { plural } from '@/lib/units'
import { Button } from '@/components/ui/button'
import { KpiTile } from '@/components/domain'
import { table } from '@/features/arcana/labels'
import { Held, Listed } from '@/features/collective/parts'
import { Facts, ForgeCard, Meter } from '@/features/cosmography/parts'
import { YES_NO } from '@/features/cycles/labels'
import { StepButton } from '@/features/cycles/parts'
import { why } from '@/features/dominion/model'
import { NodePicker } from '@/features/dominion/parts'
import { MindPicker } from '@/features/entity/mind/parts'
import { NumberField } from '@/features/entity/realm/parts'
import { Ref } from '@/features/gatherings/parts'
import { Bars } from '@/features/sacred/parts'
import { Tag } from '@/features/wars/military/parts'
import { type PursuitsNodeView, usePursuitsAction } from './api'
import {
  CANON_ICON,
  CANON_PATHS,
  FORGERY_KINDS,
  FORGERY_STATUS,
  MARKET_ROLES,
} from './labels'
import {
  ART_TYPES,
  FAIR_TYPES,
  FORGED_TYPES,
  FORM_TYPES,
  HOLDER_TYPES,
  MANY,
  MORTAL_TYPES,
  PEOPLE_TYPES,
  SPAN,
  usePursuitsRow,
  usePursuitsStep,
} from './model'

type Price = PursuitsNodeView['prices'][number]
type Sale = PursuitsNodeView['sales'][number]
type Collector = NonNullable<PursuitsNodeView['collector']>
type Forgery = PursuitsNodeView['forgeries'][number]
type Canon = PursuitsNodeView['canon'][number]

const EXPOSED = 'This forgery is already exposed'

function signedAcclaim(acclaim: number): string {
  return acclaim > 0 ? `+${acclaim}` : `${acclaim}`
}

function PriceCard({ row, blocked }: { row: Price; blocked: string | null }) {
  const action = usePursuitsRow(
    'art_price:edit',
    'art_price:delete',
    { artwork_id: row.artwork.id },
    blocked
  )
  return (
    <Held
      icon={Coins}
      tone={row.price > 0 ? 'gold' : 'muted'}
      title={row.artwork.name}
      caption={`Valued at ${row.price} · appraised in epoch ${row.updated_epoch}`}
      removeLabel='Take it off the market'
      editTitle='Set the price of the work'
      note='A work is valued each epoch by its quality, the renown of its maker, its place in a canon, how many hands it has passed through and how many collectors want its form. A price you set holds until you release it.'
      fields={[
        { key: 'price', label: 'Price', kind: 'number', min: 0, max: MANY },
        {
          key: 'provenance',
          label: 'Sales behind it',
          kind: 'number',
          min: 0,
          max: MANY,
        },
        {
          key: 'interest',
          label: 'Interest of collectors',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'acclaim',
          label: 'Acclaim of critics',
          kind: 'number',
          min: -SPAN,
          max: SPAN,
        },
        {
          key: 'last_buyer_node_id',
          label: 'Last buyer',
          kind: 'node',
          types: HOLDER_TYPES,
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    >
      <Meter
        label={`Interest of collectors (${row.interest} of ${SPAN})`}
        value={row.interest}
        tone='info'
        icon={Eye}
      />
      <Meter
        label={`Acclaim of critics (${signedAcclaim(row.acclaim)})`}
        value={Math.abs(row.acclaim)}
        tone={row.acclaim >= 0 ? 'success' : 'warning'}
        icon={MessageSquareQuote}
      />
      <div className='@container/tiles min-w-0'>
        <div className='grid min-w-0 grid-cols-2 gap-2'>
          <KpiTile label='Price' value={row.price} icon={Coins} tone='gold' />
          <KpiTile
            label='Sales behind it'
            value={row.provenance}
            icon={Handshake}
            tone='info'
          />
        </div>
      </div>
      <Facts
        items={[
          [
            'Last buyer',
            <Ref key='buyer' node={row.last_buyer} empty='never sold' />,
          ],
          [
            'Last sold',
            row.last_sale_epoch !== null
              ? `epoch ${row.last_sale_epoch}`
              : 'never',
          ],
        ]}
      />
    </Held>
  )
}

function SaleCard({ row, blocked }: { row: Sale; blocked: string | null }) {
  const action = usePursuitsRow(
    'art_sale:edit',
    'art_sale:delete',
    { sale_id: row.id },
    blocked
  )
  return (
    <Held
      icon={Handshake}
      tone='info'
      title={`${row.artwork.name} sold for ${row.price}`}
      caption={`Epoch ${row.epoch}`}
      removeLabel='Strike the sale'
      editTitle='Set the sale'
      note='A record of a work changing hands: who sold it, who bought it, for how much and where the fair was held, if it sold at one.'
      fields={[
        {
          key: 'seller_node_id',
          label: 'Seller',
          kind: 'node',
          types: HOLDER_TYPES,
        },
        {
          key: 'buyer_node_id',
          label: 'Buyer',
          kind: 'node',
          types: HOLDER_TYPES,
        },
        {
          key: 'price',
          label: 'Price paid',
          kind: 'number',
          min: 0,
          max: MANY,
        },
        {
          key: 'fair_place_entity_id',
          label: 'Where the fair was held',
          kind: 'node',
          types: FAIR_TYPES,
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    >
      <Facts
        items={[
          ['Seller', <Ref key='seller' node={row.seller} empty='no one' />],
          ['Buyer', <Ref key='buyer' node={row.buyer} empty='no one' />],
          [
            'Where the fair was held',
            <Ref key='fair' node={row.fair_place} empty='at no fair' />,
          ],
        ]}
      />
    </Held>
  )
}

function CollectorCard({
  row,
  blocked,
}: {
  row: Collector
  blocked: string | null
}) {
  const action = usePursuitsRow(
    'collector:edit',
    'collector:delete',
    { holder_id: row.holder.id },
    blocked
  )
  const role = MARKET_ROLES[row.role]
  return (
    <Held
      icon={role.icon}
      tone={role.tone}
      title={row.holder.name}
      caption={`${role.label} since epoch ${row.since_epoch}`}
      removeLabel='Take them off the market'
      editTitle='Set the collector'
      note='Collectors bid for works of the form they favour; their eye for a work lets them see through forgeries, more easily in their own land.'
      fields={[
        {
          key: 'role',
          label: 'Role',
          kind: 'pick',
          table: table(MARKET_ROLES),
        },
        {
          key: 'taste_form_entity_id',
          label: 'Favoured form',
          kind: 'node',
          types: FORM_TYPES,
        },
        {
          key: 'connoisseurship',
          label: 'Eye for a work',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
      extra={<Tag item={role} />}
    >
      <Meter
        label={`Eye for a work (${row.connoisseurship} of ${SPAN})`}
        value={row.connoisseurship}
        tone='success'
        icon={Eye}
      />
      <Facts
        items={[
          [
            'Favoured form',
            <Ref key='taste' node={row.taste} empty='any form' />,
          ],
        ]}
      />
    </Held>
  )
}

function MarketForge({
  nodeId,
  kind,
  collector,
  blocked,
}: {
  nodeId: number
  kind: string | null
  collector: number | null
  blocked: string | null
}) {
  const isWork = kind === 'artwork'
  const isHolder = (HOLDER_TYPES as readonly string[]).includes(kind ?? '')
  const [work, setWork] = useState<number | null>(isWork ? nodeId : null)
  const [buyer, setBuyer] = useState<number | null>(isHolder ? nodeId : null)
  const [price, setPrice] = useState('')
  const [role, setRole] = useState('')
  const valuing = usePursuitsAction(
    'art_price:set',
    (_: void) => ({
      artwork_id: work ?? 0,
      price: price === '' ? null : Number(price),
    }),
    'The work is valued'
  )
  const selling = usePursuitsAction(
    'art_sale:create',
    (_: void) => ({
      artwork_id: work ?? 0,
      buyer_id: buyer ?? 0,
      price: price === '' ? null : Number(price),
    }),
    'The work changes hands'
  )
  const collecting = usePursuitsAction(
    'collector:create',
    (_: void) => ({
      holder_id: buyer ?? 0,
      role: role === '' ? null : (role as Collector['role']),
      taste_id: null,
    }),
    'A collector enters the market'
  )
  const noWork = work === null ? 'Choose a work' : null
  const noBuyer = buyer === null ? 'Choose a buyer or collector' : null
  const collects =
    noBuyer ?? (buyer === collector ? 'They already collect works' : null)
  return (
    <ForgeCard
      icon={Gem}
      tone='gold'
      title='Trade in works'
      note='Value a work, sell it to a buyer at its price or the one you name, or make a mortal, realm, church, faction or town a collector.'
      columns={4}
      action={
        <div className='flex min-w-0 flex-wrap gap-2'>
          <StepButton
            act={valuing}
            icon={Coins}
            label='Value it'
            busy={why(blocked ?? noWork, valuing.isPending)}
            onClick={() => valuing.mutate()}
          />
          <StepButton
            act={selling}
            icon={Handshake}
            label='Sell it'
            busy={why(blocked ?? noWork ?? noBuyer, selling.isPending)}
            onClick={() => selling.mutate()}
          />
          <Button
            act={collecting}
            size='sm'
            disabled={why(blocked ?? collects, collecting.isPending) !== null}
            disabledReason={
              why(blocked ?? collects, collecting.isPending) ?? undefined
            }
            onClick={() => collecting.mutate()}
          >
            <Gem />
            Make a collector
          </Button>
        </div>
      }
    >
      <NodePicker
        label='The work'
        value={work}
        onChange={setWork}
        blocked={blocked}
        types={ART_TYPES}
      />
      <NodePicker
        label='Buyer or collector'
        value={buyer}
        onChange={setBuyer}
        blocked={blocked}
        types={HOLDER_TYPES}
      />
      <NumberField
        label='Price'
        value={price}
        min={0}
        max={MANY}
        placeholder='Its market price'
        blocked={blocked}
        onChange={setPrice}
      />
      <MindPicker
        label='Collector role'
        value={role}
        table={table(MARKET_ROLES)}
        placeholder='Read from the holder'
        blocked={blocked}
        onPick={setRole}
      />
    </ForgeCard>
  )
}

export function ArtMarketPanel({
  nodeId,
  kind,
  data,
  blocked,
}: {
  nodeId: number
  kind: string | null
  data: PursuitsNodeView
  blocked: string | null
}) {
  return (
    <div data-surface='ArtMarketPanel' className='flex min-w-0 flex-col gap-4'>
      <Bars
        chart='chart-art-prices'
        title='Price of each work'
        legend={[
          { text: 'Price', variant: 'warning' },
          {
            text: 'The mark is the interest of collectors',
            variant: 'outline',
          },
        ]}
        rows={data.prices.map((row) => ({
          key: row.artwork.id,
          caption: `${row.artwork.name}: ${row.price}, ${plural(row.provenance, 'sale', 'sales')}, interest ${row.interest}`,
          segments: [{ value: row.price, fill: 'fill-warning' }],
          mark: row.interest,
        }))}
        noun={['work', 'works']}
        empty='No work here is priced on the market.'
      />
      {data.collector && (
        <CollectorCard row={data.collector} blocked={blocked} />
      )}
      <Listed
        title='Works on the market'
        items={data.prices}
        empty='No work here is priced on the market.'
        noun={['work', 'works']}
        itemKey={(item) => item.artwork.id}
      >
        {(item) => <PriceCard row={item} blocked={blocked} />}
      </Listed>
      <Listed
        title='Sales'
        items={data.sales}
        empty='No work here has changed hands.'
        noun={['sale', 'sales']}
        itemKey={(item) => item.id}
      >
        {(item) => <SaleCard row={item} blocked={blocked} />}
      </Listed>
      <MarketForge
        nodeId={nodeId}
        kind={kind}
        collector={data.collector?.holder.id ?? null}
        blocked={blocked}
      />
    </div>
  )
}

function ForgeryCard({
  row,
  blocked,
}: {
  row: Forgery
  blocked: string | null
}) {
  const action = usePursuitsRow(
    'forgery:edit',
    'forgery:delete',
    { forgery_id: row.id },
    blocked
  )
  const exposing = usePursuitsStep(
    'forgery:expose',
    { forgery_id: row.id, expert_id: null },
    blocked ?? (row.status === 'exposed' ? EXPOSED : null),
    'The forgery is exposed'
  )
  const kind = FORGERY_KINDS[row.kind]
  const status = FORGERY_STATUS[row.status]
  return (
    <Held
      icon={kind.icon}
      tone={status.tone}
      title={row.item.name}
      caption={`${kind.label} forged in epoch ${row.made_epoch}${row.exposed_epoch !== null ? ` · exposed in epoch ${row.exposed_epoch}` : ''}`}
      removeLabel='Strike the forgery'
      editTitle='Set the forgery'
      note='A forgery passes for the real thing until an expert with a keener eye than the forger’s skill sees through it. Exposed, its price falls to nothing, a forged relic loses its sanctity, a forged charter loses its claim, a counterfeit wears down the brand and the forger is shamed.'
      fields={[
        {
          key: 'kind',
          label: 'What was forged',
          kind: 'pick',
          table: table(FORGERY_KINDS),
        },
        {
          key: 'forger_entity_id',
          label: 'Forger',
          kind: 'node',
          types: MORTAL_TYPES,
        },
        {
          key: 'original_entity_id',
          label: 'Original',
          kind: 'node',
          types: FORGED_TYPES,
        },
        {
          key: 'skill',
          label: 'Skill of the forger',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'status',
          label: 'Standing',
          kind: 'pick',
          table: table(FORGERY_STATUS),
        },
        {
          key: 'exposed_by_entity_id',
          label: 'Exposed by',
          kind: 'node',
          types: HOLDER_TYPES,
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
      extra={<Tag item={status} />}
    >
      <Meter
        label={`Skill of the forger (${row.skill} of ${SPAN})`}
        value={row.skill}
        tone='warning'
        icon={Palette}
      />
      <Facts
        items={[
          ['Forger', <Ref key='forger' node={row.forger} empty='unknown' />],
          ['Original', <Ref key='original' node={row.original} empty='lost' />],
          ['Counterfeits a brand', row.brand_id !== null ? 'yes' : 'no'],
          ['Backs a fabricated claim', row.claim_id !== null ? 'yes' : 'no'],
          [
            'Exposed by',
            <Ref key='expert' node={row.exposed_by} empty='no one yet' />,
          ],
        ]}
      />
      <StepButton
        icon={Eye}
        label='Expose it'
        busy={exposing.busy}
        onClick={exposing.run}
      />
    </Held>
  )
}

function ForgeryForge({
  nodeId,
  kind,
  blocked,
}: {
  nodeId: number
  kind: string | null
  blocked: string | null
}) {
  const [original, setOriginal] = useState<number | null>(
    (FORGED_TYPES as readonly string[]).includes(kind ?? '') ? nodeId : null
  )
  const [forger, setForger] = useState<number | null>(
    kind === 'mortal' ? nodeId : null
  )
  const [forgery, setForgery] = useState<string>('artwork')
  const forging = usePursuitsAction(
    'forgery:create',
    (_: void) => ({
      original_id: original ?? 0,
      forger_id: forger ?? 0,
      kind: forgery as keyof typeof FORGERY_KINDS,
    }),
    'A forgery is made'
  )
  const busy = why(
    blocked ??
      (original === null
        ? 'Choose what is copied'
        : forger === null
          ? 'Choose the mortal who forges it'
          : null),
    forging.isPending
  )
  return (
    <ForgeCard
      icon={Stamp}
      tone='warning'
      title='Have a work forged'
      note='A mortal copies a work, a relic, a charter or a town’s brand, counterfeits a realm’s coin or seal, or forges the lineage of a title, with the skill of their own creativity; the expert of each kind may see through it.'
      columns={3}
      action={
        <Button
          act={forging}
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => forging.mutate()}
        >
          <Stamp />
          Forge it
        </Button>
      }
    >
      <NodePicker
        label='What is copied'
        value={original}
        onChange={setOriginal}
        blocked={blocked}
        types={FORGED_TYPES}
      />
      <NodePicker
        label='Forger'
        value={forger}
        onChange={setForger}
        blocked={blocked}
        types={MORTAL_TYPES}
      />
      <MindPicker
        label='Kind of forgery'
        value={forgery}
        table={table(FORGERY_KINDS)}
        blocked={blocked}
        onPick={setForgery}
      />
    </ForgeCard>
  )
}

export function ForgeryPanel({
  nodeId,
  kind,
  data,
  blocked,
}: {
  nodeId: number
  kind: string | null
  data: PursuitsNodeView
  blocked: string | null
}) {
  return (
    <div data-surface='ForgeryPanel' className='flex min-w-0 flex-col gap-4'>
      <Bars
        chart='chart-forgeries'
        title='Skill of each forgery'
        legend={[
          { text: 'Passes for real', variant: 'warning' },
          { text: 'Exposed', variant: 'destructive' },
        ]}
        rows={data.forgeries.map((row) => ({
          key: row.id,
          caption: `${row.item.name}: ${FORGERY_KINDS[row.kind].label.toLowerCase()}, skill ${row.skill}, ${FORGERY_STATUS[row.status].label.toLowerCase()}`,
          segments: [
            {
              value: row.skill,
              fill:
                row.status === 'exposed' ? 'fill-destructive' : 'fill-warning',
            },
          ],
        }))}
        max={SPAN}
        noun={['forgery', 'forgeries']}
        empty='No forgery touches this.'
      />
      <Listed
        title='Forgeries'
        items={data.forgeries}
        empty='No forgery touches this.'
        noun={['forgery', 'forgeries']}
        itemKey={(item) => item.id}
      >
        {(item) => <ForgeryCard row={item} blocked={blocked} />}
      </Listed>
      <ForgeryForge nodeId={nodeId} kind={kind} blocked={blocked} />
    </div>
  )
}

function CanonCard({ row, blocked }: { row: Canon; blocked: string | null }) {
  const action = usePursuitsRow(
    'canon_work:edit',
    'canon_work:delete',
    { people_id: row.people.id, artwork_id: row.artwork.id },
    blocked
  )
  const path = CANON_PATHS[row.path]
  return (
    <Held
      icon={path.icon}
      tone={row.contested ? 'warning' : path.tone}
      title={row.artwork.name}
      caption={`In the canon of ${row.people.name} since epoch ${row.since_epoch}`}
      removeLabel='Drop it from the canon'
      editTitle='Set the canon work'
      note='A canon holds the works a people treasures. A work enters by renown, by being copied, by an institution, by teaching or by an orthodox movement; where rival movements stand, they contest it and wear its weight down until it falls out.'
      fields={[
        {
          key: 'path',
          label: 'How it entered',
          kind: 'pick',
          table: table(CANON_PATHS),
        },
        { key: 'weight', label: 'Weight', kind: 'number', min: 0, max: SPAN },
        {
          key: 'contested',
          label: 'Contested',
          kind: 'pick',
          table: YES_NO,
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
      extra={<Tag item={path} />}
    >
      <Meter
        label={`Weight in the canon (${row.weight} of ${SPAN})`}
        value={row.weight}
        tone={row.contested ? 'warning' : 'success'}
        icon={BookOpen}
      />
      <Facts
        items={[
          ['People', <Ref key='people' node={row.people} empty='none' />],
          ['Contested', row.contested ? 'yes, by rival movements' : 'no'],
        ]}
      />
    </Held>
  )
}

function CanonForge({
  nodeId,
  kind,
  canon,
  blocked,
}: {
  nodeId: number
  kind: string | null
  canon: Canon[]
  blocked: string | null
}) {
  const [people, setPeople] = useState<number | null>(
    kind === 'people' ? nodeId : null
  )
  const [work, setWork] = useState<number | null>(
    kind === 'artwork' ? nodeId : null
  )
  const [path, setPath] = useState<string>('renown')
  const placing = usePursuitsAction(
    'canon_work:create',
    (_: void) => ({
      people_id: people ?? 0,
      artwork_id: work ?? 0,
      path: path as Canon['path'],
    }),
    'The work enters the canon'
  )
  const busy = why(
    blocked ??
      (people === null
        ? 'Choose a people'
        : work === null
          ? 'Choose a work'
          : canon.some(
                (row) => row.people.id === people && row.artwork.id === work
              )
            ? 'That work is already in the canon of that people'
            : null),
    placing.isPending
  )
  return (
    <ForgeCard
      icon={CANON_ICON}
      tone='success'
      title='Set a work into a canon'
      note='The work joins the canon of the people with the weight its path gives it.'
      columns={3}
      action={
        <Button
          act={placing}
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => placing.mutate()}
        >
          <BookOpen />
          Set it in
        </Button>
      }
    >
      <NodePicker
        label='People'
        value={people}
        onChange={setPeople}
        blocked={blocked}
        types={PEOPLE_TYPES}
      />
      <NodePicker
        label='Work'
        value={work}
        onChange={setWork}
        blocked={blocked}
        types={ART_TYPES}
      />
      <MindPicker
        label='How it enters'
        value={path}
        table={table(CANON_PATHS)}
        placeholder='Choose a path'
        blocked={blocked}
        onPick={setPath}
      />
    </ForgeCard>
  )
}

export function CanonPanel({
  nodeId,
  kind,
  data,
  blocked,
}: {
  nodeId: number
  kind: string | null
  data: PursuitsNodeView
  blocked: string | null
}) {
  return (
    <div data-surface='CanonPanel' className='flex min-w-0 flex-col gap-4'>
      <Bars
        chart='chart-canon'
        title='Weight of each work in the canon'
        legend={[
          { text: 'Held firm', variant: 'success' },
          { text: 'Contested', variant: 'warning' },
        ]}
        rows={data.canon.map((row) => ({
          key: `${row.people.id}-${row.artwork.id}`,
          caption: `${row.artwork.name} in the canon of ${row.people.name}: weight ${row.weight}`,
          segments: [
            {
              value: row.weight,
              fill: row.contested ? 'fill-warning' : 'fill-success',
            },
          ],
        }))}
        max={SPAN}
        noun={['work', 'works']}
        empty='No canon holds a work tied to this.'
      />
      <Listed
        title='Canon'
        items={data.canon}
        empty='No canon holds a work tied to this.'
        noun={['work', 'works']}
        itemKey={(item) => `${item.people.id}-${item.artwork.id}`}
      >
        {(item) => <CanonCard row={item} blocked={blocked} />}
      </Listed>
      <CanonForge
        nodeId={nodeId}
        kind={kind}
        canon={data.canon}
        blocked={blocked}
      />
    </div>
  )
}
