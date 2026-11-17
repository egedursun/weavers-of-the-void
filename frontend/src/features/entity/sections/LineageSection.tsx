import { useState } from 'react'
import { Eraser, Plus, RefreshCw, X } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { type components } from '@/api/generated/schema'
import { plural } from '@/lib/units'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import {
  EmptyState,
  EntityLink,
  KpiTile,
  Medallion,
  Paged,
  PagedList,
  Section,
} from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { SCHOOLS } from '@/features/entity/lore/model'
import { AdjustStats } from '@/features/pantheon/AdjustStats'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { named } from '../environment/labels'
import {
  type Gene,
  type Genome,
  type GiftStance,
  type Lineage,
  type Locus,
  type LocusKey,
  type Pool,
  useLineage,
} from '../lineage/api'
import {
  BLOOD_EFFECTS,
  GIFT_ICON,
  GROUP_ICON,
  HARMFUL_EFFECTS,
  LIKENESS_ICON,
  LINEAGE_ICON,
  LOOKS_ICON,
  POOL_ICON,
  STANCE_TONE,
} from '../lineage/labels'
import { ControlPanel, ItemRow, MindCard, MindPicker } from '../mind/parts'
import { ATTRIBUTE_ICONS } from '../mind/splitLabels'

const SPAN = 100
const POTENTIAL = 'potential.'
type Attribute = components['schemas']['Attribute']
const WORKING = 'Working on it.'

function why(blocked: string | null, ...pending: boolean[]): string | null {
  return blocked ?? (pending.some(Boolean) ? WORKING : null)
}

function alleleTable(locus: Locus | undefined): Record<string, string> {
  return Object.fromEntries(
    (locus?.alleles ?? []).map((allele) => [allele.key, allele.label])
  )
}

function GeneEditor({
  mortalId,
  gene,
  locus,
  blocked,
  hold,
}: {
  mortalId: number
  gene: Gene
  locus: Locus | undefined
  blocked: string | null
  hold: boolean
}) {
  const [first, setFirst] = useState(gene.first)
  const [second, setSecond] = useState(gene.second)
  const save = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/genome:gene', {
          body: {
            mortal_id: mortalId,
            locus: gene.locus,
            first,
            second,
            hold,
          },
        })
      ),
  })
  const busy = why(blocked, save.isPending)
  const table = alleleTable(locus)
  const outcomes = [first, second]
    .filter((key, index, keys) => keys.indexOf(key) === index)
    .flatMap(
      (key) =>
        locus?.alleles
          .find((allele) => allele.key === key)
          ?.effects.map((effect) => `${table[key] ?? key}: ${effect}`) ?? []
    )
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      <div className='grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-2'>
        <MindPicker
          label='From one parent'
          value={first}
          table={table}
          blocked={busy}
          onPick={setFirst}
        />
        <MindPicker
          label='From the other'
          value={second}
          table={table}
          blocked={busy}
          onPick={setSecond}
        />
      </div>
      <Muted variant='caption'>
        {outcomes.length > 0
          ? outcomes.join(' · ')
          : 'Neither allele moves the body or mind on its own.'}
      </Muted>
      <div className='flex justify-end'>
        <Button
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => save.mutate()}
        >
          Set this pair
        </Button>
      </div>
    </div>
  )
}

