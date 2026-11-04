import {
  Book,
  Feather,
  Mic,
  Sparkles,
  Sprout,
  Target,
  Users,
} from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { KpiTile } from '@/components/domain'
import { Muted } from '@/components/typography'
import {
  AdjustBlock,
  DictField,
  LoreAdjust,
  LoreCard,
  LoreFields,
  LoreHero,
  NamedChip,
  RefChip,
  ShiftChips,
} from '../LoreFields'
import {
  ARCHETYPES,
  KPI_GRID,
  LORE_GRID,
  PERCENT,
  VALUES,
  lookup,
} from '../model'
import { type Card, percentHint } from './shared'

export function LegendPanel({
  id,
  card,
  blocked,
}: {
  id: number
  card: Card<'legend'>
  blocked: string | null
}) {
  const archetype = lookup(ARCHETYPES, card.archetype)
  return (
    <div data-surface='LegendCard' className='flex min-w-0 flex-col gap-4'>
      <LoreHero spec={archetype} kicker='A tale told'>
        <RefChip icon={Target} label='Tells of' item={card.subject} />
        {card.fixed_in ? (
          <RefChip icon={Book} label='Written in' item={card.fixed_in} />
        ) : (
          <NamedChip
            spec={{
              label: 'Only spoken, so it drifts',
              icon: Mic,
              tone: 'warning',
            }}
          />
        )}
      </LoreHero>
      <div className={KPI_GRID}>
        <KpiTile
          label='Believed'
          value={`${card.credence}%`}
          icon={Sparkles}
          hint={percentHint(
            card.credence,
            'Widely held true; strong belief lets it take shape in the world',
            'Doubted; each telling adds belief, each quiet epoch takes some'
          )}
          meter={{ value: card.credence, max: PERCENT, label: 'Belief' }}
        />
        <KpiTile
          label='Distorted'
          value={`${card.distortion}%`}
          icon={Feather}
          tone='warning'
          hint='Grows with each telling among the unlettered; writing holds it'
          meter={{ value: card.distortion, max: PERCENT, label: 'Distortion' }}
        />
        <KpiTile
          label='Tellers'
          value={card.tellers.length}
          icon={Users}
          tone='info'
          hint='Peoples who tell it; its moral presses on them'
        />
        <KpiTile
          label='Kept as'
          value={card.fixed_in ? 'Written' : 'Spoken'}
          icon={card.fixed_in ? Book : Mic}
          tone={card.fixed_in ? 'success' : 'muted'}
          hint={
            card.fixed_in
              ? `Set down in ${card.fixed_in.name}`
              : 'No book holds it yet'
          }
        />
      </div>
      <div className={LORE_GRID}>
        <LoreCard title='The moral it teaches' icon={Sprout} tone='success'>
          <ShiftChips
            entries={card.moral}
            table={VALUES}
            empty='It teaches nothing in particular.'
          />
          <Muted variant='caption'>
            The more it is believed, the harder these values press on its
            tellers.
          </Muted>
        </LoreCard>
        <LoreCard
          title='Told by'
          icon={Users}
          tone='info'
          aside={<Badge variant='secondary'>{card.tellers.length}</Badge>}
        >
          {card.tellers.length === 0 ? (
            <Muted>No one tells it any more.</Muted>
          ) : (
            <ul className='flex min-w-0 flex-wrap gap-1.5'>
              {card.tellers.map((teller) => (
                <li key={teller.id}>
                  <RefChip icon={Users} label='' item={teller} />
                </li>
              ))}
            </ul>
          )}
        </LoreCard>
      </div>
      <LoreAdjust
        entityId={id}
        noun='legend'
        locked={card.locked}
        blocked={blocked}
      >
        <AdjustBlock title='The tale' icon={Feather}>
          <LoreFields
            entityId={id}
            surface='LegendForm'
            fields={[
              { key: 'archetype', kind: 'enum', table: ARCHETYPES },
              { key: 'credence', kind: 'number', min: 0, max: PERCENT },
              { key: 'distortion', kind: 'number', min: 0, max: PERCENT },
            ]}
            current={card}
            blocked={blocked}
          />
        </AdjustBlock>
        <AdjustBlock title='The moral it teaches' icon={Sprout}>
          <DictField
            entityId={id}
            spec={{ key: 'moral', label: 'The moral', value: card.moral }}
            blocked={blocked}
            table={VALUES}
          />
        </AdjustBlock>
      </LoreAdjust>
    </div>
  )
}
