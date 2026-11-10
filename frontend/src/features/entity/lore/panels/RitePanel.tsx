import { useState } from 'react'
import {
  Check,
  Coins,
  History,
  PenLine,
  Plus,
  Sparkles,
  Target,
  Trash2,
  TriangleAlert,
  User,
  Wand2,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  KpiTile,
  Paged,
  PagedList,
  StatBar,
  Timeline,
  TimelineItem,
} from '@/components/domain'
import { Label, Muted } from '@/components/typography'
import { EntityPicker } from '@/features/cosmos/EntityPicker'
import { useGodAction } from '@/features/pantheon/godAction'
import {
  AdjustBlock,
  ChoicePicker,
  DictField,
  LoreAdjust,
  LoreCard,
  LoreFields,
  LoreHero,
  NamedChip,
  RefChip,
  RowEditor,
  RowEditors,
  TermChips,
} from '../LoreFields'
import {
  BACKLASHES,
  EFFECTS,
  KPI_GRID,
  LORE_GRID,
  MAX_POWER,
  PERCENT,
  RITE_COSTS,
  SCHOOLS,
  SOURCES,
  busyOf,
  lookup,
  sentence,
} from '../model'
import { RiteControls } from './RiteControls'
import { type Card, COMMUNITIES } from './shared'