function GenomeCard({
  view,
  genome,
  blocked,
  hold,
}: {
  view: Lineage
  genome: Genome
  blocked: string | null
  hold: boolean
}) {
  const nodeId = view.node_id
  const redraw = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/genome:redraw', { body: { mortal_id: nodeId } })
      ),
  })
  const strike = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/genome:remove', { body: { mortal_id: nodeId } })
      ),
  })
  const busy = why(blocked, redraw.isPending, strike.isPending)
  const loci = new Map(view.loci.map((locus) => [locus.locus, locus]))
  return (
    <MindCard
      title='Blood and looks'
      icon={LINEAGE_ICON}
      wide
      hint='Each locus holds two alleles, one from each parent; the stronger shows. Looks, scars and the marks of afflictions make the face portraits keep.'
    >
      <Text>{genome.appearance || 'Nothing about this face stands out.'}</Text>
      <div className='grid min-w-0 grid-cols-1 gap-3 @lg/mind:grid-cols-3'>
        <KpiTile
          label='Beauty'
          value={genome.beauty}
          icon={LOOKS_ICON}
          tone='gold'
          meter={{ value: genome.beauty, max: SPAN, label: 'Beauty' }}
          hint='As their own people see it'
        />
        <KpiTile
          label='Recognisable'
          value={genome.recognisability}
          icon={LIKENESS_ICON}
          tone='info'
          meter={{
            value: genome.recognisability,
            max: SPAN,
            label: 'Recognisability',
          }}
          hint='How easily the face is known again'
        />
        <KpiTile
          label='Inbreeding'
          value={genome.inbreeding}
          icon={LINEAGE_ICON}
          tone={genome.inbreeding > 20 ? 'warning' : 'muted'}
          meter={{ value: genome.inbreeding, max: SPAN, label: 'Inbreeding' }}
          hint='Raises the odds of harmful alleles twice over'
          harmful
        />
      </div>
      <div className='flex min-w-0 flex-wrap gap-2'>
        {genome.divine_son && (
          <Badge variant='secondary'>
            {'Divine blood of '}
            <EntityLink kind='son' id={String(genome.divine_son.id)}>
              {genome.divine_son.name}
            </EntityLink>
          </Badge>
        )}
        {genome.marks.map((mark) => (
          <Badge key={mark} variant='outline'>
            {mark}
          </Badge>
        ))}
        {genome.likeness.map((item) => (
          <Badge key={item.parent.id} variant='outline'>
            {`${item.likeness}% like `}
            <EntityLink kind='entity' id={String(item.parent.id)}>
              {item.parent.name}
            </EntityLink>
          </Badge>
        ))}
      </div>
      <ItemRow
        icon={LOOKS_ICON}
        tone='gold'
        title='Set beauty, inbreeding, recognisability and inborn potential'
        meta={
          Object.keys(genome.potential).length > 0
            ? `Potential: ${Object.entries(genome.potential)
                .sort(([first], [second]) => first.localeCompare(second))
                .map(
                  ([key, value]) =>
                    `${named(ATTRIBUTE_ICONS, key).label} ${value}`
                )
                .join(', ')}`
            : 'Held values stop the world from reading them anew'
        }
        editLabel='genome values'
        editor={
          <AdjustStats
            id={`genome-${nodeId}`}
            inline
            groups={[
              {
                title: 'Blood',
                fields: [
                  {
                    key: 'beauty',
                    label: 'Beauty',
                    value: genome.beauty,
                    min: 0,
                    max: SPAN,
                  },
                  {
                    key: 'recognisability',
                    label: 'Recognisability',
                    value: genome.recognisability,
                    min: 0,
                    max: SPAN,
                  },
                  {
                    key: 'inbreeding',
                    label: 'Inbreeding',
                    value: genome.inbreeding,
                    min: 0,
                    max: SPAN,
                  },
                ],
              },
              {
                title: 'Inborn potential',
                fields: Object.entries(genome.potential)
                  .sort(([first], [second]) => first.localeCompare(second))
                  .map(([key, value]) => ({
                    key: `${POTENTIAL}${key}`,
                    label: named(ATTRIBUTE_ICONS, key).label,
                    value,
                    min: 0,
                    max: SPAN,
                  })),
              },
            ]}
            run={({ key, value }) =>
              unwrap(
                api.POST('/api/actions/genome:edit', {
                  body: key.startsWith(POTENTIAL)
                    ? {
                        mortal_id: nodeId,
                        potential: {
                          [key.slice(POTENTIAL.length)]: value,
                        } as Record<Attribute, number>,
                        clear_divine: false,
                        hold,
                      }
                    : {
                        mortal_id: nodeId,
                        [key]: value,
                        clear_divine: false,
                        hold,
                      },
                })
              )
            }
          />
        }
      />
      {geneGroups(genome.genes).map(({ group, label, genes }) => (
        <div
          key={group}
          role='group'
          aria-label={label}
          className='flex min-w-0 flex-col gap-2'
        >
          <div className='flex min-w-0 items-center gap-2'>
            <Medallion icon={GROUP_ICON[group]} tone='gold' size='sm' />
            <Text variant='caption' weight='semibold'>
              {label}
            </Text>
            <Badge variant='outline'>
              {plural(genes.length, 'locus', 'loci')}
            </Badge>
          </div>
          <Paged items={genes} initial={4} noun={['locus', 'loci']}>
            {(gene) => (
              <ItemRow
                key={gene.locus}
                icon={GROUP_ICON[gene.group]}
                tone={gene.group === 'gift' ? 'verdigris' : 'gold'}
                title={`${gene.label}: ${gene.shown_label}`}
                meta={[
                  `${alleleTable(loci.get(gene.locus))[gene.first] ?? gene.first} and ${alleleTable(loci.get(gene.locus))[gene.second] ?? gene.second}`,
                  ...gene.effects,
                ].join(' · ')}
                editLabel={`${gene.label} alleles`}
                editor={
                  <GeneEditor
                    mortalId={nodeId}
                    gene={gene}
                    locus={loci.get(gene.locus)}
                    blocked={blocked}
                    hold={hold}
                  />
                }
              />
            )}
          </Paged>
        </div>
      ))}
      <div className='flex min-w-0 flex-wrap justify-end gap-2'>
        <Button
          size='sm'
          variant='outline'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => redraw.mutate()}
        >
          <RefreshCw />
          Draw the blood anew
        </Button>
        <Button
          size='sm'
          variant='ghost'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => strike.mutate()}
        >
          <Eraser />
          Strike the genome
        </Button>
      </div>
    </MindCard>
  )
}

