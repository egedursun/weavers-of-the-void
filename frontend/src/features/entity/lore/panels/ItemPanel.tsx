import { useState } from 'react'
import {
  BookOpen,
  Coins,
  Crown,
  Flag,
  Hammer,
  Hand,
  History,
  Ruler,
  ScrollText,
  Shield,
  Sparkles,
  Target,
  User,
  Weight,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  KpiTile,
  MiniStat,
  StatBar,
  Timeline,
  TimelineItem,
  Paged,
} from '@/components/domain'
import { Muted } from '@/components/typography'
import { useGodAction } from '@/features/pantheon/godAction'
import {
  AdjustBlock,
  ChoicePicker,
  LoreAdjust,
  LoreCard,
  LoreFields,
  LoreHero,
  NO_RECORD,
  NamedChip,
  RefChip,
  RoleRow,
  RowEditor,
  RowEditors,
  Who,
} from '../LoreFields'
import { useCustomKinds } from '../forge/kindApi'
import {
  CURSES,
  DEEDS,
  EFFECTS,
  ITEM_CLASSES,
  KPI_GRID,
  LORE_GRID,
  PERCENT,
  busyOf,
  lookup,
} from '../model'
import { ItemControls } from './ItemControls'
import { type Card, WORN, wear } from './shared'

