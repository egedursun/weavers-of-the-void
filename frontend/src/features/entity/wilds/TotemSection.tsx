import { useState } from 'react'
import { PawPrint, Sparkles, X } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  EmptyState,
  Medallion,
  Section,
  LoadingBlock,
} from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { EntityPicker } from '@/features/cosmos/EntityPicker'
import { useGodGate } from '@/features/pantheon/gate'
import { busyOf } from '../lore/model'
import { useTotem, useWildAction } from './api'
import { Name } from './parts'

export function TotemSection({
  peopleId,
  readOnlyReason,
}: {
  peopleId: number
  readOnlyReason?: string | null
}) {
  const view = useTotem(peopleId)
  const { reason } = useGodGate()
  const [species, setSpecies] = useState<number | null>(null)
  const set = useWildAction(
    'people:totem',
    (chosen: number | null) => ({ people_id: peopleId, species_id: chosen }),
    () => setSpecies(null)
  )
  const busy = busyOf(readOnlyReason ?? reason(), set.isPending)
  const totem = view.data?.species ?? null
  return (
    <Section
      id='section-totem'
      title='Totem'
      description='The kind this people holds as its emblem. They will not hunt it, it is holy in their lands, and a son of the Hunt they pray to may wear its head.'
      icon={PawPrint}
      tone='success'
    >
      <div data-surface='TotemCard' className='flex min-w-0 flex-col gap-3'>
        {view.isPending ? (
          <LoadingBlock label='Reading the people’s emblem' />
        ) : totem ? (
          <div className='flex min-w-0 flex-wrap items-center gap-3 rounded-md border surface-framed border-gild/70 bg-card p-3'>
            <Medallion icon={PawPrint} tone='success' />
            <div className='flex min-w-0 flex-1 flex-col gap-1'>
              <Text weight='semibold'>
                <Name item={totem} />
              </Text>
              <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
                <Badge size='sm' variant='success'>
                  <Sparkles />
                  Never hunted by them
                </Badge>
                {view.data?.tradition && (
                  <span className='flex min-w-0 items-center gap-1.5'>
                    <Muted as='span' variant='caption'>
                      Kept by
                    </Muted>
                    <Name item={view.data.tradition} />
                  </span>
                )}
              </div>
            </div>
            <Button
              size='sm'
              variant='outline'
              disabled={busy !== null}
              disabledReason={busy ?? undefined}
              onClick={() => set.mutate(null)}
            >
              <X />
              Set it aside
            </Button>
          </div>
        ) : (
          <EmptyState
            icon={PawPrint}
            title='No totem'
            description='The people may take the great kind of their land as their emblem in time, or you may give them one.'
          />
        )}
        <div className='flex min-w-0 flex-wrap items-end gap-2'>
          <div className='flex min-w-0 flex-1 basis-60 flex-col gap-1'>
            <Label>
              {totem ? 'Give them another totem' : 'Give them a totem'}
            </Label>
            <EntityPicker
              types={['species']}
              value={species}
              onChange={setSpecies}
              placeholder='Choose a kind…'
            />
          </div>
          <Button
            size='sm'
            disabled={busy !== null || species === null}
            disabledReason={
              busy ?? (species === null ? 'Choose a kind' : undefined)
            }
            onClick={() => species !== null && set.mutate(species)}
          >
            <PawPrint />
            Make it their totem
          </Button>
        </div>
      </div>
    </Section>
  )
}
