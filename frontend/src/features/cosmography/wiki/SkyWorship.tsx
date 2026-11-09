import { useState } from 'react'
import { AlertTriangle, HandHeart, Sparkles, UserMinus } from 'lucide-react'
import { plural } from '@/lib/units'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import { EmptyState, EntityLink, PagedList, Section } from '@/components/domain'
import { ENTITY_TYPE_ICON } from '@/components/domain/domainIcons'
import { Label } from '@/components/typography'
import { capitalized } from '@/features/graph/families'
import {
  type SkyWorshipView,
  cosmographyKeys,
  useCosmographyAction,
  useSkyWorship,
} from '../api'
import { Chip, ForgeCard, Meter, RecordPick, RecordRow } from '../parts'

type Change = { communityId: number; worships: boolean }

const SKY_NOUN: Record<SkyWorshipView['sky'], string> = {
  star: 'star',
  galaxy: 'galaxy',
  dimension: 'dimension',
}

const SKY_NOTE: Record<SkyWorshipView['sky'], string> = {
  star: 'Peoples under it gain or lose piety as it brightens, dims or flares, and its patron draws essence from them.',
  galaxy:
    'Peoples inside it gain piety while it forms stars and while its cluster grows.',
  dimension:
    'Peoples gain piety while it holds steady, and each of them thins its veil a little.',
}

export function SkyWorship({ nodeId }: { nodeId: number }) {
  const worship = useSkyWorship(nodeId)
  const [chosen, setChosen] = useState<number | null>(null)
  const change = useCosmographyAction<Change>(
    'heavens:worship',
    ({ communityId, worships }) => ({
      community_id: communityId,
      sky: worship.data?.sky ?? 'star',
      worships,
      dimension_id: worship.data?.sky === 'dimension' ? nodeId : null,
    }),
    'The worship of the heavens is changed',
    [cosmographyKeys.worship(nodeId), cosmographyKeys.wiki(nodeId)]
  )
  if (worship.isPending)
    return (
      <Section
        id='section-sky-worship'
        title='Worshipped by'
        icon={HandHeart}
        tone='gold'
      >
        <Skeleton className='h-control-lg w-full' />
      </Section>
    )
  if (worship.isError)
    return (
      <Section
        id='section-sky-worship'
        title='Worshipped by'
        icon={HandHeart}
        tone='gold'
      >
        <EmptyState
          icon={AlertTriangle}
          size='inline'
          title='Its worshippers could not be read'
          description={worship.error.message}
        />
      </Section>
    )
  const view = worship.data
  const noun = SKY_NOUN[view.sky]
  const busy = change.isPending ? 'Working' : null
  const pickable = view.sky === 'dimension' ? null : view.candidates
  const missing =
    pickable !== null && pickable.length === 0
      ? `Every people under this ${noun} already worships it, or none lives under it`
      : chosen === null
        ? 'Choose a people first'
        : null
  return (
    <Section
      id='section-sky-worship'
      title='Worshipped by'
      description={SKY_NOTE[view.sky]}
      icon={HandHeart}
      tone='gold'
    >
      <div className='flex min-w-0 flex-col gap-3'>
        {view.worshippers.length === 0 ? (
          <EmptyState
            icon={HandHeart}
            size='inline'
            title={`No people worships this ${noun}`}
            description='Cults rise by themselves when it stirs; you can also turn a people to it below.'
          />
        ) : (
          <PagedList
            items={view.worshippers}
            initial={6}
            noun={['people', 'peoples']}
            className='grid min-w-0 grid-cols-1 gap-2 lg:grid-cols-2'
            itemKey={(row) => String(row.id)}
          >
            {(row) => (
              <RecordRow
                icon={ENTITY_TYPE_ICON[row.entity_type]}
                tone='gold'
                title={
                  <EntityLink kind='entity' id={String(row.id)}>
                    {row.name}
                  </EntityLink>
                }
                caption={capitalized(row.entity_type.replaceAll('_', ' '))}
                aside={
                  <Button
                    size='sm'
                    variant='ghost'
                    disabled={busy !== null}
                    disabledReason={busy ?? undefined}
                    onClick={() =>
                      change.mutate({ communityId: row.id, worships: false })
                    }
                  >
                    <UserMinus />
                    Turn away
                  </Button>
                }
              >
                {row.piety !== null && (
                  <Meter label='Piety' value={row.piety} tone='success' />
                )}
              </RecordRow>
            )}
          </PagedList>
        )}
        <ForgeCard
          icon={HandHeart}
          tone='gold'
          title={`Turn a people to this ${noun}`}
          note={
            view.sky === 'dimension'
              ? 'Any people may come to worship a dimension.'
              : `Only peoples who live under this ${noun} can worship it.`
          }
          columns={2}
          meta={
            <Chip icon={Sparkles}>
              {plural(view.worshippers.length, 'worshipper')}
            </Chip>
          }
          action={
            <Button
              size='sm'
              disabled={busy !== null || missing !== null}
              disabledReason={busy ?? missing ?? undefined}
              onClick={() => {
                if (chosen === null) return
                change.mutate({ communityId: chosen, worships: true })
                setChosen(null)
              }}
            >
              <HandHeart />
              Make them worship it
            </Button>
          }
        >
          {pickable === null ? (
            <RecordPick
              label='People'
              types={['people', 'settlement']}
              value={chosen}
              onChange={setChosen}
            />
          ) : (
            <div className='flex min-w-0 flex-col gap-1'>
              <Label>People</Label>
              <Select
                value={chosen !== null ? String(chosen) : ''}
                onValueChange={(next) => setChosen(Number(next))}
                disabled={pickable.length === 0}
              >
                <SelectTrigger aria-label='People to turn' className='w-full'>
                  <SelectValue placeholder='Choose a people' />
                </SelectTrigger>
                <SelectContent>
                  {pickable.map((row) => (
                    <SelectItem key={row.id} value={String(row.id)}>
                      {row.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}
        </ForgeCard>
      </div>
    </Section>
  )
}
