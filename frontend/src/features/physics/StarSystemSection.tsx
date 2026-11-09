import { useState } from 'react'
import { Crown, Orbit, Plus, Split, Sun } from 'lucide-react'
import { plural } from '@/lib/units'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { EmptyState, EntityLink, PagedList } from '@/components/domain'
import { Label } from '@/components/typography'
import { useCosmography } from '@/features/cosmography/api'
import {
  Chip,
  Facts,
  ForgeCard,
  RecordEditor,
  RecordRow,
} from '@/features/cosmography/parts'
import { STAR_TYPE_LABEL } from '@/features/cosmos/model/labels'
import { OrbitView } from './OrbitView'
import { physicsKeys, usePhysicsAction, useStarPhysics } from './api'
import { fixed } from './format'
import { SYSTEM_ROLES } from './labels'
import { QuerySection } from './parts'

type Move = { star: number; role: 'primary' | 'companion'; system: number }
type Edit = {
  system: number
  values?: Record<string, number | string | null>
  release?: string[]
}

export function StarSystemSection({ starId }: { starId: number }) {
  const query = useStarPhysics(starId)
  const heavens = useCosmography()
  const [joining, setJoining] = useState<string>('')
  const refresh = [physicsKeys.star(starId)]
  const move = usePhysicsAction(
    'star_system:move',
    ({ star, role, system }: Move) => ({
      star_id: star,
      system_id: system,
      role,
    }),
    'The star takes its place in the system',
    refresh
  )
  const edit = usePhysicsAction(
    'star_system:edit',
    (vars: Edit) => ({
      system_id: vars.system,
      values: vars.values ?? {},
      release: vars.release ?? [],
    }),
    'The system is reshaped',
    refresh
  )
  const create = usePhysicsAction(
    'star_system:create',
    (_: null) => ({ star_ids: [starId], name: '', separation: 0 }),
    'A new system is gathered',
    refresh
  )
  const breakUp = usePhysicsAction(
    'star_system:delete',
    (system: number) => ({ system_id: system }),
    'The system is broken up',
    refresh
  )
  const busy =
    move.isPending || edit.isPending || create.isPending || breakUp.isPending
      ? 'Working'
      : null
  return (
    <QuerySection
      id='section-star-system'
      title='Its system'
      description='The stars that share one centre, the band where their worlds are temperate and the orbits that circle them.'
      icon={Orbit}
      tone='info'
      query={query}
    >
      {(view) => {
        const system = view.system
        const members = new Set(system?.members.map((row) => row.star_id) ?? [])
        const others = (heavens.data?.stars ?? []).filter(
          (row) => !members.has(row.id)
        )
        const missing =
          system === null
            ? 'This star stands in no system yet'
            : joining === ''
              ? 'Choose a star first'
              : null
        return (
          <div className='flex min-w-0 flex-col gap-3'>
            {system === null ? (
              <EmptyState
                icon={Orbit}
                size='inline'
                title='It stands in no system'
                description='Gather it into a system of its own below.'
              />
            ) : (
              <>
                <Facts
                  items={[
                    ['System', system.name],
                    [
                      'Distance between its stars',
                      `${fixed(system.separation)} orbits`,
                    ],
                    [
                      'Temperate band of the system',
                      `${fixed(system.band_inner)} to ${fixed(system.band_outer)} orbits`,
                    ],
                  ]}
                />
                <PagedList
                  items={system.members}
                  initial={6}
                  noun={['star', 'stars']}
                  className='grid min-w-0 grid-cols-1 gap-2 lg:grid-cols-2'
                  itemKey={(row) => String(row.star_id)}
                >
                  {(row) => (
                    <RecordRow
                      icon={SYSTEM_ROLES[row.role].icon}
                      tone={SYSTEM_ROLES[row.role].tone}
                      title={
                        <EntityLink kind='star' id={String(row.star_id)}>
                          {row.name}
                        </EntityLink>
                      }
                      caption={`${STAR_TYPE_LABEL[row.star_type]} · ${fixed(row.mass)} suns · ${fixed(row.luminosity, 3)} light`}
                      aside={
                        row.role === 'primary' ? (
                          <Chip icon={Crown}>Primary</Chip>
                        ) : (
                          <Button
                            size='sm'
                            variant='ghost'
                            disabled={busy !== null}
                            disabledReason={busy ?? undefined}
                            onClick={() =>
                              move.mutate({
                                star: row.star_id,
                                role: 'primary',
                                system: system.id,
                              })
                            }
                          >
                            <Crown />
                            Make primary
                          </Button>
                        )
                      }
                    />
                  )}
                </PagedList>
                <RecordEditor
                  title='Name and spacing'
                  note='How far apart its stars stand sets how much light a world near one of them takes from the other.'
                  fields={[
                    { key: 'name', label: 'Name', kind: 'text' },
                    {
                      key: 'separation',
                      label: 'Distance between its stars (orbits)',
                      kind: 'decimal',
                      min: 0,
                    },
                  ]}
                  locked={system.locked}
                  busy={busy}
                  onSave={(values) =>
                    edit.mutate({ system: system.id, values })
                  }
                  onRelease={(release) =>
                    edit.mutate({ system: system.id, release })
                  }
                />
              </>
            )}
            <ForgeCard
              icon={Sun}
              tone='info'
              title='Bring a star into this system'
              note='A companion lights the worlds of its primary; worlds that circle both stars take the light of both.'
              columns={2}
              meta={<Chip icon={Orbit}>{plural(members.size, 'star')}</Chip>}
              action={
                <Button
                  size='sm'
                  disabled={busy !== null || missing !== null}
                  disabledReason={busy ?? missing ?? undefined}
                  onClick={() =>
                    system !== null &&
                    move.mutate({
                      star: Number(joining),
                      role: 'companion',
                      system: system.id,
                    })
                  }
                >
                  <Plus />
                  Bring it in
                </Button>
              }
            >
              <div className='flex min-w-0 flex-col gap-1'>
                <Label>Star</Label>
                <Select
                  value={joining}
                  onValueChange={setJoining}
                  disabled={others.length === 0}
                >
                  <SelectTrigger
                    aria-label='Star to bring in'
                    className='w-full'
                  >
                    <SelectValue placeholder='Choose a star' />
                  </SelectTrigger>
                  <SelectContent>
                    {others.map((row) => (
                      <SelectItem key={row.id} value={String(row.id)}>
                        {row.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </ForgeCard>
            <div className='flex min-w-0 flex-wrap gap-2'>
              <Button
                size='sm'
                variant='outline'
                disabled={busy !== null}
                disabledReason={busy ?? undefined}
                onClick={() => create.mutate(null)}
              >
                <Plus />
                Give it a system of its own
              </Button>
              <Button
                size='sm'
                variant='ghost'
                disabled={busy !== null || system === null}
                disabledReason={
                  busy ??
                  (system === null ? 'It stands in no system' : undefined)
                }
                onClick={() => system !== null && breakUp.mutate(system.id)}
              >
                <Split />
                Break the system up
              </Button>
            </div>
            <OrbitView view={view} />
          </div>
        )
      }}
    </QuerySection>
  )
}