export function ItemPanel({
  id,
  card,
  blocked,
}: {
  id: number
  card: Card<'item'>
  blocked: string | null
}) {
  const [effect, setEffect] = useState('')
  const enchant = useGodAction<{ effect: string; strength: number }>({
    run: ({ effect: chosen, strength }) =>
      unwrap(
        api.POST('/api/actions/item:enchant', {
          body: { item_id: id, effect: chosen as 'ward', strength },
        })
      ),
  })
  const busy = busyOf(blocked, enchant.isPending)
  const kind = lookup(ITEM_CLASSES, card.item_class)
  const curse = lookup(CURSES, card.curse)
  const customKinds = useCustomKinds('item_class').data?.kinds ?? []
  const customClass = customKinds.find(
    (item) => item.id === card.custom_class_id
  )
  const customTable = Object.fromEntries([
    [
      NO_RECORD,
      {
        label: 'No class of your own',
        icon: kind.icon,
        tone: 'muted' as const,
      },
    ],
    ...customKinds.map((item) => [
      String(item.id),
      {
        label: item.name,
        icon: kind.icon,
        tone: 'gold' as const,
        hint: item.description,
      },
    ]),
  ])
  return (
    <div data-surface='ItemCard' className='flex min-w-0 flex-col gap-4'>
      <LoreHero
        spec={kind}
        kicker='A made thing'
        hint={card.curse !== 'none' ? curse.hint : undefined}
      >
        {card.curse !== 'none' && (
          <NamedChip
            spec={curse}
          >{`Cursed: ${curse.label.toLowerCase()}`}</NamedChip>
        )}
        {customClass && (
          <NamedChip
            spec={{ label: '', icon: kind.icon, tone: 'gold' }}
          >{`Of the ${customClass.name} class`}</NamedChip>
        )}
        {card.material && (
          <NamedChip spec={{ label: '', icon: Hammer, tone: 'muted' }}>
            {`Made of ${card.material.replaceAll('_', ' ')}`}
          </NamedChip>
        )}
        {card.symbol && (
          <NamedChip
            spec={{ label: 'A symbol of its people', icon: Flag, tone: 'gold' }}
          />
        )}
        {card.damage_type && (
          <NamedChip spec={{ label: '', icon: Target, tone: 'muted' }}>
            {`Deals ${card.damage_type.replaceAll('_', ' ')}`}
          </NamedChip>
        )}
      </LoreHero>
      <div className={KPI_GRID}>
        <KpiTile
          label='Quality'
          value={card.quality}
          icon={Hammer}
          hint='The skill of its making'
          meter={{ value: card.quality, max: PERCENT, label: 'Quality' }}
        />
        <KpiTile
          label='Condition'
          value={card.condition}
          icon={Shield}
          tone={wear(card.condition)}
          hint={
            card.condition < WORN
              ? 'Near to breaking'
              : 'Wear from use and years'
          }
          meter={{ value: card.condition, max: PERCENT, label: 'Condition' }}
        />
        <KpiTile
          label='Renown'
          value={card.renown}
          icon={Sparkles}
          tone='verdigris'
          hint='Grows with every deed it is part of'
          meter={{ value: card.renown, max: PERCENT, label: 'Renown' }}
        />
        <KpiTile
          label='Worth'
          value={card.value}
          icon={Coins}
          tone='gold'
          hint='Its price in trade'
        />
      </div>
      <div className='grid min-w-0 grid-cols-2 gap-2 sm:grid-cols-3'>
        <MiniStat icon={Ruler} label='Reach' value={card.reach} />
        <MiniStat icon={Shield} label='Coverage' value={card.coverage} />
        <MiniStat icon={Weight} label='Weight' value={card.weight} />
      </div>
      <div className={LORE_GRID}>
        <LoreCard title='Hands it has known' icon={Hand}>
          {!card.maker && !card.owner && !card.regalia_of ? (
            <Muted>No one is remembered with it.</Muted>
          ) : (
            <div className='flex min-w-0 flex-col gap-2.5'>
              {card.maker && (
                <RoleRow icon={Hammer} tone='gold' label='Made by'>
                  <Who item={card.maker} />
                </RoleRow>
              )}
              {card.owner && (
                <RoleRow icon={Hand} tone='info' label='Held by'>
                  <Who item={card.owner} />
                </RoleRow>
              )}
              {card.regalia_of && (
                <RoleRow icon={Crown} tone='gold' label='Regalia of'>
                  <Who item={card.regalia_of} />
                </RoleRow>
              )}
            </div>
          )}
        </LoreCard>
        <LoreCard
          title='Enchantments'
          icon={Sparkles}
          tone='verdigris'
          aside={<Badge variant='secondary'>{card.enchantments.length}</Badge>}
        >
          {card.enchantments.length === 0 ? (
            <Muted>No spell is bound into it.</Muted>
          ) : (
            <ul
              data-surface='Enchantments'
              className='flex min-w-0 flex-col gap-2'
            >
              <Paged items={card.enchantments} as='li'>
                {(row) => {
                  const spec = lookup(EFFECTS, row.effect)
                  return (
                    <li key={row.effect}>
                      <StatBar
                        label={spec.label}
                        value={row.strength}
                        max={PERCENT}
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
        {card.contents.length > 0 && (
          <LoreCard title='Written within' icon={BookOpen} tone='info' wide>
            <ul
              data-surface='BookContents'
              className='flex min-w-0 flex-wrap gap-1.5'
            >
              <Paged items={card.contents} as='li'>
                {(item) => (
                  <li key={item.id}>
                    <RefChip icon={ScrollText} label='' item={item} />
                  </li>
                )}
              </Paged>
            </ul>
          </LoreCard>
        )}
        <LoreCard
          title='Its story'
          icon={History}
          tone='info'
          wide
          aside={<Badge variant='secondary'>{card.history.length}</Badge>}
        >
          {card.history.length === 0 ? (
            <Muted>Nothing has befallen it yet.</Muted>
          ) : (
            <div data-surface='ItemHistory'>
              <Timeline label='Item history'>
                <Paged items={card.history} as='li'>
                  {(row, index) => {
                    const spec = lookup(DEEDS, row.deed)
                    return (
                      <TimelineItem
                        key={`${row.epoch}.${index}`}
                        icon={spec.icon}
                        tone={
                          spec.tone === 'danger'
                            ? 'destructive'
                            : spec.tone === 'gold'
                              ? 'primary'
                              : spec.tone === 'success'
                                ? 'success'
                                : spec.tone === 'warning'
                                  ? 'warning'
                                  : 'default'
                        }
                        title={spec.label}
                        timestamp={`Epoch ${row.epoch}`}
                        last={index === card.history.length - 1}
                      >
                        <div className='flex min-w-0 flex-col gap-1'>
                          {row.actor && (
                            <div>
                              <RefChip
                                icon={User}
                                label='By'
                                item={row.actor}
                              />
                            </div>
                          )}
                          {row.note && <Muted>{row.note}</Muted>}
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
        noun='item'
        locked={card.locked}
        blocked={blocked}
      >
        <AdjustBlock title='The item' icon={kind.icon}>
          <LoreFields
            entityId={id}
            surface='ItemForm'
            fields={[
              { key: 'item_class', kind: 'enum', table: ITEM_CLASSES },
              { key: 'curse', kind: 'enum', table: CURSES },
              { key: 'custom_class_id', kind: 'record', table: customTable },
              { key: 'material', kind: 'text', nullable: true },
              { key: 'quality', kind: 'number', min: 0, max: PERCENT },
              { key: 'condition', kind: 'number', min: 0, max: PERCENT },
              { key: 'renown', kind: 'number', min: 0, max: PERCENT },
              { key: 'value', kind: 'number', min: 0 },
              { key: 'reach', kind: 'number', min: 0 },
              { key: 'coverage', kind: 'number', min: 0 },
              { key: 'weight', kind: 'number', min: 0 },
              { key: 'symbol', kind: 'bool' },
            ]}
            current={card}
            blocked={blocked}
          />
        </AdjustBlock>
        <AdjustBlock title='Enchantments' icon={Sparkles}>
          {card.enchantments.length > 0 && (
            <RowEditors>
              <Paged items={card.enchantments}>
                {(row) => {
                  const spec = lookup(EFFECTS, row.effect)
                  return (
                    <RowEditor
                      key={row.effect}
                      label={`${spec.label} strength`}
                      icon={spec.icon}
                      value={row.strength}
                      max={PERCENT}
                      blocked={busy}
                      onSave={(strength) =>
                        enchant.mutate({ effect: row.effect, strength })
                      }
                    />
                  )
                }}
              </Paged>
            </RowEditors>
          )}
          <div className='flex min-w-0 flex-wrap items-end gap-2'>
            <div className='min-w-0 flex-1 basis-48'>
              <ChoicePicker
                label='Enchant with'
                value={effect}
                table={Object.fromEntries(
                  Object.entries(EFFECTS).filter(
                    ([key]) =>
                      !card.enchantments.some((row) => row.effect === key)
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
                busy ?? (effect === '' ? 'Choose an enchantment' : undefined)
              }
              onClick={() => enchant.mutate({ effect, strength: 20 })}
            >
              <Sparkles />
              Enchant
            </Button>
          </div>
        </AdjustBlock>
        <ItemControls id={id} card={card} blocked={blocked} />
      </LoreAdjust>
    </div>
  )
}