function geneGroups(genes: Gene[]) {
  const groups = new Map<
    Gene['group'],
    { group: Gene['group']; label: string; genes: Gene[] }
  >()
  for (const gene of genes) {
    const found = groups.get(gene.group) ?? {
      group: gene.group,
      label: gene.group_label,
      genes: [],
    }
    found.genes.push(gene)
    groups.set(gene.group, found)
  }
  return [...groups.values()]
}

function signedAmount(amount: number, perEpoch: boolean) {
  const sign = amount > 0 ? '+' : ''
  return perEpoch ? `${sign}${amount} health each epoch` : `${sign}${amount}%`
}

function BloodCard({ genome }: { genome: Genome }) {
  return (
    <MindCard
      title='What the blood does'
      icon={LINEAGE_ICON}
      hint='Loci lean the body, the senses, the temper and the aptitudes of a mortal; the leanings below are what this blood adds up to, what it carries hidden and the traits it tends toward.'
    >
      <div className='flex min-w-0 flex-col gap-2'>
        <Text variant='caption' weight='semibold'>
          Leanings of the blood
        </Text>
        {genome.blood_effects.length === 0 ? (
          <Muted variant='caption'>
            This blood leans neither way on health, children, healing, strain or
            climate.
          </Muted>
        ) : (
          <PagedList
            items={genome.blood_effects}
            initial={6}
            noun={['leaning', 'leanings']}
            as='div'
            className='flex min-w-0 flex-col gap-2'
            itemKey={(item) => item.effect}
          >
            {(item) => {
              const spec = BLOOD_EFFECTS[item.effect]
              const worse = HARMFUL_EFFECTS.has(item.effect)
                ? item.amount > 0
                : item.amount < 0
              return (
                <ItemRow
                  icon={spec.icon}
                  tone={worse ? 'danger' : 'success'}
                  title={`${spec.label}: ${signedAmount(item.amount, item.per_epoch)}`}
                  meta={item.label}
                />
              )
            }}
          </PagedList>
        )}
      </div>
      <div className='flex min-w-0 flex-col gap-2'>
        <Text variant='caption' weight='semibold'>
          Traits the blood tends toward
        </Text>
        {genome.tied_traits.length === 0 ? (
          <Muted variant='caption'>
            No locus here leans strongly enough to shape a trait.
          </Muted>
        ) : (
          <PagedList
            items={genome.tied_traits}
            initial={8}
            noun={['trait', 'traits']}
            as='div'
            className='flex min-w-0 flex-wrap gap-2'
            itemKey={(item) => `${item.locus}-${item.trait}`}
          >
            {(item) => (
              <Badge variant={item.held ? 'default' : 'outline'}>
                {`${item.trait_label} · ${item.locus_label}${item.held ? '' : ' · not taken'}`}
              </Badge>
            )}
          </PagedList>
        )}
      </div>
      <div className='flex min-w-0 flex-col gap-2'>
        <Text variant='caption' weight='semibold'>
          Carried, unseen, to children
        </Text>
        {genome.carried.length === 0 ? (
          <Muted variant='caption'>
            Every allele this blood carries also shows.
          </Muted>
        ) : (
          <PagedList
            items={genome.carried}
            initial={8}
            noun={['allele', 'alleles']}
            as='div'
            className='flex min-w-0 flex-wrap gap-2'
            itemKey={(item) => `${item.locus}-${item.allele}`}
          >
            {(item) => (
              <Badge variant={item.harmful ? 'destructive' : 'secondary'}>
                {`${item.locus_label}: ${item.allele_label}`}
              </Badge>
            )}
          </PagedList>
        )}
      </div>
    </MindCard>
  )
}

