import { useState } from 'react'
import { Eraser, Skull } from 'lucide-react'
import { type ActionBody } from '@/api/actions'
import { Button } from '@/components/ui/button'
import { Medallion, Section } from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { MindPicker } from '@/features/entity/mind/parts'
import {
  type CosmographyCatalog,
  catalogLabel,
  catalogTable,
  useCosmographyAction,
} from './api'

export function ApocalypseVariantPanel({
  current,
  likely,
  catalog,
}: {
  current: string | null
  likely: string
  catalog: CosmographyCatalog | undefined
}) {
  const [choice, setChoice] = useState('')
  const set = useCosmographyAction(
    'apocalypse:variant',
    (variant: string | null) => ({
      variant: variant as ActionBody<'apocalypse:variant'>['variant'],
    }),
    'The shape of the end is set'
  )
  const busy = set.isPending ? 'Setting the shape of the end' : null
  const description = catalog?.apocalypse_variants.find(
    (row) => row.value === (current ?? likely)
  )?.description
  return (
    <Section
      id='panel-apocalypse'
      title='The shape of the end'
      description='When the doom clock runs out, the end takes the shape of the cause that drove it most, unless you choose it.'
      icon={Skull}
      tone='danger'
      surface='card'
    >
      <div
        data-surface='ApocalypseVariantPanel'
        className='flex min-w-0 flex-col gap-3'
      >
        <div className='flex min-w-0 items-center gap-3'>
          <Medallion icon={Skull} tone='danger' />
          <div className='flex min-w-0 flex-1 flex-col'>
            <Text weight='semibold'>
              {catalogLabel(catalog?.apocalypse_variants, current ?? likely)}
            </Text>
            <Muted variant='caption'>
              {current
                ? 'Chosen by you'
                : 'What the causes of the doom point to now'}
              {description ? ` · ${description}` : ''}
            </Muted>
          </div>
        </div>
        <div className='flex min-w-0 flex-wrap items-end gap-2'>
          <div className='min-w-0 flex-1 basis-60'>
            <MindPicker
              label='Choose the end'
              value={choice}
              table={catalogTable(catalog?.apocalypse_variants)}
              blocked={busy}
              onPick={setChoice}
            />
          </div>
          <Button
            size='sm'
            disabled={busy !== null || choice === ''}
            disabledReason={
              busy ?? (choice === '' ? 'Choose a shape first' : undefined)
            }
            onClick={() => set.mutate(choice)}
          >
            <Skull />
            Fix this end
          </Button>
          <Button
            size='sm'
            variant='outline'
            disabled={busy !== null || current === null}
            disabledReason={
              busy ??
              (current === null
                ? 'The end already follows its causes'
                : undefined)
            }
            onClick={() => set.mutate(null)}
          >
            <Eraser />
            Let the causes decide
          </Button>
        </div>
      </div>
    </Section>
  )
}
