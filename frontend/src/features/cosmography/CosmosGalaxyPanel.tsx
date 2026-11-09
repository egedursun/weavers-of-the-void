import { useState } from 'react'
import { Link } from '@tanstack/react-router'
import { Eye, Globe2, Layers, Orbit, Plus, Sparkles, Star } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Progress } from '@/components/ui/progress'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { EmptyState, MiniStat, Section } from '@/components/domain'
import { useDrawerStack } from '@/components/layout/drawer/useDrawerStack'
import { Label, Muted, Stat, Text } from '@/components/typography'
import { type Cosmography, type CosmographyCatalog, catalogLabel } from './api'
import { BETWEEN_GALAXIES, galaxyName } from './cosmosGalaxy'
import { CreateGalaxyStudio } from './create/CreateStudio'
import { GALAXY_AGES, NUCLEI, ZONES } from './labels'
import { ladderOf } from './ladder'
import { Chip } from './parts'
import { GalaxyThumb } from './visual/GalaxyThumb'

const PERCENT = 100

export function GalaxySwitcher({
  heavens,
  catalog,
  value,
  onChange,
}: {
  heavens: Cosmography
  catalog: CosmographyCatalog
  value: number | undefined
  onChange: (galaxyId: number) => void
}) {
  const outside = heavens.placements.some((row) => row.galaxy_id === null)
  return (
    <Select
      value={value !== undefined ? String(value) : undefined}
      onValueChange={(next) => onChange(Number(next))}
    >
      <SelectTrigger aria-label='Galaxy shown' className='min-w-0'>
        <SelectValue placeholder='Choose a galaxy' />
      </SelectTrigger>
      <SelectContent>
        {heavens.galaxies.map((galaxy) => (
          <SelectItem key={galaxy.id} value={String(galaxy.id)}>
            <span className='flex min-w-0 items-center gap-2'>
              <GalaxyThumb
                galaxy={galaxy}
                shape={catalog.shape}
                label={galaxy.name}
                points={600}
                className='size-icon-xl shrink-0 rounded-sm'
              />
              {galaxy.name}
            </span>
          </SelectItem>
        ))}
        {outside && (
          <SelectItem value={String(BETWEEN_GALAXIES)}>
            Between the galaxies
          </SelectItem>
        )}
      </SelectContent>
    </Select>
  )
}