function GiftsCard({ genome }: { genome: Genome }) {
  return (
    <MindCard
      title='The magical gift'
      icon={GIFT_ICON}
      hint='Aptitude for each form of magic is carried in the blood; two gifted alleles or one wild allele make a mortal gifted.'
    >
      {genome.gifts.length === 0 ? (
        <Muted variant='caption'>
          No aptitude for any form runs in this blood.
        </Muted>
      ) : (
        <div className='flex min-w-0 flex-col gap-3'>
          {genome.gifts.map((gift) => (
            <div key={gift.school} className='flex min-w-0 flex-col gap-1'>
              <div className='flex min-w-0 items-center justify-between gap-2'>
                <Text variant='caption' weight='semibold'>
                  {SCHOOLS[gift.school].label}
                </Text>
                <Badge variant={gift.gifted ? 'default' : 'outline'}>
                  {gift.gifted
                    ? `Gifted ${gift.aptitude}`
                    : `Carrier ${gift.aptitude}`}
                </Badge>
              </div>
              <Progress
                value={gift.aptitude}
                size='sm'
                tone={gift.gifted ? 'success' : 'default'}
                aria-label={`${SCHOOLS[gift.school].label} aptitude ${gift.aptitude}`}
              />
            </div>
          ))}
        </div>
      )}
    </MindCard>
  )
}

function FrequencyEditor({
  peopleId,
  locus,
  hold,
}: {
  peopleId: number
  locus: Locus
  hold: boolean
}) {
  return (
    <AdjustStats
      id={`pool-${peopleId}-${locus.locus}`}
      inline
      groups={[
        {
          title: locus.label,
          fields: locus.alleles.map((allele) => ({
            key: allele.key,
            label: allele.label,
            value: allele.frequency ?? 0,
            min: 0,
            max: SPAN,
          })),
        },
      ]}
      run={({ key, value }) =>
        unwrap(
          api.POST('/api/actions/allele_pool:frequency', {
            body: {
              people_id: peopleId,
              locus: locus.locus,
              allele: key,
              frequency: value,
              hold,
            },
          })
        )
      }
    />
  )
}

