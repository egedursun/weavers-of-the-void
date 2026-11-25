import { useState } from 'react'
import {
  Ban,
  BookText,
  CalendarHeart,
  GitMerge,
  Languages,
  Plus,
  Sparkles,
  Star,
  Target,
  Users,
} from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { KpiTile, Paged, PagedList } from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { EntityPicker } from '@/features/cosmos/EntityPicker'
import {
  AdjustBlock,
  DictField,
  LoreAdjust,
  LoreCard,
  LoreFields,
  LoreHero,
  MeterList,
  MeterRow,
  RefChip,
  RowEditor,
  RowEditors,
} from '../LoreFields'
import { ART_DISCIPLINES } from '../discoveryLabels'
import {
  KPI_GRID,
  LORE_GRID,
  PERCENT,
  TRADITION_KINDS,
  busyOf,
  lookup,
  useLoreEdit,
} from '../model'
import { useLoreAction } from './controlParts'
import { type Card, COMMUNITIES } from './shared'

const HOLDER_TYPES = [...COMMUNITIES, 'mortal']

export function ArtFormPanel({
  id,
  card,
  blocked,
}: {
  id: number
  card: Card<'art_form'>
  blocked: string | null
}) {
  const practise = useLoreAction(
    'art_form:practitioner',
    (value: { holder: number; mastery: number; present: boolean }) => ({
      art_form_id: id,
      holder_id: value.holder,
      mastery: value.mastery,
      present: value.present,
    })
  )
  const [holder, setHolder] = useState<number | null>(null)
  const edit = useLoreEdit(id)
  const busy = busyOf(blocked, practise.isPending)
  const discipline = ART_DISCIPLINES[card.discipline]
  const parts = Object.fromEntries(
    card.parts.map((part) => [part, lookup({}, part)])
  )
  const mean =
    card.practitioners.length === 0
      ? 0
      : Math.round(
          card.practitioners.reduce((sum, row) => sum + row.mastery, 0) /
            card.practitioners.length
        )
  return (
    <div data-surface='ArtFormCard' className='flex min-w-0 flex-col gap-4'>
      <LoreHero
        spec={discipline}
        kicker={`${card.discipline_label} of the mortals`}
        hint='Practitioners master it, artworks made in it borrow its prestige, and it is lost when no one keeps it.'
      >
        <RefChip icon={Users} label='First practised in' item={card.origin} />
        <RefChip icon={Star} label='Founded by' item={card.founder} />
        <RefChip
          icon={Languages}
          label='Tied to the tongue'
          item={card.language}
        />
        {card.sacred && (
          <Badge variant='default'>
            <Sparkles aria-hidden='true' />
            Sacred
          </Badge>
        )}
        {card.notation && (
          <Badge variant='secondary'>
            <BookText aria-hidden='true' />
            Written down
          </Badge>
        )}
      </LoreHero>
      <div className={KPI_GRID}>
        <KpiTile
          label='Practitioners'
          value={card.practitioners.length}
          icon={Users}
          tone='info'
          hint='Peoples and mortals who practise it'
        />
        <KpiTile
          label='Prestige'
          value={card.prestige}
          icon={Star}
          tone='gold'
          meter={{ value: card.prestige, max: PERCENT, label: 'Prestige' }}
          hint='How highly it is esteemed; it rises as more take it up'
        />
        <KpiTile
          label='Difficulty'
          value={card.difficulty}
          icon={Target}
          tone='warning'
          meter={{ value: card.difficulty, max: PERCENT, label: 'Difficulty' }}
          hint='The skill it takes to master'
        />
        <KpiTile
          label='Mastery'
          value={`${mean}%`}
          icon={Sparkles}
          tone='verdigris'
          meter={{ value: mean, max: PERCENT, label: 'Mean mastery' }}
          hint='How well its practitioners know it, on average'
        />
      </div>
      <div className={LORE_GRID}>
        <LoreCard
          title='Its shape'
          icon={discipline.icon}
          tone={discipline.tone}
        >
          {card.parts.length === 0 ||
          Object.keys(card.structure).length === 0 ? (
            <Muted>Its shape has not been set down.</Muted>
          ) : (
            <dl className='grid min-w-0 grid-cols-1 gap-1.5'>
              {card.parts
                .filter((part) => part in card.structure)
                .map((part) => (
                  <div key={part} className='flex min-w-0 items-baseline gap-2'>
                    <dt>
                      <Muted as='span' variant='caption'>
                        {lookup({}, part).label}
                      </Muted>
                    </dt>
                    <dd className='min-w-0'>
                      <Text as='span'>{String(card.structure[part])}</Text>
                    </dd>
                  </div>
                ))}
            </dl>
          )}
        </LoreCard>
        <LoreCard title='Lineage' icon={GitMerge} tone='verdigris'>
          <div
            data-surface='ArtFormLineage'
            className='flex min-w-0 flex-col gap-2'
          >
            {card.parents.length === 0 && card.children.length === 0 && (
              <Muted>
                It was born alone and nothing has grown from it yet.
              </Muted>
            )}
            {card.parents.length > 0 && (
              <PagedList
                items={card.parents}
                initial={12}
                noun={['entry', 'entries']}
                as='div'
                className='flex min-w-0 flex-wrap gap-1.5'
                itemKey={(item) => item.id}
              >
                {(item) => (
                  <RefChip
                    key={item.id}
                    icon={GitMerge}
                    label='From'
                    item={item}
                  />
                )}
              </PagedList>
            )}
            {card.children.length > 0 && (
              <PagedList
                items={card.children}
                initial={12}
                noun={['entry', 'entries']}
                as='div'
                className='flex min-w-0 flex-wrap gap-1.5'
                itemKey={(item) => item.id}
              >
                {(item) => (
                  <RefChip
                    key={item.id}
                    icon={GitMerge}
                    label='Into'
                    item={item}
                  />
                )}
              </PagedList>
            )}
          </div>
        </LoreCard>
        <LoreCard
          title='Practitioners'
          icon={Users}
          tone='info'
          wide
          aside={<Badge variant='secondary'>{card.practitioners.length}</Badge>}
        >
          {card.practitioners.length === 0 ? (
            <Muted>
              No one practises it now; unless it is written down it will be
              lost.
            </Muted>
          ) : (
            <MeterList surface='ArtFormPractitioners'>
              <Paged items={card.practitioners}>
                {(row) => (
                  <MeterRow
                    key={row.holder.id}
                    item={row.holder}
                    label={`Mastery, since epoch ${row.since_epoch}`}
                    value={row.mastery}
                    icon={Users}
                    tone='info'
                  />
                )}
              </Paged>
            </MeterList>
          )}
        </LoreCard>
        <LoreCard title='Artworks made in it' icon={Sparkles} tone='gold'>
          {card.artworks.length === 0 ? (
            <Muted>No artwork is credited to it yet.</Muted>
          ) : (
            <div className='flex min-w-0 flex-wrap gap-1.5'>
              <Paged items={card.artworks}>
                {(item) => (
                  <RefChip key={item.id} icon={Sparkles} label='' item={item} />
                )}
              </Paged>
            </div>
          )}
        </LoreCard>
        <LoreCard title='Banned in' icon={Ban} tone='danger'>
          {card.banned_in.length === 0 ? (
            <Muted>No realm bans it. Ban it from a realm's era panel.</Muted>
          ) : (
            <PagedList
              items={card.banned_in}
              initial={12}
              noun={['entry', 'entries']}
              as='div'
              className='flex min-w-0 flex-wrap gap-1.5'
              itemKey={(item) => item.id}
            >
              {(item) => (
                <RefChip key={item.id} icon={Ban} label='' item={item} />
              )}
            </PagedList>
          )}
        </LoreCard>
      </div>
      <LoreAdjust
        entityId={id}
        noun='art form'
        locked={card.locked}
        blocked={blocked}
      >
        <AdjustBlock title='Its standing' icon={Star}>
          <LoreFields
            entityId={id}
            surface='ArtFormFields'
            fields={[
              { key: 'discipline', kind: 'enum', table: ART_DISCIPLINES },
              { key: 'prestige', kind: 'number', min: 0, max: PERCENT },
              { key: 'difficulty', kind: 'number', min: 0, max: PERCENT },
              { key: 'sacred', kind: 'bool' },
              { key: 'notation', kind: 'bool' },
            ]}
            current={card}
            locked={card.locked}
            blocked={blocked}
          />
        </AdjustBlock>
        <AdjustBlock title='Its shape' icon={discipline.icon}>
          <DictField
            entityId={id}
            spec={{
              key: 'structure',
              label: 'Its parts',
              value: card.structure,
            }}
            blocked={blocked}
            table={parts}
          />
        </AdjustBlock>
        <AdjustBlock title='Occasions it is made for' icon={CalendarHeart}>
          <div
            data-surface='ArtFormOccasions'
            className='flex min-w-0 flex-wrap gap-2'
          >
            {Object.entries(TRADITION_KINDS).map(([key, spec]) => {
              const chosen = card.occasions.includes(key)
              const Icon = spec.icon
              return (
                <Button
                  act={edit}
                  key={key}
                  size='sm'
                  variant={chosen ? 'default' : 'outline'}
                  aria-pressed={chosen}
                  disabled={busy !== null || edit.isPending}
                  disabledReason={
                    busy ?? (edit.isPending ? 'Working on it.' : undefined)
                  }
                  onClick={() =>
                    edit.mutate({
                      values: {
                        occasions: chosen
                          ? card.occasions.filter((item) => item !== key)
                          : [...card.occasions, key],
                      },
                    })
                  }
                >
                  <Icon />
                  {spec.label}
                </Button>
              )
            })}
          </div>
          <Muted variant='caption'>
            Traditions of these kinds grow stronger among those who practise it,
            as every tradition does for a sacred form.
          </Muted>
        </AdjustBlock>
        <AdjustBlock title='Practitioners' icon={Users}>
          {card.practitioners.length > 0 && (
            <RowEditors>
              <Paged items={card.practitioners}>
                {(row) => (
                  <RowEditor
                    act={practise}
                    key={row.holder.id}
                    label={row.holder.name}
                    icon={Users}
                    value={row.mastery}
                    max={PERCENT}
                    blocked={busy}
                    onSave={(mastery) =>
                      practise.mutate({
                        holder: row.holder.id,
                        mastery,
                        present: true,
                      })
                    }
                  >
                    <Button
                      act={practise}
                      type='button'
                      size='icon'
                      variant='ghost'
                      aria-label={`${row.holder.name} stops practising it`}
                      disabled={busy !== null}
                      disabledReason={busy ?? undefined}
                      onClick={() =>
                        practise.mutate({
                          holder: row.holder.id,
                          mastery: row.mastery,
                          present: false,
                        })
                      }
                    >
                      <Ban />
                    </Button>
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
              placeholder='Spread it to…'
            />
            <Button
              act={practise}
              size='sm'
              variant='outline'
              disabled={busy !== null || holder === null}
              disabledReason={
                busy ?? (holder === null ? 'Choose who takes it up' : undefined)
              }
              onClick={() =>
                holder !== null &&
                practise.mutate({ holder, mastery: 20, present: true })
              }
            >
              <Plus />
              Spread it
            </Button>
          </div>
        </AdjustBlock>
      </LoreAdjust>
    </div>
  )
}
