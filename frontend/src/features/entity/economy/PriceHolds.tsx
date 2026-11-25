import { useState } from 'react'
import { Lock, Package, Percent, Scale } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { type ActProp } from '@/api/mutation'
import { formatInteger } from '@/lib/format'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  EmptyState,
  IconStat,
  Medallion,
  Paged,
  LoadingBlock,
} from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { useGodAction } from '@/features/pantheon/godAction'
import {
  AdjustPanel,
  FIELD_GRID,
  NumberField,
  PartHeader,
} from './EntityEconomy'
import { ECONOMY_REFRESH, useMarketHolds } from './api'
import {
  COMMODITY,
  type CommodityKind,
  GOODS_FAMILY,
  type Named,
  premiumTone,
} from './labels'
import { useBusy, whole } from './model'
import { ChoiceSelect, ReleaseButton } from './parts'

type Premium = {
  commodity: CommodityKind
  premium_pct: number
  held_price: number | null
  held_supply: number | null
}

const COMMODITY_CHOICES: Record<string, Named> = Object.fromEntries(
  Object.entries(COMMODITY).map(([key, item]) => [
    key,
    {
      label: item.label,
      icon: item.icon,
      tone: GOODS_FAMILY[item.family].tone,
    },
  ])
)

function PremiumRow({
  row,
  busy,
  onRelease,
  act,
}: {
  row: Premium
  busy: string | null
  onRelease: () => void
  act?: ActProp
}) {
  const spec = COMMODITY[row.commodity]
  const tone = premiumTone(row.premium_pct)
  const held = row.held_price !== null || row.held_supply !== null
  return (
    <li
      data-commodity={row.commodity}
      className='flex min-w-0 flex-wrap items-center gap-2.5 rounded-md border surface-framed border-gild/70 bg-card p-2.5'
    >
      <Medallion icon={spec.icon} tone={tone} size='sm' />
      <div className='flex min-w-0 flex-1 basis-40 flex-col'>
        <Text weight='medium' truncate>
          {spec.label}
        </Text>
        <Muted variant='caption' truncate>
          {`${spec.label}: ${row.premium_pct}% of base price`}
        </Muted>
      </div>
      <IconStat
        icon={Percent}
        label='Material premium on its price'
        value={`${row.premium_pct}%`}
        tone={tone}
      />
      {row.held_price !== null && (
        <Badge size='sm' variant='default'>
          <Lock />
          {`Price held at ${formatInteger(row.held_price)}`}
        </Badge>
      )}
      {row.held_supply !== null && (
        <Badge size='sm' variant='default'>
          <Lock />
          {`Supply held at ${formatInteger(row.held_supply)}`}
        </Badge>
      )}
      <ReleaseButton act={act} held={held} busy={busy} onRelease={onRelease} />
    </li>
  )
}

export function PriceHolds({
  marketId,
  readOnlyReason,
}: {
  marketId: number
  readOnlyReason?: string | null
}) {
  const view = useMarketHolds(marketId)
  const [commodity, setCommodity] = useState<string>('grain')
  const [price, setPrice] = useState('')
  const [supply, setSupply] = useState('')
  const hold = useGodAction({
    writes: [{ lever: 'market:hold_price' }],
    invalidate: ECONOMY_REFRESH,
    run: () =>
      unwrap(
        api.POST('/api/actions/market:hold_price', {
          body: {
            market_id: marketId,
            commodity: commodity as CommodityKind,
            price: price.trim() === '' ? null : whole(price),
            supply: supply.trim() === '' ? null : whole(supply),
          },
        })
      ),
  })
  const release = useGodAction({
    writes: [{ lever: 'market:release_price' }],
    invalidate: ECONOMY_REFRESH,
    run: (kind: CommodityKind) =>
      unwrap(
        api.POST('/api/actions/market:release_price', {
          body: { market_id: marketId, commodity: kind },
        })
      ),
  })
  const busy = useBusy(readOnlyReason, hold.isPending, release.isPending)
  const rows = [...(view.data?.premiums ?? [])].sort(
    (a, b) => b.premium_pct - a.premium_pct
  )
  const heldCount = rows.filter(
    (row) => row.held_price !== null || row.held_supply !== null
  ).length
  return (
    <div
      data-surface='PriceHolds'
      className='@container/holds flex min-w-0 flex-col gap-3'
    >
      <PartHeader
        icon={Scale}
        title='Material premiums and held prices'
        note='Goods made of rare or precious materials sell above their base price. A held price or supply stays where you set it.'
        aside={
          heldCount > 0 ? (
            <Badge variant='default'>
              <Lock />
              {`${heldCount} held`}
            </Badge>
          ) : undefined
        }
      />
      {view.isPending && <LoadingBlock label='Loading the premiums' />}
      {view.data && rows.length === 0 && (
        <EmptyState
          icon={Package}
          title='No premiums here'
          description='Every good sells at its base price; nothing is held.'
        />
      )}
      {rows.length > 0 && (
        <ul className='grid min-w-0 grid-cols-1 gap-2 @3xl/holds:grid-cols-2'>
          <Paged items={rows} as='li'>
            {(row) => (
              <PremiumRow
                act={release}
                key={row.commodity}
                row={row}
                busy={busy}
                onRelease={() => release.mutate(row.commodity)}
              />
            )}
          </Paged>
        </ul>
      )}
      <AdjustPanel
        acts={[hold]}
        label='Hold a price'
        title='Hold a price or a supply'
        note='Leave a field empty to let it move freely; leave both empty to release the good.'
      >
        <div className={cn(FIELD_GRID, '@md/holds:grid-cols-4')}>
          <ChoiceSelect
            label='Good'
            value={commodity}
            table={COMMODITY_CHOICES}
            blocked={busy}
            onPick={setCommodity}
          />
          <NumberField
            label='Price (100 is usual)'
            aria='Held price'
            value={price}
            onChange={setPrice}
          />
          <NumberField
            label='Supply'
            aria='Held supply'
            value={supply}
            onChange={setSupply}
          />
          <Button
            act={hold}
            size='sm'
            className='justify-self-start'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => hold.mutate(undefined)}
          >
            <Lock />
            Hold it
          </Button>
        </div>
      </AdjustPanel>
    </div>
  )
}