function PoolCard({
  view,
  pool,
  blocked,
  hold,
}: {
  view: Lineage
  pool: Pool
  blocked: string | null
  hold: boolean
}) {
  const nodeId = view.node_id
  const stance = useGodAction({
    run: (value: GiftStance) =>
      unwrap(
        api.POST('/api/actions/allele_pool:stance', {
          body: { people_id: nodeId, stance: value, hold },
        })
      ),
  })
  const strike = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/allele_pool:remove', {
          body: { people_id: nodeId },
        })
      ),
  })
  const busy = why(blocked, stance.isPending, strike.isPending)
  const stances = Object.fromEntries(
    view.stances.map((item) => [item.key, item.label])
  )
  return (
    <MindCard
      title='Allele pool and the gift'
      icon={POOL_ICON}
      wide
      hint='How often each allele runs among the people. It drifts toward the blood of its living members; persecution, natural laws and the god move the gift.'
    >
      <div className='grid min-w-0 grid-cols-1 gap-3 @lg/mind:grid-cols-2'>
        <KpiTile
          label='Born gifted'
          value={`${pool.gifted_share}%`}
          icon={GIFT_ICON}
          tone='verdigris'
          meter={{ value: pool.gifted_share, max: SPAN, label: 'Gifted share' }}
        />
        <div className='flex min-w-0 flex-col gap-2'>
          <MindPicker
            label='How the people read the gift'
            value={pool.gift_stance}
            table={stances}
            blocked={busy}
            onPick={(value) => stance.mutate(value as GiftStance)}
          />
          <Badge variant='outline' className='w-fit'>
            <Text
              as='span'
              variant='caption'
              tone={
                STANCE_TONE[pool.gift_stance] === 'danger'
                  ? 'destructive'
                  : 'default'
              }
            >
              {pool.gift_stance_label}
            </Text>
          </Badge>
        </div>
      </div>
      {pool.cohort_shares.length > 0 && (
        <PagedList
          items={pool.cohort_shares}
          initial={12}
          noun={['entry', 'entries']}
          as='div'
          className='flex min-w-0 flex-wrap gap-2'
          itemKey={(cohort) => cohort.key}
        >
          {(cohort) => (
            <Badge key={cohort.key} variant='outline'>
              {`${cohort.key.replaceAll('_', ' ')}: ${cohort.label}% gifted`}
            </Badge>
          )}
        </PagedList>
      )}
      <ItemRow
        icon={GIFT_ICON}
        tone='verdigris'
        title='Set the gifted share'
        meta='Held, the world stops reckoning it from the blood'
        editLabel='gifted share'
        editor={
          <AdjustStats
            id={`gift-${nodeId}`}
            inline
            groups={[
              {
                title: 'Gift',
                fields: [
                  {
                    key: 'gifted_share',
                    label: 'Gifted share',
                    value: pool.gifted_share,
                    min: 0,
                    max: SPAN,
                  },
                ],
              },
            ]}
            run={({ value }) =>
              unwrap(
                api.POST('/api/actions/allele_pool:share', {
                  body: { people_id: nodeId, gifted_share: value, hold },
                })
              )
            }
          />
        }
      />
      <Paged items={pool.loci} initial={6} noun={['locus', 'loci']}>
        {(locus) => (
          <ItemRow
            key={locus.locus}
            icon={GROUP_ICON[locus.group] ?? LINEAGE_ICON}
            tone={locus.group === 'gift' ? 'verdigris' : 'gold'}
            title={locus.label}
            meta={locus.alleles
              .filter((allele) => (allele.frequency ?? 0) > 0)
              .map((allele) => `${allele.label} ${allele.frequency}%`)
              .join(', ')}
            editLabel={`${locus.label} frequencies`}
            editor={
              <FrequencyEditor peopleId={nodeId} locus={locus} hold={hold} />
            }
          />
        )}
      </Paged>
      <div className='flex justify-end'>
        <Button
          size='sm'
          variant='ghost'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => strike.mutate()}
        >
          <Eraser />
          Strike the pool
        </Button>
      </div>
    </MindCard>
  )
}

function LikenessCard({
  view,
  blocked,
  hold,
}: {
  view: Lineage
  blocked: string | null
  hold: boolean
}) {
  const nodeId = view.node_id
  const looks = view.loci.filter((locus) => locus.group === 'looks')
  const [locusKey, setLocusKey] = useState<string>(
    view.resemblance?.locus ?? looks[0]?.locus ?? 'hair_colour'
  )
  const locus = looks.find((item) => item.locus === locusKey)
  const [allele, setAllele] = useState<string>(
    view.resemblance?.allele ?? locus?.alleles[0]?.key ?? ''
  )
  const save = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/resemblance:set', {
          body: {
            house_id: nodeId,
            locus: locusKey as LocusKey,
            allele,
            share: view.resemblance?.share ?? 60,
            hold,
          },
        })
      ),
  })
  const strike = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/resemblance:remove', {
          body: { house_id: nodeId },
        })
      ),
  })
  const busy = why(blocked, save.isPending, strike.isPending)
  return (
    <MindCard
      title='Family likeness'
      icon={LIKENESS_ICON}
      hint='When most of a house share a look, the world comes to know the house by it.'
    >
      {view.resemblance ? (
        <ItemRow
          icon={LIKENESS_ICON}
          tone='gold'
          title={view.resemblance.allele_label}
          meta={`${view.resemblance.locus_label}, shared by ${view.resemblance.share}% since epoch ${view.resemblance.since_epoch}`}
          actions={
            <Button
              size='icon-sm'
              variant='ghost'
              aria-label='Strike the family likeness'
              disabled={busy !== null}
              disabledReason={busy ?? undefined}
              onClick={() => strike.mutate()}
            >
              <X />
            </Button>
          }
        />
      ) : (
        <Muted variant='caption'>No look marks this house yet.</Muted>
      )}
      <div className='grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-2'>
        <MindPicker
          label='Look'
          value={locusKey}
          table={Object.fromEntries(
            looks.map((item) => [item.locus, item.label])
          )}
          blocked={busy}
          onPick={(value) => {
            setLocusKey(value)
            setAllele(
              looks.find((item) => item.locus === value)?.alleles[0]?.key ?? ''
            )
          }}
        />
        <MindPicker
          label='Allele'
          value={allele}
          table={alleleTable(locus)}
          blocked={busy}
          onPick={setAllele}
        />
      </div>
      <div className='flex justify-end'>
        <Button
          size='sm'
          disabled={busy !== null || !allele}
          disabledReason={
            busy ?? (allele ? undefined : 'Choose an allele first.')
          }
          onClick={() => save.mutate()}
        >
          <Plus />
          Mark the house by this look
        </Button>
      </div>
    </MindCard>
  )
}

