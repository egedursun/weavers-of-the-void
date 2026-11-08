import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  Crosshair,
  HandHeart,
  Hourglass,
  PawPrint,
  TriangleAlert,
  Unlock,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  EmptyState,
  LoadingBlock,
  Medallion,
  Paged,
  Section,
  StatBar,
} from '@/components/domain'
import { Muted } from '@/components/typography'
import { useGodGate } from '@/features/pantheon/gate'
import { busyOf } from '../lore/model'
import { MindPicker } from '../mind/parts'
import { petKeys, useWildAction } from './api'
import { SIZE, named } from './labels'
import { Name } from './parts'

function usePets(mortalId: number) {
  return useQuery({
    queryKey: petKeys.mortal(mortalId),
    queryFn: () =>
      unwrap(
        api.GET('/api/entities/{entity_id}/pets', {
          params: { path: { entity_id: mortalId } },
        })
      ),
  })
}

export function PetsSection({
  mortalId,
  readOnlyReason,
}: {
  mortalId: number
  readOnlyReason?: string | null
}) {
  const view = usePets(mortalId)
  const give = useWildAction<number>('pet:give', (species) => ({
    owner_id: mortalId,
    species_id: species,
  }))
  const free = useWildAction<number>('pet:set', (beast) => ({
    beast_id: beast,
    owner_id: null,
  }))
  const [kind, setKind] = useState('')
  const { reason } = useGodGate()
  const busy = busyOf(
    readOnlyReason ?? reason(),
    give.isPending || free.isPending
  )
  const data = view.data
  return (
    <Section
      id='section-pets'
      title='Companions'
      description='The animals this mortal keeps at their side. Only mortals keep pets: peoples, places, gods and worlds have herds, lairs or worshippers instead.'
      icon={HandHeart}
      tone='success'
    >
      {view.isPending && <LoadingBlock label='Reading their companions' />}
      {view.isError && (
        <EmptyState
          icon={TriangleAlert}
          title='Their companions could not be read'
          description={view.error.message}
        />
      )}
      {data && (
        <div data-surface='MortalPets' className='flex min-w-0 flex-col gap-3'>
          {data.pets.length === 0 ? (
            <EmptyState
              icon={PawPrint}
              title='No companion yet'
              description='A mortal takes a pet from the small tame kinds their people keep; you can give them one.'
            />
          ) : (
            <ul className='flex min-w-0 flex-col gap-2'>
              <Paged items={data.pets} as='li'>
                {(row) => (
                  <li
                    key={row.pet?.id}
                    className='flex min-w-0 flex-col gap-2 rounded-lg border bg-muted/30 p-3'
                  >
                    <div className='flex min-w-0 items-center gap-2'>
                      <Medallion icon={PawPrint} tone='success' size='sm' />
                      <div className='flex min-w-0 flex-1 flex-col gap-1'>
                        <Name item={row.pet} />
                        <div className='flex min-w-0 flex-wrap gap-1'>
                          <Badge size='sm' variant='secondary'>
                            {named(SIZE, row.size_class).label}
                          </Badge>
                          {row.species && (
                            <Badge size='sm' variant='outline'>
                              {row.species.name}
                            </Badge>
                          )}
                          {row.hunts && (
                            <Badge size='sm' variant='warning'>
                              <Crosshair aria-hidden='true' />
                              Hunts at their side
                            </Badge>
                          )}
                        </div>
                      </div>
                      {row.pet && (
                        <Button
                          size='sm'
                          variant='ghost'
                          disabled={busy !== null}
                          disabledReason={busy ?? undefined}
                          onClick={() => row.pet && free.mutate(row.pet.id)}
                        >
                          <Unlock />
                          Set it free
                        </Button>
                      )}
                    </div>
                    <StatBar
                      label='Years of its life'
                      value={row.age}
                      max={Math.max(1, row.lifespan)}
                      icon={Hourglass}
                      tone='success'
                    />
                    <Muted variant='caption'>
                      {`Kept since epoch ${row.since_epoch}`}
                    </Muted>
                  </li>
                )}
              </Paged>
            </ul>
          )}
          {data.kinds.length > 0 ? (
            <div className='flex min-w-0 flex-wrap items-end gap-2'>
              <MindPicker
                label='Give them a pet of a kind their people keep'
                value={kind}
                table={Object.fromEntries(
                  data.kinds.map((item) => [String(item.id), item.name])
                )}
                blocked={busy}
                placeholder='Choose a kind'
                onPick={setKind}
              />
              <Button
                size='sm'
                variant='outline'
                disabled={busy !== null || kind === '' || data.pets.length > 0}
                disabledReason={
                  busy ??
                  (data.pets.length > 0
                    ? 'They already keep a pet; set it free first'
                    : kind === ''
                      ? 'Choose a kind'
                      : undefined)
                }
                onClick={() => give.mutate(Number(kind))}
              >
                <HandHeart />
                Give the pet
              </Button>
            </div>
          ) : (
            <Muted variant='caption'>
              Their people keep no small tame kind to take a pet from; a herd of
              a companion, guard, war or pest-hunting kind would give them one.
            </Muted>
          )}
        </div>
      )}
    </Section>
  )
}
