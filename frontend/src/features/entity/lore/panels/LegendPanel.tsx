import { useState } from 'react'
import {
  Book,
  BookX,
  Feather,
  History,
  Mic,
  Shapes,
  Sparkles,
  Sprout,
  Target,
  Users,
} from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { KpiTile, Paged } from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { EntityPicker } from '@/features/cosmos/EntityPicker'
import { CustomKindChoice } from '../CultureParts'
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
import { KindForge } from '../forge/KindForge'
import {
  ARCHETYPES,
  KPI_GRID,
  LORE_GRID,
  PERCENT,
  VALUES,
  busyOf,
  lookup,
  useLoreEdit,
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
  const [work, setWork] = useState<number | null>(null)
  const edit = useLoreEdit(id)
  const busy = busyOf(blocked, edit.isPending)
  return (
    <div data-surface='LegendCard' className='flex min-w-0 flex-col gap-4'>
      <LoreHero spec={archetype} kicker='A tale told'>
        <RefChip icon={Target} label='Tells of' item={card.subject} />
        {card.source && (
          <span data-surface='LegendSource'>
            <NamedChip spec={{ label: '', icon: History, tone: 'info' }}>
              {`Born of a true incident in epoch ${card.source.epoch}`}
            </NamedChip>
          </span>
        )}
        {card.custom_archetype_id && (
          <NamedChip spec={{ label: '', icon: Shapes, tone: 'gold' }}>
            A kind of tale of your own
          </NamedChip>
        )}
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
          hint={
            card.source
              ? 'How far the telling has strayed from the true incident: the older it is, the further, unless letters or a work hold it'
              : 'Grows with each telling among the unlettered; writing holds it'
          }
          meter={{ value: card.distortion, max: PERCENT, label: 'Distortion' }}
        />
        <KpiTile
          label='Tellers'
          value={card.tellers.length + card.bards.length}
          icon={Users}
          tone='info'
          hint={`${card.tellers.length} peoples and ${card.bards.length} bards tell it; its moral presses on the peoples`}
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
          aside={
            <Badge variant='secondary'>
              {card.tellers.length + card.bards.length}
            </Badge>
          }
        >
          {card.tellers.length + card.bards.length === 0 ? (
            <Muted>No one tells it any more.</Muted>
          ) : (
            <ul className='flex min-w-0 flex-wrap gap-1.5'>
              <Paged items={card.tellers} as='li'>
                {(teller) => (
                  <li key={teller.id}>
                    <RefChip icon={Users} label='' item={teller} />
                  </li>
                )}
              </Paged>
              <Paged items={card.bards}>
                {(bard) => (
                  <li key={bard.id}>
                    <RefChip icon={Mic} label='Bard' item={bard} />
                  </li>
                )}
              </Paged>
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
        <AdjustBlock title='Its own kind' icon={Shapes}>
          <CustomKindChoice
            entityId={id}
            field='custom_archetype_id'
            catalog='archetype'
            value={card.custom_archetype_id}
            blocked={blocked}
          />
          <KindForge catalog='archetype' />
        </AdjustBlock>
        <AdjustBlock title='Fix it in a work' icon={Book}>
          <Text as='p'>
            A tale set down in a work no longer drifts. The world fixes a legend
            in any work that portrays it; you may choose the work.
          </Text>
          <div className='flex min-w-0 flex-wrap items-end gap-2'>
            <EntityPicker
              types={['artwork']}
              value={work}
              onChange={setWork}
              placeholder='Choose a work…'
            />
            <Button
              size='sm'
              disabled={busy !== null || work === null}
              disabledReason={
                busy ?? (work === null ? 'Choose a work' : undefined)
              }
              onClick={() =>
                edit.mutate({ values: { fixed_in_entity_id: work } })
              }
            >
              <Book />
              Fix it there
            </Button>
            {card.fixed_in && (
              <Button
                size='sm'
                variant='outline'
                disabled={busy !== null}
                disabledReason={busy ?? undefined}
                onClick={() =>
                  edit.mutate({ values: { fixed_in_entity_id: null } })
                }
              >
                <BookX />
                Let it drift again
              </Button>
            )}
          </div>
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