function WriteGenome({
  nodeId,
  blocked,
}: {
  nodeId: number
  blocked: string | null
}) {
  const found = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/genome:found', { body: { mortal_id: nodeId } })
      ),
  })
  const busy = why(blocked, found.isPending)
  return (
    <Button
      size='sm'
      disabled={busy !== null}
      disabledReason={busy ?? undefined}
      onClick={() => found.mutate()}
    >
      <Plus />
      Write it down now
    </Button>
  )
}

function DrawPool({
  nodeId,
  blocked,
}: {
  nodeId: number
  blocked: string | null
}) {
  const found = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/allele_pool:found', {
          body: { people_id: nodeId },
        })
      ),
  })
  const busy = why(blocked, found.isPending)
  return (
    <Button
      size='sm'
      disabled={busy !== null}
      disabledReason={busy ?? undefined}
      onClick={() => found.mutate()}
    >
      <Plus />
      Draw it now
    </Button>
  )
}

export function LineageSection({ nodeId }: { nodeId: number }) {
  const { reason } = useGodGate()
  const [hold, setHold] = useState(true)
  const query = useLineage(nodeId)
  const view = query.data
  if (query.isError)
    return (
      <Section id='section-blood' title='Blood and lineage' icon={LINEAGE_ICON}>
        <EmptyState
          icon={LINEAGE_ICON}
          title='This could not be read'
          description={query.error.message}
        />
      </Section>
    )
  if (!view) return null
  const blocked = reason()
  if (view.reason)
    return (
      <Section id='section-blood' title='Blood and lineage' icon={LINEAGE_ICON}>
        <EmptyState
          icon={LINEAGE_ICON}
          title='No blood to read'
          description={view.reason}
        />
      </Section>
    )
  return (
    <Section
      id='section-blood'
      title='Blood and lineage'
      description='Genomes for mortals, the allele pools and the magical gift for peoples, and the family likeness of houses.'
      icon={LINEAGE_ICON}
    >
      <div className='@container/mind flex min-w-0 flex-col gap-4'>
        <div className='grid min-w-0 grid-cols-1 gap-4 @xl/mind:grid-cols-2'>
          {view.can_hold_genome &&
            (view.genome ? (
              <>
                <GenomeCard
                  view={view}
                  genome={view.genome}
                  blocked={blocked}
                  hold={hold}
                />
                <GiftsCard genome={view.genome} />
                <BloodCard genome={view.genome} />
              </>
            ) : (
              <MindCard
                title='Blood and looks'
                icon={LINEAGE_ICON}
                hint='The world writes down every mortal blood each epoch.'
              >
                <Muted variant='caption'>
                  No genome is written for this mortal yet.
                </Muted>
                <WriteGenome nodeId={nodeId} blocked={blocked} />
              </MindCard>
            ))}
          {view.can_hold_pool &&
            (view.pool ? (
              <PoolCard
                view={view}
                pool={view.pool}
                blocked={blocked}
                hold={hold}
              />
            ) : (
              <MindCard
                title='Allele pool and the gift'
                icon={POOL_ICON}
                hint='The world draws a pool for every people each epoch.'
              >
                <Muted variant='caption'>
                  No allele pool is written for this people yet.
                </Muted>
                <DrawPool nodeId={nodeId} blocked={blocked} />
              </MindCard>
            ))}
          {view.can_hold_likeness && (
            <LikenessCard view={view} blocked={blocked} hold={hold} />
          )}
        </div>
        <ControlPanel
          title='Hold what you set'
          note='Alleles, frequencies, stances and shares you set are held against the world while the switch is on. Every change goes into the ledger and can be undone.'
          hold={hold}
          onHold={setHold}
        >
          {null}
        </ControlPanel>
      </div>
    </Section>
  )
}
