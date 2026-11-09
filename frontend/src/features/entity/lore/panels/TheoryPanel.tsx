import { useState } from 'react'
import {
  ArrowRightLeft,
  BookMarked,
  Crown,
  Eye,
  Gauge,
  History,
  Plus,
  Scale,
  ShieldX,
  ThumbsUp,
  TriangleAlert,
  Users,
} from 'lucide-react'
import { type ActionBody } from '@/api/actions'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import { KpiTile, Medallion, Paged, StatBar } from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { EntityPicker } from '@/features/cosmos/EntityPicker'
import {
  AdjustBlock,
  ChoicePicker,
  LoreAdjust,
  LoreCard,
  LoreFields,
  LoreHero,
  MeterList,
  MeterRow,
  RefChip,
  RowEditor,
  RowEditors,
  Who,
} from '../LoreFields'
import { ANOMALY_KINDS, THEORY_DOMAINS } from '../discoveryLabels'
import { KPI_GRID, LORE_GRID, PERCENT, busyOf } from '../model'
import { useLoreAction } from './controlParts'
import { type Card, COMMUNITIES } from './shared'

const HOLDER_TYPES = [...COMMUNITIES, 'mortal']

function truthTone(value: number): 'success' | 'warning' | 'destructive' {
  return value >= 70 ? 'success' : value >= 40 ? 'warning' : 'destructive'
}

