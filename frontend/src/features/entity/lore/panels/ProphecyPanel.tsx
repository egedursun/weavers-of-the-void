import {
  CalendarDays,
  Check,
  Eye,
  Feather,
  Gauge,
  Hourglass,
  Repeat,
  ScrollText,
  Sparkles,
  Swords,
  Users,
  X,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { KpiTile, Paged } from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { useGodAction } from '@/features/pantheon/godAction'
import {
  AdjustBlock,
  DictField,
  LoreAdjust,
  LoreCard,
  LoreFields,
  LoreHero,
  NamedChip,
  RefChip,
  RoleRow,
  Who,
} from '../LoreFields'
import {
  KPI_GRID,
  LORE_GRID,
  PERCENT,
  PREDICATES,
  PROPHECY_ARGS,
  PROPHECY_STATES,
  busyOf,
  lookup,
  sentence,
} from '../model'
import { ProphecyControls } from './MindControls'
import { type Card, ENTITY_ARGS } from './shared'

export function ProphecyPanel({
  id,
  card,
  blocked,
}: {
  id: number
  card: Card<'prophecy'>
  blocked: string | null
}) {
  const settle = useGodAction<boolean>({
    writes: [{ lever: 'prophecy:resolve' }],
    run: (fulfilled) =>
      unwrap(
        api.POST('/api/actions/prophecy:resolve', {
          body: { prophecy_id: id, fulfilled },
        })
      ),
  })
  const busy = busyOf(blocked, settle.isPending)
  const pending = card.state === 'pending'
  const predicate = lookup(PREDICATES, card.predicate)
  const state = lookup(PROPHECY_STATES, card.state)
  const terms = Object.entries(card.args)
  return (
    <div data-surface='ProphecyCard' className='flex min-w-0 flex-col gap-4'>
      <LoreHero
        spec={predicate}
        kicker='It is foretold'
        hint='Pressure bends the world toward it; it is weighed when its deadline comes.'
      >
        <NamedChip spec={state} />
        <RefChip icon={Eye} label='Seen by' item={card.seer} />
        {card.rival && (
          <RefChip icon={Swords} label='Its rival' item={card.rival} />
        )}
        {card.forged && (
          <NamedChip
            spec={{ label: 'Forged', icon: Feather, tone: 'danger' }}
          />
        )}
        {card.resolved_epoch !== null && (
          <NamedChip spec={{ label: '', icon: CalendarDays, tone: 'muted' }}>
            {`Settled in epoch ${card.resolved_epoch}`}
          </NamedChip>
        )}
      </LoreHero>
      <div className={KPI_GRID}>
        <KpiTile
          label='Pressure'
          value={`${card.pressure}%`}
          icon={Gauge}
          tone='warning'
          hint='How hard it bends events toward itself'
          meter={{ value: card.pressure, max: PERCENT, label: 'Pressure' }}
        />
        <KpiTile
          label='State'
          value={state.label}
          icon={state.icon}
          tone={state.tone}
          hint={
            card.resolved_epoch !== null
              ? `Settled in epoch ${card.resolved_epoch}`
              : 'Not yet settled'
          }
        />
        <KpiTile
          label='Deadline'
          value={
            card.deadline_epoch !== null
              ? `Epoch ${card.deadline_epoch}`
              : 'None'
          }
          icon={Hourglass}
          tone='muted'
          hint={
            card.deadline_epoch !== null
              ? 'It must come true by then'
              : 'It waits without end'
          }
        />
        <KpiTile
          label='Heard by'
          value={card.audience.length}
          icon={Users}
          tone='info'
          hint='Those who know of it'
        />
        <KpiTile
          label='Retold'
          value={card.retold}
          icon={Repeat}
          tone='muted'
          hint='Times it was changed in the telling'
        />
      </div>
      <div className={LORE_GRID}>
        <LoreCard
          title='What must happen'
          icon={predicate.icon}
          tone={predicate.tone}
        >
          <Text weight='medium'>{predicate.label}</Text>
          {terms.length === 0 ? (
            <Muted>No further terms bind it.</Muted>
          ) : (
            <div className='flex min-w-0 flex-col gap-2'>
              {terms.map(([key, value]) => {
                const spec = lookup(PROPHECY_ARGS, key)
                return (
                  <RoleRow
                    key={key}
                    icon={spec.icon}
                    tone={spec.tone}
                    label={spec.label}
                  >
                    {ENTITY_ARGS.has(key) && typeof value === 'number' ? (
                      <Who item={{ id: value, name: `Record ${value}` }} />
                    ) : (
                      <Text as='span'>{sentence(String(value))}</Text>
                    )}
                  </RoleRow>
                )
              })}
            </div>
          )}
        </LoreCard>
        <LoreCard
          title='Who heard it'
          icon={Users}
          tone='info'
          aside={<Badge variant='secondary'>{card.audience.length}</Badge>}
        >
          {card.audience.length === 0 ? (
            <Muted>No one has heard it spoken.</Muted>
          ) : (
            <ul className='flex min-w-0 flex-wrap gap-1.5'>
              <Paged items={card.audience} as='li'>
                {(item) => (
                  <li key={item.id}>
                    <RefChip icon={Users} label='' item={item} />
                  </li>
                )}
              </Paged>
            </ul>
          )}
        </LoreCard>
        {pending && (
          <LoreCard title='Decide its fate' icon={Sparkles} wide>
            <Muted>Settle it now instead of waiting for its deadline.</Muted>
            <div className='flex min-w-0 flex-wrap gap-2'>
              <Button
                act={settle}
                disabled={busy !== null}
                disabledReason={busy ?? undefined}
                onClick={() => settle.mutate(true)}
              >
                <Check />
                Let it come true
              </Button>
              <Button
                act={settle}
                variant='outline'
                disabled={busy !== null}
                disabledReason={busy ?? undefined}
                onClick={() => settle.mutate(false)}
              >
                <X />
                Let it fail
              </Button>
            </div>
          </LoreCard>
        )}
      </div>
      <LoreAdjust
        entityId={id}
        noun='prophecy'
        locked={card.locked}
        blocked={blocked}
      >
        <AdjustBlock title='The foretelling' icon={predicate.icon}>
          <LoreFields
            entityId={id}
            surface='ProphecyForm'
            fields={[
              { key: 'predicate', kind: 'enum', table: PREDICATES },
              { key: 'deadline_epoch', kind: 'number', min: 0, nullable: true },
              { key: 'pressure', kind: 'number', min: 0, max: PERCENT },
              { key: 'retold', kind: 'number', min: 0 },
              { key: 'forged', kind: 'bool' },
              {
                key: 'rival_entity_id',
                kind: 'number',
                min: 1,
                nullable: true,
              },
            ]}
            current={card}
            blocked={blocked}
          />
        </AdjustBlock>
        <AdjustBlock title='What exactly must happen' icon={ScrollText}>
          <DictField
            entityId={id}
            spec={{ key: 'args', label: 'Its terms', value: card.args }}
            blocked={blocked}
            table={PROPHECY_ARGS}
          />
        </AdjustBlock>
        <ProphecyControls id={id} card={card} blocked={blocked} />
      </LoreAdjust>
    </div>
  )
}
