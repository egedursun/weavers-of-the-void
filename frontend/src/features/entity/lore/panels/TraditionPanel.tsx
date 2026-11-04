import {
  CalendarDays,
  Coins,
  HeartPulse,
  History,
  Sparkles,
  TriangleAlert,
  Users,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { Badge } from '@/components/ui/badge'
import { KpiTile } from '@/components/domain'
import { Muted } from '@/components/typography'
import { useGodAction } from '@/features/pantheon/godAction'
import {
  AdjustBlock,
  DictField,
  LoreAdjust,
  LoreCard,
  LoreFields,
  LoreHero,
  MeterList,
  MeterRow,
  NamedChip,
  RefChip,
  RowEditor,
  RowEditors,
  TermChips,
} from '../LoreFields'
import {
  KPI_GRID,
  LORE_GRID,
  PERCENT,
  TRADITION_KINDS,
  TRADITION_TERMS,
  busyOf,
  lookup,
} from '../model'
import { type Card, COST_ONLY, average } from './shared'

export function TraditionPanel({
  id,
  card,
  blocked,
}: {
  id: number
  card: Card<'tradition'>
  blocked: string | null
}) {
  const keep = useGodAction<{ community: number; value: number }>({
    run: ({ community, value }) =>
      unwrap(
        api.POST('/api/actions/tradition:participation', {
          body: {
            tradition_id: id,
            community_id: community,
            participation: value,
          },
        })
      ),
  })
  const busy = busyOf(blocked, keep.isPending)
  const kind = lookup(TRADITION_KINDS, card.kind)
  const skipped = card.keepers.reduce((sum, row) => sum + row.skipped, 0)
  const kept = card.keepers
    .map((row) => row.last_celebrated_epoch)
    .filter((epoch): epoch is number => epoch !== null)
  return (
    <div data-surface='TraditionCard' className='flex min-w-0 flex-col gap-4'>
      <LoreHero spec={kind} kicker='A custom kept'>
        {card.calendar_slot && (
          <NamedChip spec={{ label: '', icon: CalendarDays, tone: 'info' }}>
            {`Kept at ${card.calendar_slot}`}
          </NamedChip>
        )}
        {card.taboo_target && (
          <NamedChip spec={TRADITION_KINDS.taboo}>
            {`Forbids ${card.taboo_target.replaceAll('_', ' ')}`}
          </NamedChip>
        )}
        <RefChip icon={History} label='Remembers' item={card.origin} />
      </LoreHero>
      <div className={KPI_GRID}>
        <KpiTile
          label='Kept by'
          value={card.keepers.length}
          icon={Users}
          tone='info'
          hint='Communities that keep it'
        />
        <KpiTile
          label='Devotion'
          value={`${average(card.keepers.map((row) => row.participation))}%`}
          icon={HeartPulse}
          tone='success'
          hint='How many of its keepers take part, on average'
          meter={{
            value: average(card.keepers.map((row) => row.participation)),
            max: PERCENT,
            label: 'Devotion',
          }}
        />
        <KpiTile
          label='Skipped'
          value={skipped}
          icon={TriangleAlert}
          tone={skipped > 0 ? 'warning' : 'muted'}
          hint='Times it was skipped in hunger; each costs cohesion'
        />
        <KpiTile
          label='Last kept'
          value={kept.length > 0 ? `Epoch ${Math.max(...kept)}` : 'Never'}
          icon={CalendarDays}
          tone='verdigris'
        />
      </div>
      <div className={LORE_GRID}>
        <LoreCard title='What it costs' icon={Coins} tone='warning'>
          <TermChips
            entries={card.cost}
            table={TRADITION_TERMS}
            empty='It costs nothing to keep.'
          />
        </LoreCard>
        <LoreCard title='What it brings' icon={Sparkles} tone='success'>
          <TermChips
            entries={card.effects}
            table={TRADITION_TERMS}
            empty='It brings nothing but habit.'
            unit={(key, value) =>
              `${lookup(TRADITION_TERMS, key).label} +${value}`
            }
          />
        </LoreCard>
        <LoreCard
          title='Kept by'
          icon={Users}
          tone='info'
          wide
          aside={<Badge variant='secondary'>{card.keepers.length}</Badge>}
        >
          {card.keepers.length === 0 ? (
            <Muted>No one keeps it any more.</Muted>
          ) : (
            <MeterList surface='TraditionKeepers'>
              {card.keepers.map((row) => (
                <MeterRow
                  key={row.community?.id}
                  item={row.community}
                  label={
                    row.last_celebrated_epoch !== null
                      ? `Takes part · last kept in epoch ${row.last_celebrated_epoch}`
                      : 'Takes part'
                  }
                  value={row.participation}
                  icon={kind.icon}
                  tone={kind.tone}
                >
                  {row.skipped > 0 && (
                    <Badge size='sm' variant='warning'>
                      {`Skipped ${row.skipped}×`}
                    </Badge>
                  )}
                </MeterRow>
              ))}
            </MeterList>
          )}
        </LoreCard>
      </div>
      <LoreAdjust
        entityId={id}
        noun='tradition'
        locked={card.locked}
        blocked={blocked}
      >
        <AdjustBlock title='The custom' icon={kind.icon}>
          <LoreFields
            entityId={id}
            surface='TraditionForm'
            fields={[
              { key: 'kind', kind: 'enum', table: TRADITION_KINDS },
              { key: 'calendar_slot', kind: 'text', nullable: true },
              { key: 'taboo_target', kind: 'text', nullable: true },
            ]}
            current={card}
            blocked={blocked}
          />
        </AdjustBlock>
        <div className={LORE_GRID}>
          <AdjustBlock title='What it costs' icon={Coins}>
            <DictField
              entityId={id}
              spec={{ key: 'cost', label: 'The cost', value: card.cost }}
              blocked={blocked}
              table={COST_ONLY}
            />
          </AdjustBlock>
          <AdjustBlock title='What it brings' icon={Sparkles}>
            <DictField
              entityId={id}
              spec={{
                key: 'effects',
                label: 'Its effects',
                value: card.effects,
              }}
              blocked={blocked}
              table={TRADITION_TERMS}
            />
          </AdjustBlock>
        </div>
        {card.keepers.length > 0 && (
          <AdjustBlock title='How many take part' icon={Users}>
            <RowEditors>
              {card.keepers.map((row) => (
                <RowEditor
                  key={row.community?.id}
                  label={row.community?.name ?? 'Unknown'}
                  icon={Users}
                  value={row.participation}
                  max={PERCENT}
                  blocked={busy}
                  onSave={(value) =>
                    keep.mutate({ community: row.community?.id ?? 0, value })
                  }
                />
              ))}
            </RowEditors>
          </AdjustBlock>
        )}
      </LoreAdjust>
    </div>
  )
}
