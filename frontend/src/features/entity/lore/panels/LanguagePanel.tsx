import { useState } from 'react'
import {
  BookOpen,
  Coins,
  Crown,
  Languages,
  Mic,
  Plus,
  Scale,
  Unlock,
  Users,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { ChangeChip, KpiTile, Paged } from '@/components/domain'
import { Label, Muted } from '@/components/typography'
import { EntityPicker } from '@/features/cosmos/EntityPicker'
import { useGodAction } from '@/features/pantheon/godAction'
import { HeldBadge } from '../CultureParts'
import {
  AdjustBlock,
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
} from '../LoreFields'
import { RegisterEditor, RegisterList } from '../RegisterParts'
import {
  KPI_GRID,
  LORE_GRID,
  LORE_KIND,
  PERCENT,
  SPEAKER_KINDS,
  busyOf,
  lookup,
  sentence,
} from '../model'
import { type Card, COMMUNITIES } from './shared'

export function LanguagePanel({
  id,
  card,
  blocked,
}: {
  id: number
  card: Card<'language'>
  blocked: string | null
}) {
  const [community, setCommunity] = useState<number | null>(null)
  const speakers = useGodAction<{
    community: number
    share: number
    kind: string
  }>({
    run: ({ community: target, share, kind }) =>
      unwrap(
        api.POST('/api/actions/language:speakers', {
          body: {
            community_id: target,
            language_id: id,
            kind: kind as 'second',
            share,
          },
        })
      ),
  })
  const kin = useGodAction<{ other: number; value: number }>({
    run: ({ other, value }) =>
      unwrap(
        api.POST('/api/actions/language:intelligibility', {
          body: { first_id: id, second_id: other, value },
        })
      ),
  })
  const releaseSpeakers = useGodAction<{ community: number; kind: string }>({
    run: ({ community: target, kind }) =>
      unwrap(
        api.POST('/api/actions/language:release_speakers', {
          body: {
            community_id: target,
            language_id: id,
            kind: kind as 'second',
          },
        })
      ),
  })
  const releaseKin = useGodAction<{ other: number }>({
    run: ({ other }) =>
      unwrap(
        api.POST('/api/actions/language:release_understanding', {
          body: { first_id: id, second_id: other },
        })
      ),
  })
  const busy = busyOf(
    blocked,
    speakers.isPending,
    kin.isPending,
    releaseSpeakers.isPending,
    releaseKin.isPending
  )
  const parts = Object.entries(card.prestige_parts)
  const near = card.kin
    .filter((row) => row.value > 0)
    .sort((left, right) => right.value - left.value)
  const far = card.kin.filter((row) => row.value <= 0)
  return (
    <div
      data-surface='LanguageStanding'
      className='flex min-w-0 flex-col gap-4'
    >
      <LoreHero
        spec={LORE_KIND.language}
        kicker='A living tongue'
        title={
          card.lingua_franca
            ? 'Tongue of the trade roads'
            : card.liturgical
              ? 'Tongue of worship'
              : 'A spoken tongue'
        }
        hint='Prestige draws learners to it; kin tongues understand it without a teacher.'
      >
        {card.lingua_franca && (
          <NamedChip
            spec={{ label: 'Lingua franca', icon: Coins, tone: 'gold' }}
          />
        )}
        {card.liturgical && <NamedChip spec={SPEAKER_KINDS.liturgical} />}
        {!card.lingua_franca && !card.liturgical && (
          <NamedChip
            spec={{ label: 'Everyday speech', icon: Mic, tone: 'muted' }}
          />
        )}
      </LoreHero>
      <div className={KPI_GRID}>
        <KpiTile
          label='Prestige'
          value={card.prestige}
          icon={Crown}
          hint='The power of its speakers, its literature and its holiness'
          meter={{ value: card.prestige, max: PERCENT, label: 'Prestige' }}
        />
        <KpiTile
          label='Standardisation'
          value={card.standardisation}
          icon={BookOpen}
          tone='verdigris'
          hint='Grammar schools fix its forms year by year'
          meter={{
            value: card.standardisation,
            max: PERCENT,
            label: 'Standardisation',
          }}
        />
        <KpiTile
          label='Speaking peoples'
          value={card.speakers.length}
          icon={Users}
          tone='info'
          hint='Communities that speak it as a first or second tongue'
        />
        <KpiTile
          label='Kin tongues'
          value={near.length}
          icon={Languages}
          tone={near.length > 0 ? 'verdigris' : 'muted'}
          hint={
            far.length > 0
              ? `Tongues that understand some of it; ${far.length} more share no word`
              : 'Tongues that understand some of it'
          }
        />
      </div>
      <div className={LORE_GRID}>
        <LoreCard
          title='Who speaks it'
          icon={Users}
          tone='info'
          wide
          aside={<Badge variant='secondary'>{card.speakers.length}</Badge>}
        >
          {card.speakers.length === 0 ? (
            <Muted>No community has taken it as a second tongue.</Muted>
          ) : (
            <MeterList surface='SpeakerCohorts'>
              <Paged items={card.speakers}>
                {(row) => {
                  const kind = lookup(SPEAKER_KINDS, row.kind)
                  return (
                    <MeterRow
                      key={`${row.community?.id}.${row.kind}`}
                      item={row.community}
                      label={`Share of its people, since epoch ${row.since_epoch}`}
                      value={row.share}
                      icon={kind.icon}
                      tone={kind.tone}
                    >
                      <NamedChip spec={kind} />
                    </MeterRow>
                  )
                }}
              </Paged>
            </MeterList>
          )}
        </LoreCard>
        <LoreCard title='Where its prestige comes from' icon={Crown} wide>
          {parts.length === 0 ? (
            <Muted>Nothing lends it standing yet.</Muted>
          ) : (
            <ul
              data-surface='PrestigeParts'
              className='flex min-w-0 flex-wrap gap-1.5'
            >
              {parts.map(([part, value]) => (
                <li key={part}>
                  <ChangeChip value={value} label={sentence(part)} />
                </li>
              ))}
            </ul>
          )}
        </LoreCard>
        <LoreCard
          title='Understood by'
          icon={Languages}
          tone='verdigris'
          wide
          aside={<Badge variant='secondary'>{card.kin.length}</Badge>}
        >
          {card.kin.length === 0 ? (
            <Muted>No other tongue makes sense of it.</Muted>
          ) : (
            <div
              data-surface='Intelligibility'
              className='flex min-w-0 flex-col gap-3'
            >
              {near.length > 0 && (
                <MeterList surface='KinNear'>
                  <Paged items={near}>
                    {(row) => (
                      <MeterRow
                        key={row.language?.id}
                        item={row.language}
                        label='How much its speakers understand'
                        value={row.value}
                        icon={Languages}
                        tone='verdigris'
                      />
                    )}
                  </Paged>
                </MeterList>
              )}
              {far.length > 0 && (
                <div className='flex min-w-0 flex-col gap-1.5'>
                  <Label>{`No word in common with ${far.length}`}</Label>
                  <ul className='flex min-w-0 flex-wrap gap-1.5'>
                    <Paged items={far} as='li'>
                      {(row) => (
                        <li key={row.language?.id}>
                          <RefChip
                            icon={Languages}
                            label=''
                            item={row.language}
                          />
                        </li>
                      )}
                    </Paged>
                  </ul>
                </div>
              )}
            </div>
          )}
        </LoreCard>
      </div>
      <LoreCard
        title='Where it is spoken, and how'
        icon={Scale}
        tone='gold'
        wide
      >
        <RegisterList rows={card.registers} surface='LanguageRegisters' />
        <Muted variant='caption'>
          Treaties are read in the court's tongue, preachers are heard in the
          liturgy, caravans bargain in the market tongue.
        </Muted>
      </LoreCard>
      <LoreAdjust
        entityId={id}
        noun='tongue'
        locked={card.locked}
        blocked={blocked}
      >
        <AdjustBlock title='Standing' icon={Crown}>
          <LoreFields
            entityId={id}
            surface='LanguageForm'
            fields={[
              { key: 'prestige', kind: 'number', min: 0, max: PERCENT },
              { key: 'standardisation', kind: 'number', min: 0, max: PERCENT },
              { key: 'liturgical', kind: 'bool' },
              { key: 'lingua_franca', kind: 'bool' },
            ]}
            current={card}
            blocked={blocked}
          />
        </AdjustBlock>
        <AdjustBlock title='Speakers' icon={Users}>
          {card.speakers.length > 0 && (
            <RowEditors>
              <Paged items={card.speakers}>
                {(row) => (
                  <RowEditor
                    key={`${row.community?.id}.${row.kind}`}
                    label={`${row.community?.name ?? 'Unknown'} share`}
                    icon={lookup(SPEAKER_KINDS, row.kind).icon}
                    value={row.share}
                    max={PERCENT}
                    blocked={busy}
                    onSave={(share) =>
                      speakers.mutate({
                        community: row.community?.id ?? 0,
                        share,
                        kind: row.kind,
                      })
                    }
                  >
                    <HeldBadge held={row.held} />
                    {row.held && (
                      <Button
                        size='icon'
                        variant='ghost'
                        aria-label={`Let the share in ${row.community?.name ?? 'it'} move again`}
                        disabled={busy !== null}
                        disabledReason={busy ?? undefined}
                        onClick={() =>
                          releaseSpeakers.mutate({
                            community: row.community?.id ?? 0,
                            kind: row.kind,
                          })
                        }
                      >
                        <Unlock />
                      </Button>
                    )}
                  </RowEditor>
                )}
              </Paged>
            </RowEditors>
          )}
          <div className='flex min-w-0 flex-wrap items-end gap-2'>
            <EntityPicker
              types={COMMUNITIES}
              value={community}
              onChange={setCommunity}
              placeholder='Teach it to…'
            />
            <Button
              size='sm'
              variant='outline'
              disabled={busy !== null || community === null}
              disabledReason={
                busy ?? (community === null ? 'Choose a community' : undefined)
              }
              onClick={() =>
                speakers.mutate({
                  community: community ?? 0,
                  share: 10,
                  kind: 'second',
                })
              }
            >
              <Plus />
              Teach the tongue
            </Button>
          </div>
        </AdjustBlock>
        <AdjustBlock title='Registers' icon={Scale}>
          <RegisterEditor
            languageId={id}
            rows={card.registers}
            blocked={blocked}
          />
        </AdjustBlock>
        {card.kin.length > 0 && (
          <AdjustBlock title='Understanding' icon={Languages}>
            <RowEditors>
              <Paged items={card.kin}>
                {(row) => (
                  <RowEditor
                    key={row.language?.id}
                    label={`${row.language?.name ?? 'Unknown'} understanding`}
                    icon={Languages}
                    value={row.value}
                    max={PERCENT}
                    blocked={busy}
                    onSave={(value) =>
                      kin.mutate({ other: row.language?.id ?? 0, value })
                    }
                  >
                    <HeldBadge held={row.held} />
                    {row.held && (
                      <Button
                        size='icon'
                        variant='ghost'
                        aria-label={`Let the world measure ${row.language?.name ?? 'it'} again`}
                        disabled={busy !== null}
                        disabledReason={busy ?? undefined}
                        onClick={() =>
                          releaseKin.mutate({ other: row.language?.id ?? 0 })
                        }
                      >
                        <Unlock />
                      </Button>
                    )}
                  </RowEditor>
                )}
              </Paged>
            </RowEditors>
          </AdjustBlock>
        )}
      </LoreAdjust>
    </div>
  )
}
