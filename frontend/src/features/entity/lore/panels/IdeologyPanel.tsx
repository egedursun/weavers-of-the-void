import { useState } from 'react'
import {
  Crown,
  HeartPulse,
  Megaphone,
  PenLine,
  Plus,
  ScrollText,
  Sprout,
  Users,
  X,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import { KpiTile, StatBar } from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { EntityPicker } from '@/features/cosmos/EntityPicker'
import { useGodAction } from '@/features/pantheon/godAction'
import {
  AdjustBlock,
  ChoicePicker,
  DictField,
  LoreAdjust,
  LoreCard,
  LoreHero,
  MeterList,
  MeterRow,
  NamedChip,
  RefChip,
  RowEditor,
  RowEditors,
  ShiftChips,
} from '../LoreFields'
import {
  CLASSES,
  KPI_GRID,
  LORE_GRID,
  LORE_KIND,
  PERCENT,
  TENETS,
  VALUES,
  busyOf,
  lookup,
} from '../model'
import { IdeologyControls } from './MindControls'
import { type Card, COMMUNITIES, average } from './shared'

export function IdeologyPanel({
  id,
  card,
  blocked,
}: {
  id: number
  card: Card<'ideology'>
  blocked: string | null
}) {
  const [tenet, setTenet] = useState('')
  const [community, setCommunity] = useState<number | null>(null)
  const teach = useGodAction<{ tenet: string; held: boolean }>({
    run: ({ tenet: chosen, held }) =>
      unwrap(
        api.POST('/api/actions/creed:tenet', {
          body: { ideology_id: id, tenet: chosen as 'legalism', held },
        })
      ),
  })
  const adhere = useGodAction<{
    community: number
    strength: number
    state: boolean
  }>({
    run: ({ community: target, strength, state }) =>
      unwrap(
        api.POST('/api/actions/creed:adherent', {
          body: { ideology_id: id, community_id: target, strength, state },
        })
      ),
  })
  const busy = busyOf(blocked, teach.isPending, adhere.isPending)
  const states = card.adherents.filter((row) => row.state).length
  const appeal = Object.entries(card.appeal).sort(([, a], [, b]) => b - a)
  const lead = card.tenets[0]
    ? lookup(TENETS, card.tenets[0])
    : LORE_KIND.ideology
  return (
    <div data-surface='IdeologyCard' className='flex min-w-0 flex-col gap-4'>
      <LoreHero
        spec={{
          ...lead,
          label: card.tenets.length > 0 ? lead.label : 'An unformed creed',
        }}
        kicker='A creed of the mortals'
        hint='Its tenets press values on its adherents; a realm that takes it as its own leans its decisions toward it.'
      >
        <RefChip icon={PenLine} label='Taught by' item={card.founder} />
        {card.tenets.map((item) => (
          <NamedChip key={item} spec={lookup(TENETS, item)} />
        ))}
      </LoreHero>
      <div className={KPI_GRID}>
        <KpiTile
          label='Adherents'
          value={card.adherents.length}
          icon={Users}
          tone='info'
          hint='Communities that hold it'
        />
        <KpiTile
          label='Adherence'
          value={`${average(card.adherents.map((row) => row.strength))}%`}
          icon={HeartPulse}
          tone='gold'
          hint='How firmly its adherents hold it, on average'
          meter={{
            value: average(card.adherents.map((row) => row.strength)),
            max: PERCENT,
            label: 'Adherence',
          }}
        />
        <KpiTile
          label='State creed of'
          value={states}
          icon={Crown}
          tone={states > 0 ? 'gold' : 'muted'}
          hint='Realms that have made it their own'
        />
        <KpiTile
          label='Tenets'
          value={card.tenets.length}
          icon={ScrollText}
          tone='verdigris'
          hint='The principles it holds'
        />
      </div>
      <div className={LORE_GRID}>
        <LoreCard title='Values it presses' icon={Sprout} tone='success'>
          <ShiftChips
            entries={card.values}
            table={VALUES}
            empty='It presses no value.'
          />
        </LoreCard>
        <LoreCard title='Who it calls to' icon={Megaphone} tone='verdigris'>
          {appeal.length === 0 ? (
            <Muted>It calls to no class in particular.</Muted>
          ) : (
            <div className='flex min-w-0 flex-col gap-2'>
              {appeal.map(([key, value]) => {
                const spec = lookup(CLASSES, key)
                return (
                  <StatBar
                    key={key}
                    label={spec.label}
                    value={value}
                    max={PERCENT}
                    icon={spec.icon}
                    tone='verdigris'
                  />
                )
              })}
            </div>
          )}
        </LoreCard>
        <LoreCard
          title='Adherents'
          icon={Users}
          tone='info'
          wide
          aside={<Badge variant='secondary'>{card.adherents.length}</Badge>}
        >
          {card.adherents.length === 0 ? (
            <Muted>No community holds it yet.</Muted>
          ) : (
            <MeterList surface='CreedAdherents'>
              {card.adherents.map((row) => (
                <MeterRow
                  key={row.community?.id}
                  item={row.community}
                  label={`Adherence, since epoch ${row.since_epoch}`}
                  value={row.strength}
                  icon={row.state ? Crown : Users}
                  tone={row.state ? 'gold' : 'info'}
                >
                  {row.state && (
                    <Badge size='sm' variant='default'>
                      State creed
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
        noun='creed'
        locked={card.locked}
        blocked={blocked}
      >
        <AdjustBlock title='Tenets' icon={ScrollText}>
          <ul
            data-surface='CreedTenets'
            className='flex min-w-0 flex-wrap gap-2'
          >
            {card.tenets.length === 0 && <Muted>It holds no tenet yet.</Muted>}
            {card.tenets.map((item) => {
              const spec = lookup(TENETS, item)
              const Icon = spec.icon
              return (
                <li
                  key={item}
                  className='flex items-center gap-1 rounded-md border bg-muted/30 py-0.5 pr-0.5 pl-2'
                >
                  <Icon
                    aria-hidden='true'
                    className='size-icon-xs text-muted-foreground'
                  />
                  <Text as='span' variant='caption' weight='medium'>
                    {spec.label}
                  </Text>
                  <Button
                    size='icon-sm'
                    variant='ghost'
                    aria-label={`Cast off ${spec.label}`}
                    disabled={busy !== null}
                    disabledReason={busy ?? undefined}
                    onClick={() => teach.mutate({ tenet: item, held: false })}
                  >
                    <X />
                  </Button>
                </li>
              )
            })}
          </ul>
          <div className='flex min-w-0 flex-wrap items-end gap-2'>
            <div className='min-w-0 flex-1 basis-48'>
              <ChoicePicker
                label='Teach a tenet'
                value={tenet}
                table={Object.fromEntries(
                  Object.entries(TENETS).filter(
                    ([key]) => !card.tenets.includes(key as never)
                  )
                )}
                blocked={busy}
                placeholder='Choose a tenet'
                onPick={setTenet}
              />
            </div>
            <Button
              size='sm'
              variant='outline'
              disabled={busy !== null || tenet === ''}
              disabledReason={
                busy ?? (tenet === '' ? 'Choose a tenet' : undefined)
              }
              onClick={() => teach.mutate({ tenet, held: true })}
            >
              <Plus />
              Teach it
            </Button>
          </div>
        </AdjustBlock>
        <div className={LORE_GRID}>
          <AdjustBlock title='Values it presses' icon={Sprout}>
            <DictField
              entityId={id}
              spec={{
                key: 'value_delta',
                label: 'Its values',
                value: card.values,
              }}
              blocked={blocked}
              table={VALUES}
            />
          </AdjustBlock>
          <AdjustBlock title='Who it calls to' icon={Megaphone}>
            <DictField
              entityId={id}
              spec={{ key: 'appeal', label: 'Its appeal', value: card.appeal }}
              blocked={blocked}
              table={CLASSES}
            />
          </AdjustBlock>
        </div>
        <AdjustBlock title='Adherents' icon={Users}>
          {card.adherents.length > 0 && (
            <RowEditors>
              {card.adherents.map((row) => (
                <RowEditor
                  key={row.community?.id}
                  label={row.community?.name ?? 'Unknown'}
                  icon={Users}
                  value={row.strength}
                  max={PERCENT}
                  blocked={busy}
                  onSave={(strength) =>
                    adhere.mutate({
                      community: row.community?.id ?? 0,
                      strength,
                      state: row.state,
                    })
                  }
                >
                  <label className='flex h-control-md shrink-0 items-center gap-1.5'>
                    <Switch
                      checked={row.state}
                      disabled={busy !== null}
                      aria-label='State creed'
                      onCheckedChange={(next) =>
                        adhere.mutate({
                          community: row.community?.id ?? 0,
                          strength: row.strength,
                          state: next,
                        })
                      }
                    />
                    <Crown
                      aria-hidden='true'
                      className='size-icon-sm text-primary'
                    />
                  </label>
                </RowEditor>
              ))}
            </RowEditors>
          )}
          <div className='flex min-w-0 flex-wrap items-end gap-2'>
            <EntityPicker
              types={COMMUNITIES}
              value={community}
              onChange={setCommunity}
              placeholder='Win over…'
            />
            <Button
              size='sm'
              variant='outline'
              disabled={busy !== null || community === null}
              disabledReason={
                busy ?? (community === null ? 'Choose a community' : undefined)
              }
              onClick={() =>
                adhere.mutate({
                  community: community ?? 0,
                  strength: 25,
                  state: false,
                })
              }
            >
              <Plus />
              Win them over
            </Button>
          </div>
        </AdjustBlock>
        <IdeologyControls id={id} card={card} blocked={blocked} />
      </LoreAdjust>
    </div>
  )
}
