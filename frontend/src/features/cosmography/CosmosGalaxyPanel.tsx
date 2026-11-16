import { useState } from 'react'
import { Link } from '@tanstack/react-router'
import {
  ChevronDown,
  ChevronUp,
  Eye,
  Globe2,
  Layers,
  Orbit,
  Plus,
  Sparkles,
  Star,
} from 'lucide-react'
import { plural } from '@/lib/units'
import { Button } from '@/components/ui/button'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { type ControlSize } from '@/components/ui/control-size'
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
import { Medallion, MiniStat } from '@/components/domain'
import { useDrawerStack } from '@/components/layout/drawer/useDrawerStack'
import { Label, Muted, Stat } from '@/components/typography'
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
  stretch = false,
  size = 'default',
}: {
  heavens: Cosmography
  catalog: CosmographyCatalog
  value: number | undefined
  onChange: (galaxyId: number) => void
  stretch?: boolean
  size?: ControlSize
}) {
  const outside = heavens.placements.some((row) => row.galaxy_id === null)
  return (
    <Select
      value={value !== undefined ? String(value) : undefined}
      onValueChange={(next) => onChange(Number(next))}
    >
      <SelectTrigger
        size={size}
        aria-label='Galaxy shown'
        className={stretch ? 'w-full min-w-0' : 'min-w-0'}
      >
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
  const [open, setOpen] = useState(false)
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
    <Collapsible
      open={open}
      onOpenChange={setOpen}
      id='section-cosmos-galaxy'
      className='flex min-w-0 flex-col gap-3 rounded-md border surface-framed border-gild/70 bg-card p-3'
    >
      <div className='flex min-w-0 items-center gap-3'>
        {galaxy ? (
          <GalaxyThumb
            galaxy={galaxy}
            shape={catalog.shape}
            label={galaxy.name}
            points={1600}
            className='size-portrait-lg shrink-0'
          />
        ) : (
          <Medallion icon={Orbit} tone='muted' />
        )}
        <div className='flex min-w-0 flex-1 flex-col gap-1'>
          <Label variant='overline'>
            {galaxy
              ? `Galaxy · ${catalogLabel(catalog.galaxy_types, galaxy.galaxy_type)}`
              : 'Outside every galaxy'}
          </Label>
          <div className='flex min-w-0 items-center gap-2'>
            <div className='min-w-0 flex-1'>
              <GalaxySwitcher
                heavens={heavens}
                catalog={catalog}
                value={galaxyId}
                onChange={onChange}
                stretch
              />
            </div>
            <CollapsibleTrigger asChild>
              <Button
                variant='outline'
                aria-label={open ? 'Hide the galaxy' : 'Show the galaxy'}
              >
                {open ? <ChevronUp /> : <ChevronDown />}
                {open ? 'Less' : 'More'}
              </Button>
            </CollapsibleTrigger>
          </div>
        </div>
      </div>
      <div className='flex min-w-0 flex-wrap gap-1'>
        <Chip icon={Star}>{plural(stars.length, 'star')}</Chip>
        <Chip icon={Globe2}>{plural(worlds.length, 'world')}</Chip>
        {leaving > 0 && (
          <Chip icon={Orbit}>
            {plural(leaving, 'route leaving', 'routes leaving')}
          </Chip>
        )}
        {galaxy && (
          <Chip icon={NUCLEI[galaxy.nucleus].icon}>
            {NUCLEI[galaxy.nucleus].label}
          </Chip>
        )}
      </div>
      <CollapsibleContent className='flex min-w-0 flex-col gap-3'>
        {galaxy ? (
          <>
            <GalaxyThumb
              galaxy={galaxy}
              shape={catalog.shape}
              label={galaxy.name}
              stars={stars.map((star) => ({
                id: star.id,
                x: star.x,
                y: star.y,
              }))}
              className='aspect-video w-full'
            />
            <div className='flex min-w-0 flex-wrap gap-1'>
              <Chip>{GALAXY_AGES[galaxy.age_stage]}</Chip>
              {galaxy.cluster_id !== null && (
                <Chip icon={Layers}>
                  {ladder.names.get(galaxy.cluster_id) ?? 'Its cluster'}
                </Chip>
              )}
              {zones.map(([zone, count]) => {
                const named = ZONES[zone as keyof typeof ZONES]
                return (
                  <Chip key={zone} icon={named.icon}>
                    {`${named.label}: ${count}`}
                  </Chip>
                )
              })}
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
                icon={Eye}
                tone='danger'
                label='Leak'
                value={`${galaxy.leak}%`}
              />
            </div>
          </>
        ) : (
          <Muted variant='caption'>
            {`${galaxyName(heavens.galaxies, galaxyId)}: these worlds drift outside every galaxy; their dimension alone shapes them.`}
          </Muted>
        )}
        <div className='flex min-w-0 flex-wrap gap-2'>
          {galaxy && (
            <Button
              size='sm'
              onClick={() =>
                drawers.open({ kind: 'galaxy', id: String(galaxy.id) })
              }
            >
              <Eye />
              Shape this galaxy
            </Button>
          )}
          <Button size='sm' variant='outline' asChild>
            <Link
              to='/heavens'
              search={galaxy ? { layer: 'galaxy', node: galaxy.id } : {}}
            >
              <Layers />
              See it in the Heavens
            </Link>
          </Button>
          <Button size='sm' variant='outline' onClick={() => setCreating(true)}>
            <Plus />
            New galaxy
          </Button>
        </div>
      </CollapsibleContent>
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
    </Collapsible>
  )
}
