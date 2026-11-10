import { Dices, Hourglass, Sprout } from 'lucide-react'
import { formatInteger } from '@/lib/format'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { Skeleton } from '@/components/ui/skeleton'
import {
  CopyButton,
  Medallion,
  MiniStat,
  PagedList,
  Section,
} from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { useEngineSeed } from './api'
import { phaseLabel } from './phaseModel'

const STREAM_PAGE = 24

export function SeedPanel() {
  const seed = useEngineSeed()
  return (
    <Section
      title='Determinism'
      description='Every tick draws its chance from the world seed and the epoch, one stream per step. The same world and seed always replay the same epoch.'
      surface='card'
      level={3}
      icon={Dices}
      tone='info'
    >
      {seed.isPending && <Skeleton className='h-24 w-full' />}
      {seed.isError && <Text tone='destructive'>{seed.error.message}</Text>}
      {seed.data && (
        <div className='flex min-w-0 flex-col gap-3'>
          <div className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-2'>
            <div className='flex min-w-0 items-center gap-2.5 rounded-lg border bg-background p-2'>
              <Medallion icon={Sprout} tone='gold' size='sm' />
              <div className='flex min-w-0 flex-1 flex-col'>
                <Text as='span' weight='medium' className='font-mono break-all'>
                  {String(seed.data.world_seed)}
                </Text>
                <Label>World seed</Label>
              </div>
              <CopyButton
                text={String(seed.data.world_seed)}
                label='Copy the world seed'
              />
            </div>
            <MiniStat
              icon={Hourglass}
              label='Epoch'
              value={formatInteger(seed.data.epoch)}
              tone='verdigris'
            />
          </div>
          <Muted variant='caption'>{`Stream: ${seed.data.stream_format}`}</Muted>
          <Collapsible className='flex min-w-0 flex-col gap-2'>
            <CollapsibleTrigger asChild>
              <Button variant='ghost' size='sm' className='self-start'>
                <Dices />
                {`${formatInteger(seed.data.phase_streams.length)} step streams`}
              </Button>
            </CollapsibleTrigger>
            <CollapsibleContent>
              <PagedList
                items={seed.data.phase_streams}
                initial={STREAM_PAGE}
                noun={['stream', 'streams']}
                as='div'
                className='flex min-w-0 flex-wrap items-center gap-1'
                itemKey={(name) => name}
              >
                {(name) => (
                  <Badge size='sm' variant='outline' title={name}>
                    {phaseLabel(name)}
                  </Badge>
                )}
              </PagedList>
            </CollapsibleContent>
          </Collapsible>
        </div>
      )}
    </Section>
  )
}