export function RitePanel({
  id,
  card,
  blocked,
}: {
  id: number
  card: Card<'rite'>
  blocked: string | null
}) {
  const [effect, setEffect] = useState('')
  const [caster, setCaster] = useState<number | null>(card.inventor?.id ?? null)
  const [target, setTarget] = useState<number | null>(null)
  const shape = useGodAction<{ effect: string; magnitude: number }>({
    run: ({ effect: chosen, magnitude }) =>
      unwrap(
        api.POST('/api/actions/rite:effect', {
          body: { rite_id: id, effect: chosen as 'heal', magnitude },
        })
      ),
  })
  const cast = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/rite:cast', {
          body: { rite_id: id, caster_id: caster ?? 0, target_id: target },
        })
      ),
  })
  const busy = busyOf(blocked, shape.isPending, cast.isPending)
  const school = lookup(SCHOOLS, card.school)
  const source = lookup(SOURCES, card.source)
  const backlash = lookup(BACKLASHES, card.backlash)
  const worked = card.castings.filter((row) => row.succeeded).length
  const needs = Object.entries(card.requirements)
  return (
    <div data-surface='RiteCard' className='flex min-w-0 flex-col gap-4'>
      <LoreHero
        spec={school}
        kicker='A working of magic'
        title={`Rite of ${school.label.toLowerCase()}`}
      >
        <NamedChip
          spec={source}
        >{`Drawn from ${source.label.toLowerCase()}`}</NamedChip>
        {card.holy && (
          <NamedChip spec={{ label: 'Holy', icon: Sparkles, tone: 'gold' }} />
        )}
        {card.heretical && (
          <NamedChip
            spec={{ label: 'Heresy', icon: TriangleAlert, tone: 'danger' }}
          />
        )}
        <RefChip icon={PenLine} label='Devised by' item={card.inventor} />
      </LoreHero>
      <div className={KPI_GRID}>
        <KpiTile
          label='Power'
          value={`${card.power}/${MAX_POWER}`}
          icon={Wand2}
          tone='verdigris'
          hint='Stronger rites cost more and risk more'
          meter={{ value: card.power, max: MAX_POWER, label: 'Power' }}
        />
        <KpiTile
          label='Backlash'
          value={`${card.backlash_chance}%`}
          icon={backlash.icon}
          tone='danger'
          hint={`When it goes wrong: ${backlash.label.toLowerCase()}`}
          meter={{
            value: card.backlash_chance,
            max: PERCENT,
            label: 'Backlash chance',
          }}
        />
        <KpiTile
          label='Workings'
          value={card.effects.length}
          icon={Sparkles}
          tone='gold'
          hint='What it does when worked'
        />
        <KpiTile
          label='Cast'
          value={card.castings.length}
          icon={History}
          tone='info'
          hint={
            card.castings.length > 0
              ? `${worked} of ${card.castings.length} took hold`
              : 'It has never been worked'
          }
        />
      </div>
      <div className={LORE_GRID}>
        <LoreCard title='What it does' icon={Sparkles}>
          {card.effects.length === 0 ? (
            <Muted>It does nothing yet.</Muted>
          ) : (
            <ul
              data-surface='RiteEffects'
              className='flex min-w-0 flex-col gap-2'
            >
              <Paged items={card.effects} as='li'>
                {(row) => {
                  const spec = lookup(EFFECTS, row.effect)
                  return (
                    <li key={row.effect}>
                      <StatBar
                        label={
                          row.detail
                            ? `${spec.label} · ${row.detail}`
                            : spec.label
                        }
                        value={row.magnitude}
                        max={MAX_POWER}
                        icon={spec.icon}
                        tone='verdigris'
                      />
                    </li>
                  )
                }}
              </Paged>
            </ul>
          )}
        </LoreCard>
        <LoreCard title='Its price' icon={Coins} tone='warning'>
          <TermChips
            entries={card.cost}
            table={RITE_COSTS}
            empty='It asks for nothing.'
          />
          {needs.length > 0 && (
            <div className='flex min-w-0 flex-col gap-1.5'>
              <Label>It needs</Label>
              <PagedList
                items={needs}
                initial={12}
                noun={['entry', 'entries']}
                as='div'
                className='flex min-w-0 flex-wrap gap-1.5'
                itemKey={([key]) => key}
              >
                {([key, value]) => (
                  <NamedChip
                    key={key}
                    spec={{ label: '', icon: Check, tone: 'muted' }}
                  >
                    {`${sentence(key)}: ${sentence(String(value))}`}
                  </NamedChip>
                )}
              </PagedList>
            </div>
          )}
        </LoreCard>
        <LoreCard title='Work the rite' icon={Wand2} tone='verdigris' wide>
          <div
            data-surface='CastRite'
            className='flex min-w-0 flex-wrap items-end gap-2'
          >
            <div className='flex min-w-0 flex-1 basis-48 flex-col gap-1'>
              <Label>Caster</Label>
              <EntityPicker
                types={['mortal', 'cult']}
                value={caster}
                onChange={setCaster}
                placeholder='Caster'
              />
            </div>
            <div className='flex min-w-0 flex-1 basis-48 flex-col gap-1'>
              <Label>Target</Label>
              <EntityPicker
                types={['mortal', ...COMMUNITIES]}
                value={target}
                onChange={setTarget}
                placeholder='Target (optional)'
              />
            </div>
            <Button
              disabled={busy !== null || caster === null}
              disabledReason={
                busy ?? (caster === null ? 'Choose a caster' : undefined)
              }
              onClick={() => cast.mutate(undefined)}
            >
              <Wand2 />
              Work the rite
            </Button>
          </div>
        </LoreCard>
        <LoreCard
          title='Castings'
          icon={History}
          tone='info'
          wide
          aside={<Badge variant='secondary'>{card.castings.length}</Badge>}
        >
          {card.castings.length === 0 ? (
            <Muted>It has never been worked.</Muted>
          ) : (
            <div data-surface='Castings'>
              <Timeline label='Castings'>
                <Paged items={card.castings} as='li'>
                  {(row, index) => {
                    const spec = lookup(EFFECTS, row.effect)
                    return (
                      <TimelineItem
                        key={row.id}
                        icon={row.succeeded ? spec.icon : TriangleAlert}
                        tone={row.succeeded ? 'success' : 'destructive'}
                        title={
                          row.succeeded
                            ? `${spec.label} took hold`
                            : `${spec.label} failed`
                        }
                        timestamp={`Epoch ${row.epoch}`}
                        last={index === card.castings.length - 1}
                      >
                        <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
                          <RefChip icon={User} label='By' item={row.caster} />
                          <RefChip icon={Target} label='On' item={row.target} />
                          {row.backlash && (
                            <NamedChip
                              spec={lookup(BACKLASHES, row.backlash)}
                            />
                          )}
                        </div>
                      </TimelineItem>
                    )
                  }}
                </Paged>
              </Timeline>
            </div>
          )}
        </LoreCard>
      </div>
      <LoreAdjust
        entityId={id}
        noun='rite'
        locked={card.locked}
        blocked={blocked}
      >
        <AdjustBlock title='The rite' icon={school.icon}>
          <LoreFields
            entityId={id}
            surface='RiteForm'
            fields={[
              { key: 'school', kind: 'enum', table: SCHOOLS },
              { key: 'source', kind: 'enum', table: SOURCES },
              { key: 'backlash', kind: 'enum', table: BACKLASHES },
              { key: 'power', kind: 'number', min: 1, max: MAX_POWER },
              { key: 'backlash_chance', kind: 'number', min: 0, max: PERCENT },
              { key: 'holy', kind: 'bool' },
              { key: 'heretical', kind: 'bool' },
            ]}
            current={card}
            blocked={blocked}
          />
        </AdjustBlock>
        <AdjustBlock title='Its price' icon={Coins}>
          <DictField
            entityId={id}
            spec={{ key: 'cost', label: 'The price', value: card.cost }}
            blocked={blocked}
            table={RITE_COSTS}
          />
        </AdjustBlock>
        <AdjustBlock title='What it does' icon={Sparkles}>
          {card.effects.length > 0 && (
            <RowEditors>
              <Paged items={card.effects}>
                {(row) => {
                  const spec = lookup(EFFECTS, row.effect)
                  return (
                    <RowEditor
                      key={row.effect}
                      label={`${spec.label} magnitude`}
                      icon={spec.icon}
                      value={row.magnitude}
                      blocked={busy}
                      onSave={(magnitude) =>
                        shape.mutate({ effect: row.effect, magnitude })
                      }
                    >
                      <Button
                        size='icon'
                        variant='ghost'
                        aria-label={`Remove ${spec.label}`}
                        disabled={busy !== null}
                        disabledReason={busy ?? undefined}
                        onClick={() =>
                          shape.mutate({ effect: row.effect, magnitude: 0 })
                        }
                      >
                        <Trash2 />
                      </Button>
                    </RowEditor>
                  )
                }}
              </Paged>
            </RowEditors>
          )}
          <div className='flex min-w-0 flex-wrap items-end gap-2'>
            <div className='min-w-0 flex-1 basis-48'>
              <ChoicePicker
                label='Add a working'
                value={effect}
                table={Object.fromEntries(
                  Object.entries(EFFECTS).filter(
                    ([key]) => !card.effects.some((row) => row.effect === key)
                  )
                )}
                blocked={busy}
                placeholder='Choose'
                onPick={setEffect}
              />
            </div>
            <Button
              size='sm'
              variant='outline'
              disabled={busy !== null || effect === ''}
              disabledReason={
                busy ?? (effect === '' ? 'Choose a working' : undefined)
              }
              onClick={() => shape.mutate({ effect, magnitude: 3 })}
            >
              <Plus />
              Add
            </Button>
          </div>
        </AdjustBlock>
        <RiteControls id={id} card={card} blocked={blocked} />
      </LoreAdjust>
    </div>
  )
}
