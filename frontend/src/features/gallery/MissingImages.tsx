import { useState } from 'react'
import { ImageOff } from 'lucide-react'
import { formatInteger } from '@/lib/format'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Skeleton } from '@/components/ui/skeleton'
import { EmptyState, EntityLink, Medallion, Section } from '@/components/domain'
import { Label, Text } from '@/components/typography'
import { READ_ONLY_REASON } from '@/features/entity/actions/gate'
import { useWorldState } from '@/features/entity/api/queries'
import { GenerateImageButton } from '@/features/images/GenerateImageButton'
import { ImageUploadZone } from '@/features/images/ImageUploadZone'
import { useMissingImages } from '@/features/images/api'
import { CATEGORY_ICON, FALLBACK_ICON, categoryLabel } from './galleryModel'

const STEP = 12
const PERCENT = 100

export function MissingImages({ type }: { type: string | null }) {
  const [limit, setLimit] = useState(STEP)
  const state = useWorldState()
  const missing = useMissingImages(type, limit)
  const readOnly = state.data?.read_only ? READ_ONLY_REASON : null
  const items = missing.data ?? []
  const top = Math.max(1, ...items.map((entity) => entity.importance ?? 0))
  return (
    <Section
      id='gallery-missing'
      title='Waiting for a likeness'
      description='The most important bare records first. Drop an image on a card, or let the worker paint one.'
      level={3}
    >
      {missing.isPending && <Skeleton className='h-textarea w-full' />}
      {missing.isError && (
        <Text tone='destructive'>{missing.error.message}</Text>
      )}
      {missing.isSuccess && items.length === 0 && (
        <EmptyState
          size='compact'
          icon={ImageOff}
          title='Nothing is missing'
          description='Every important record has a likeness.'
        />
      )}
      {items.length > 0 && (
        <ul className='grid min-w-0 grid-cols-1 gap-3 lg:grid-cols-2 2xl:grid-cols-3'>
          {items.map((entity, index) => {
            const Icon = CATEGORY_ICON[entity.entity_type] ?? FALLBACK_ICON
            const importance = entity.importance ?? 0
            return (
              <li
                key={entity.id}
                className='flex min-w-0 flex-col gap-3 rounded-xl border bg-card p-3'
              >
                <div className='flex min-w-0 items-start gap-3'>
                  <Medallion
                    icon={Icon}
                    tone={index < 3 ? 'gold' : 'muted'}
                    size='sm'
                  />
                  <div className='flex min-w-0 flex-1 flex-col gap-1'>
                    <EntityLink kind='entity' id={String(entity.id)}>
                      {entity.name}
                    </EntityLink>
                    <div className='flex min-w-0 flex-wrap gap-1.5'>
                      <Badge size='sm' variant='outline'>
                        {categoryLabel(entity.entity_type)}
                      </Badge>
                      <Badge size='sm' variant='outline'>
                        {`Epoch ${entity.birth_epoch}`}
                      </Badge>
                    </div>
                  </div>
                  <Badge
                    size='sm'
                    variant={index < 3 ? 'default' : 'secondary'}
                  >
                    {`#${index + 1}`}
                  </Badge>
                </div>
                {entity.importance !== null && (
                  <div className='flex min-w-0 flex-col gap-1'>
                    <div className='flex min-w-0 items-center justify-between gap-2'>
                      <Label>Importance</Label>
                      <Text as='span' weight='medium'>
                        {formatInteger(importance)}
                      </Text>
                    </div>
                    <Progress
                      size='sm'
                      value={(importance / top) * PERCENT}
                      aria-label={`Importance of ${entity.name}`}
                    />
                  </div>
                )}
                <GenerateImageButton
                  nodeId={entity.id}
                  hasImages={false}
                  readOnlyReason={readOnly}
                />
                <ImageUploadZone
                  nodeId={entity.id}
                  label={`Upload for ${entity.name}`}
                  acceptPaste={false}
                  disabledReason={readOnly}
                />
              </li>
            )
          })}
        </ul>
      )}
      {items.length >= limit && (
        <Button
          variant='outline'
          className='self-start'
          disabled={missing.isFetching}
          disabledReason='Loading.'
          onClick={() => setLimit((value) => value + STEP)}
        >
          {`Show ${STEP} more`}
        </Button>
      )}
    </Section>
  )
}