export function CosmosGalaxyPanel({
  heavens,
  catalog,
  galaxyId,
  leaving,
  onChange,
}: {
  heavens: Cosmography
  catalog: CosmographyCatalog
  galaxyId: number | undefined
  leaving: number
  onChange: (galaxyId: number) => void
}) {
  const drawers = useDrawerStack()
  const [creating, setCreating] = useState(false)
  const ladder = ladderOf(heavens)
  const galaxy = heavens.galaxies.find((row) => row.id === galaxyId)
  const stars = heavens.stars.filter(
    (row) => (row.galaxy_id ?? BETWEEN_GALAXIES) === galaxyId
  )
  const worlds = heavens.placements.filter(
    (row) => (row.galaxy_id ?? BETWEEN_GALAXIES) === galaxyId
  )
  const zones = Object.entries(
    stars.reduce<Record<string, number>>(
      (counts, star) => ({
        ...counts,
        [star.galactic_zone]: (counts[star.galactic_zone] ?? 0) + 1,
      }),
      {}
    )
  )
  return (
    <div id='section-cosmos-galaxy' className='flex min-w-0 flex-col gap-4'>
      <div className='flex min-w-0 flex-col gap-1'>
        <Label>Galaxy shown in the Cosmos</Label>
        <GalaxySwitcher
          heavens={heavens}
          catalog={catalog}
          value={galaxyId}
          onChange={onChange}
        />
      </div>
      {galaxy ? (
        <div className='flex min-w-0 flex-col gap-3 rounded-xl border bg-card p-3'>
          <GalaxyThumb
            galaxy={galaxy}
            shape={catalog.shape}
            label={galaxy.name}
            stars={stars.map((star) => ({ id: star.id, x: star.x, y: star.y }))}
            className='aspect-video w-full'
          />
          <div className='flex min-w-0 flex-col gap-1'>
            <Label variant='overline'>{`Galaxy · ${catalogLabel(catalog.galaxy_types, galaxy.galaxy_type)}`}</Label>
            <Text weight='semibold'>{galaxy.name}</Text>
            <div className='flex min-w-0 flex-wrap gap-1'>
              <Chip icon={NUCLEI[galaxy.nucleus].icon}>
                {NUCLEI[galaxy.nucleus].label}
              </Chip>
              <Chip>{GALAXY_AGES[galaxy.age_stage]}</Chip>
              {galaxy.cluster_id !== null && (
                <Chip icon={Layers}>
                  {ladder.names.get(galaxy.cluster_id) ?? 'Its cluster'}
                </Chip>
              )}
            </div>
          </div>
          <div className='flex max-w-sm min-w-0 flex-col gap-1.5'>
            <div className='flex min-w-0 items-center justify-between gap-2'>
              <Label>Star formation</Label>
              <Stat value={galaxy.star_formation} unit={`/ ${PERCENT}`} />
            </div>
            <Progress
              size='sm'
              value={galaxy.star_formation}
              tone='success'
              aria-label='Star formation'
            />
          </div>
          <div className='grid min-w-0 grid-cols-2 gap-2'>
            <MiniStat
              icon={Star}
              tone='gold'
              label='Stars'
              value={stars.length}
            />
            <MiniStat
              icon={Globe2}
              tone='info'
              label='Worlds'
              value={worlds.length}
            />
            <MiniStat
              icon={Sparkles}
              tone='verdigris'
              label='Structures'
              value={
                heavens.structures.filter(
                  (row) =>
                    row.galaxy_id === galaxy.id && row.ended_epoch === null
                ).length
              }
            />
            <MiniStat
              icon={Orbit}
              tone='warning'
              label='Routes leaving'
              value={leaving}
            />
          </div>
          {zones.length > 0 && (
            <div className='flex min-w-0 flex-wrap gap-1'>
              {zones.map(([zone, count]) => {
                const named = ZONES[zone as keyof typeof ZONES]
                return (
                  <Chip
                    key={zone}
                    icon={named.icon}
                  >{`${named.label}: ${count}`}</Chip>
                )
              })}
            </div>
          )}
          <div className='flex min-w-0 flex-wrap gap-2'>
            <Button
              size='sm'
              onClick={() =>
                drawers.open({ kind: 'galaxy', id: String(galaxy.id) })
              }
            >
              <Eye />
              Shape this galaxy
            </Button>
            <Button size='sm' variant='outline' asChild>
              <Link to='/heavens' search={{ layer: 'galaxy', node: galaxy.id }}>
                <Layers />
                See it in the Heavens
              </Link>
            </Button>
          </div>
        </div>
      ) : (
        <EmptyState
          icon={Orbit}
          size='compact'
          title={galaxyName(heavens.galaxies, galaxyId)}
          description='These worlds drift outside every galaxy; their dimension alone shapes them.'
        />
      )}
      <Section title='Other galaxies' icon={Orbit} tone='gold'>
        <ul className='grid min-w-0 grid-cols-2 gap-2'>
          {heavens.galaxies
            .filter((row) => row.id !== galaxyId)
            .map((row) => (
              <li key={row.id}>
                <Button
                  variant='ghost'
                  size='card'
                  onClick={() => onChange(row.id)}
                >
                  <GalaxyThumb
                    galaxy={row}
                    shape={catalog.shape}
                    label={row.name}
                    points={1200}
                    className='aspect-video w-full'
                  />
                  <Text as='span' variant='caption' truncate>
                    {row.name}
                  </Text>
                </Button>
              </li>
            ))}
        </ul>
        <Button variant='outline' onClick={() => setCreating(true)}>
          <Plus />
          Set a new galaxy turning
        </Button>
        {heavens.galaxies.length <= 1 && (
          <Muted variant='caption'>
            This is the only galaxy so far; a new one appears here and in the
            Heavens.
          </Muted>
        )}
      </Section>
      <Dialog open={creating} onOpenChange={setCreating}>
        <DialogContent className='max-w-4xl'>
          <DialogHeader>
            <DialogTitle>A new galaxy</DialogTitle>
            <DialogDescription>
              Choose its form, name it and place it in a cluster or a dimension.
            </DialogDescription>
          </DialogHeader>
          <CreateGalaxyStudio ladder={ladder} catalog={catalog} />
        </DialogContent>
      </Dialog>
    </div>
  )
}
