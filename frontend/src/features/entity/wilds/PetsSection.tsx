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
import { Label, Muted } from '@/components/typography'
import { EntityPicker } from '@/features/cosmos/EntityPicker'
import { useGodGate } from '@/features/pantheon/gate'
import { busyOf } from '../lore/model'
import { MindPicker } from '../mind/parts'
import { petKeys, useWildAction } from './api'
import { SIZE, named } from './labels'
import { Group, Name } from './parts'

const BEASTS = ['beast'] as const

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
  const give = useWildAction('pet:give', (species: number) => ({
    owner_id: mortalId,
    species_id: species,
  }))
  const free = useWildAction('pet:set', (beast: number) => ({
    beast_id: beast,
    owner_id: null,
  }))
  const keep = useWildAction('pet:set', (picked: number) => ({
    beast_id: picked,
    owner_id: mortalId,
  }))
  const [kind, setKind] = useState('')
  const [beast, setBeast] = useState<number | null>(null)
  const { reason } = useGodGate()
  const busy = busyOf(
    readOnlyReason ?? reason(),
    give.isPending || free.isPending || keep.isPending
  )
  const data = view.data
  const kindTable = data
    ? Object.fromEntries([
        ...data.kinds.map((item) => [
          String(item.id),
          `${item.name} (their people keep it)`,
        ]),
        ...data.other_kinds.map((item) => [String(item.id), item.name]),
      ])
    : {}
  const kindCount = Object.keys(kindTable).length
  const kept = (data?.pets.length ?? 0) > 0
  const kindProblem = kept
    ? 'They already keep a pet; set it free first'
    : kind === ''
      ? 'Choose a kind'
      : null
  const beastProblem = kept
    ? 'They already keep a pet; set it free first'
    : beast === null
      ? 'Choose a beast'
      : null
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
                    className='flex min-w-0 flex-col gap-2 rounded-md border surface-well border-gild/20 bg-muted/60 p-3'
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
                          act={free}
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
          <Group title='Give them a companion' icon={HandHeart}>
            {data.pets.length > 0 && (
              <Muted variant='caption'>
                They already keep a pet; set it free first to give another.
              </Muted>
            )}
            <div className='grid min-w-0 grid-cols-1 gap-3 md:grid-cols-2'>
              <div className='flex min-w-0 flex-col gap-2'>
                {kindCount === 0 ? (
                  <Muted variant='caption'>
                    No animal kind lives in the cosmos yet; make one in the
                    Wilds and you can give it.
                  </Muted>
                ) : (
                  <MindPicker
                    label='A new pet of any animal kind'
                    value={kind}
                    table={kindTable}
                    blocked={busy}
                    placeholder='Choose a kind'
                    onPick={setKind}
                  />
                )}
                <Button
                  act={give}
                  size='sm'
                  variant='outline'
                  className='self-start'
                  disabled={(busy ?? kindProblem) !== null}
                  disabledReason={busy ?? kindProblem ?? undefined}
                  onClick={() => give.mutate(Number(kind))}
                >
                  <HandHeart />
                  Give the pet
                </Button>
              </div>
              <div className='flex min-w-0 flex-col gap-2'>
                <Label>A beast that already lives</Label>
                <EntityPicker
                  types={BEASTS}
                  value={beast}
                  onChange={setBeast}
                  placeholder='Choose a beast…'
                />
                <Button
                  act={keep}
                  size='sm'
                  variant='outline'
                  className='self-start'
                  disabled={(busy ?? beastProblem) !== null}
                  disabledReason={busy ?? beastProblem ?? undefined}
                  onClick={() => beast !== null && keep.mutate(beast)}
                >
                  <PawPrint />
                  Make it their pet
                </Button>
              </div>
            </div>
            {data.kinds.length === 0 && kindCount > 0 && (
              <Muted variant='caption'>
                Their people keep no small tame kind of their own, so they will
                not take a pet by themselves; any kind you give is theirs all
                the same.
              </Muted>
            )}
          </Group>
        </div>
      )}
    </Section>
  )
}