export function TheoryPanel({
  id,
  card,
  blocked,
}: {
  id: number
  card: Card<'theory'>
  blocked: string | null
}) {
  const adhere = useLoreAction(
    'theory:adherent',
    (value: {
      holder: number
      strength: number
      orthodox: boolean
      present: boolean
    }) => ({
      theory_id: id,
      holder_id: value.holder,
      strength: value.strength,
      orthodox: value.orthodox,
      present: value.present,
    })
  )
  const anomaly = useLoreAction(
    'theory:anomaly',
    (value: { kind: string; weight: number }) => ({
      theory_id: id,
      kind: value.kind as ActionBody<'theory:anomaly'>['kind'],
      weight: value.weight,
    })
  )
  const reveal = useLoreAction(
    'theory:reveal',
    (value: { community: number }) => ({
      theory_id: id,
      community_id: value.community,
    })
  )
  const [holder, setHolder] = useState<number | null>(null)
  const [kind, setKind] = useState('')
  const [hearer, setHearer] = useState<number | null>(null)
  const busy = busyOf(
    blocked,
    adhere.isPending,
    anomaly.isPending,
    reveal.isPending
  )
  const domain = THEORY_DOMAINS[card.domain]
  const ruling = card.adherents.filter((row) => row.orthodox).length
  const strained = card.pressure > card.explanatory_power
  return (
    <div data-surface='TheoryCard' className='flex min-w-0 flex-col gap-4'>
      <LoreHero
        spec={domain}
        kicker={`An account of ${card.subject}`}
        hint='What its holders believe, and beside it what is true; only you see both.'
      >
        <RefChip icon={Users} label='Set out by' item={card.founder} />
        <RefChip
          icon={BookMarked}
          label='Written in'
          item={card.founding_book}
        />
        <RefChip icon={ArrowRightLeft} label='Rival of' item={card.rival} />
      </LoreHero>
      <div className={LORE_GRID}>
        <LoreCard title='What they believe' icon={Users} tone='info'>
          <Text as='p'>{card.claim || 'It has not been put into words.'}</Text>
        </LoreCard>
        <LoreCard title='What is true' icon={Eye} tone='gold'>
          <StatBar
            label='How true it is'
            value={card.correctness}
            max={PERCENT}
            icon={Scale}
            tone={truthTone(card.correctness)}
          />
          <Muted variant='caption'>
            {card.correctness >= 70
              ? 'Mostly true: the work it guides goes better.'
              : card.correctness >= 40
                ? 'Half true: it helps and misleads by turns.'
                : 'Mostly false: the work it guides goes worse and anomalies gather.'}
          </Muted>
          {card.revealed_by_son_id !== null && (
            <Badge variant='default'>
              <Eye aria-hidden='true' />
              Revealed by a god
            </Badge>
          )}
        </LoreCard>
      </div>
      <div className={KPI_GRID}>
        <KpiTile
          label='Holders'
          value={card.adherents.length}
          icon={Users}
          tone='info'
          hint='Peoples and minds that hold it'
        />
        <KpiTile
          label='Ruling account of'
          value={ruling}
          icon={Crown}
          tone={ruling > 0 ? 'gold' : 'muted'}
          hint='Where it is the account the scholars teach'
        />
        <KpiTile
          label='Explanatory power'
          value={card.explanatory_power}
          icon={Gauge}
          tone='verdigris'
          meter={{
            value: card.explanatory_power,
            max: PERCENT,
            label: 'Explanatory power',
          }}
          hint='Anomalies must outweigh it before a rival can overturn it'
        />
        <KpiTile
          label='Weight of anomalies'
          value={card.pressure}
          icon={TriangleAlert}
          tone={strained ? 'danger' : 'muted'}
          hint={
            strained
              ? 'It is open to a paradigm contest'
              : 'It still explains what is seen'
          }
        />
      </div>
      <div className={LORE_GRID}>
        <LoreCard title='Faiths that endorse it' icon={ThumbsUp} tone='success'>
          {card.endorsed_by.length === 0 ? (
            <Muted>No faith endorses it.</Muted>
          ) : (
            <div className='flex min-w-0 flex-wrap gap-1.5'>
              {card.endorsed_by.map((item) => (
                <RefChip key={item.id} icon={ThumbsUp} label='' item={item} />
              ))}
            </div>
          )}
        </LoreCard>
        <LoreCard title='Faiths that condemn it' icon={ShieldX} tone='danger'>
          {card.condemned_by.length === 0 ? (
            <Muted>No faith condemns it.</Muted>
          ) : (
            <div className='flex min-w-0 flex-wrap gap-1.5'>
              {card.condemned_by.map((item) => (
                <RefChip key={item.id} icon={ShieldX} label='' item={item} />
              ))}
            </div>
          )}
        </LoreCard>
        <LoreCard
          title='Holders'
          icon={Users}
          tone='info'
          wide
          aside={<Badge variant='secondary'>{card.adherents.length}</Badge>}
        >
          {card.adherents.length === 0 ? (
            <Muted>No one holds it now.</Muted>
          ) : (
            <MeterList surface='TheoryAdherents'>
              <Paged items={card.adherents}>
                {(row) => (
                  <MeterRow
                    key={row.holder.id}
                    item={row.holder}
                    label={`Held since epoch ${row.since_epoch}`}
                    value={row.strength}
                    icon={row.orthodox ? Crown : Users}
                    tone={row.orthodox ? 'gold' : 'info'}
                  >
                    {row.orthodox && (
                      <Badge size='sm' variant='default'>
                        Ruling account
                      </Badge>
                    )}
                  </MeterRow>
                )}
              </Paged>
            </MeterList>
          )}
        </LoreCard>
        <LoreCard
          title='Timeline'
          icon={History}
          tone='verdigris'
          wide
          aside={
            <Badge variant='secondary'>{`${card.anomalies.length + card.shifts.length}`}</Badge>
          }
        >
          <div
            data-surface='TheoryTimeline'
            className='flex min-w-0 flex-col gap-2'
          >
            {card.shifts.length === 0 && card.anomalies.length === 0 && (
              <Muted>Nothing has yet tested it.</Muted>
            )}
            <ul className='flex min-w-0 flex-col gap-1.5'>
              <Paged items={card.shifts} as='li'>
                {(row) => (
                  <li
                    key={`shift-${row.id}`}
                    className='flex min-w-0 flex-wrap items-center gap-2 rounded-md border border-primary/40 bg-primary/5 px-2.5 py-1.5'
                  >
                    <Medallion icon={ArrowRightLeft} tone='gold' size='sm' />
                    <Who item={row.community} />
                    <Muted as='span' variant='caption'>
                      turned from
                    </Muted>
                    <Who item={row.old} />
                    <Muted as='span' variant='caption'>
                      to
                    </Muted>
                    <Who item={row.new} />
                    <Muted
                      as='span'
                      variant='caption'
                      className='ml-auto'
                    >{`Epoch ${row.epoch}`}</Muted>
                  </li>
                )}
              </Paged>
            </ul>
            <ul className='flex min-w-0 flex-col gap-1.5'>
              <Paged items={card.anomalies} as='li'>
                {(row) => {
                  const look = ANOMALY_KINDS[row.kind]
                  return (
                    <li
                      key={`anomaly-${row.id}`}
                      className='flex min-w-0 flex-wrap items-center gap-2 rounded-md border px-2.5 py-1.5'
                    >
                      <Medallion icon={look.icon} tone={look.tone} size='sm' />
                      <Text as='span' className='min-w-0 flex-1' truncate>
                        {row.label}
                      </Text>
                      {row.witness && <Who item={row.witness} />}
                      <Badge
                        size='sm'
                        variant='outline'
                      >{`Weight ${row.weight}`}</Badge>
                      <Muted
                        as='span'
                        variant='caption'
                      >{`Epoch ${row.epoch}`}</Muted>
                    </li>
                  )
                }}
              </Paged>
            </ul>
          </div>
        </LoreCard>
      </div>
      <LoreAdjust
        entityId={id}
        noun='theory'
        locked={card.locked}
        blocked={blocked}
      >
        <AdjustBlock title='Its account and its truth' icon={Scale}>
          <LoreFields
            entityId={id}
            surface='TheoryFields'
            fields={[
              { key: 'domain', kind: 'enum', table: THEORY_DOMAINS },
              { key: 'claim', kind: 'text' },
              { key: 'correctness', kind: 'number', min: 0, max: PERCENT },
              {
                key: 'explanatory_power',
                kind: 'number',
                min: 0,
                max: PERCENT,
              },
            ]}
            current={card}
            locked={card.locked}
            blocked={blocked}
          />
        </AdjustBlock>
        <AdjustBlock title='Holders' icon={Users}>
          {card.adherents.length > 0 && (
            <RowEditors>
              <Paged items={card.adherents}>
                {(row) => (
                  <RowEditor
                    key={row.holder.id}
                    label={row.holder.name}
                    icon={Users}
                    value={row.strength}
                    max={PERCENT}
                    blocked={busy}
                    onSave={(strength) =>
                      adhere.mutate({
                        holder: row.holder.id,
                        strength,
                        orthodox: row.orthodox,
                        present: true,
                      })
                    }
                  >
                    <label className='flex h-control-md shrink-0 items-center gap-1.5'>
                      <Switch
                        checked={row.orthodox}
                        disabled={busy !== null}
                        aria-label='Ruling account'
                        onCheckedChange={(next) =>
                          adhere.mutate({
                            holder: row.holder.id,
                            strength: row.strength,
                            orthodox: next,
                            present: true,
                          })
                        }
                      />
                      <Crown
                        aria-hidden='true'
                        className='size-icon-sm text-primary'
                      />
                    </label>
                  </RowEditor>
                )}
              </Paged>
            </RowEditors>
          )}
          <div className='flex min-w-0 flex-wrap items-end gap-2'>
            <EntityPicker
              types={HOLDER_TYPES}
              value={holder}
              onChange={setHolder}
              placeholder='Win over…'
            />
            <Button
              size='sm'
              variant='outline'
              disabled={busy !== null || holder === null}
              disabledReason={
                busy ??
                (holder === null ? 'Choose who will hold it' : undefined)
              }
              onClick={() =>
                holder !== null &&
                adhere.mutate({
                  holder,
                  strength: 40,
                  orthodox: false,
                  present: true,
                })
              }
            >
              <Plus />
              Win them over
            </Button>
          </div>
        </AdjustBlock>
        <div className={LORE_GRID}>
          <AdjustBlock title='Lay an anomaly against it' icon={TriangleAlert}>
            <ChoicePicker
              label='Anomaly'
              value={kind}
              table={ANOMALY_KINDS}
              blocked={busy}
              placeholder='Choose'
              onPick={setKind}
            />
            <Button
              size='sm'
              variant='outline'
              className='self-start'
              disabled={busy !== null || kind === ''}
              disabledReason={
                busy ?? (kind === '' ? 'Choose an anomaly' : undefined)
              }
              onClick={() => anomaly.mutate({ kind, weight: 1 })}
            >
              <TriangleAlert />
              Lay it
            </Button>
          </AdjustBlock>
          <AdjustBlock title='Make its truth known' icon={Eye}>
            <Label>Whose scholars hear it</Label>
            <EntityPicker
              types={[...COMMUNITIES]}
              value={hearer}
              onChange={setHearer}
              placeholder='Choose a people'
            />
            <Button
              size='sm'
              className='self-start'
              disabled={busy !== null || hearer === null}
              disabledReason={
                busy ?? (hearer === null ? 'Choose who hears it' : undefined)
              }
              onClick={() =>
                hearer !== null && reveal.mutate({ community: hearer })
              }
            >
              <Eye />
              Reveal it
            </Button>
          </AdjustBlock>
        </div>
      </LoreAdjust>
    </div>
  )
}
