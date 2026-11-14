import { useState } from 'react'
import { Globe2, X } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { type components } from '@/api/generated/schema'
import { plural } from '@/lib/units'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import { FormRow, JobProgress } from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { CosmicActionButton } from './CosmicActionButton'
import { PaletteStrip } from './Glyphs'
import { StarOptions } from './StarOptions'
import { type StarType, type WorldType, useJob } from './api'
import { type CosmosIndex } from './model/cosmosModel'
import { STAR_TYPES, STAR_TYPE_LABEL, WORLD_TYPES } from './model/labels'
import { type RuleBook } from './model/rules'
import { useCosmicAction } from './useCosmicAction'

type Placement = 'fate' | 'star' | 'moon' | 'new'

const PLACEMENT_LABEL: Record<Placement, string> = {
  fate: 'Let Fate choose',
  star: 'Around a star',
  moon: 'Moon of a world',
  new: 'New star system',
}

const PLACEMENT_NOTE: Record<Placement, string> = {
  fate: 'Fate places the world where its story fits best.',
  star: 'The world joins the planets of the star you choose.',
  moon: 'The world circles the world you choose as its moon.',
  new: 'A new star ignites in the void and the world is its first planet.',
}

type CreateWorldBody = components['schemas']['PostWorldsBody']

type CreateWorldFormProps = {
  index: CosmosIndex
  rules: RuleBook
}

export function CreateWorldForm({ index, rules }: CreateWorldFormProps) {
  const [worldType, setWorldType] = useState<WorldType>('ordinary')
  const [inspiration, setInspiration] = useState('')
  const [placement, setPlacement] = useState<Placement>('fate')
  const [starId, setStarId] = useState('')
  const [starOpen, setStarOpen] = useState(false)
  const [parentId, setParentId] = useState('')
  const [newStarType, setNewStarType] = useState<StarType | 'fate'>('fate')
  const topLevel = index.worlds.filter(
    (item) => item.world.parent_world_id === null
  )
  const star =
    starId || (index.data.stars[0] ? String(index.data.stars[0].id) : '')
  const parent = parentId || (topLevel[0] ? String(topLevel[0].world.id) : '')
  const create = useCosmicAction({
    run: () => {
      const body: CreateWorldBody = {
        world_type: worldType,
        inspiration,
        new_star: placement === 'new',
      }
      if (placement === 'star') body.star_id = Number(star)
      if (placement === 'moon') body.parent_world_id = Number(parent)
      if (placement === 'new' && newStarType !== 'fate')
        body.new_star_type = newStarType
      return unwrap(api.POST('/api/worlds', { body }))
    },
    success: 'A new world is being born; watch the live feed',
    onDone: () => setInspiration(''),
  })
  const { data: job } = useJob(create.jobId)
  const maxLength = rules.get('inspirationMax')
  const blocked =
    placement === 'star' && !star
      ? 'There is no star yet; choose another placement.'
      : placement === 'moon' && !parent
        ? 'There is no world to circle yet.'
        : undefined
  return (
    <div className='flex min-w-0 flex-col gap-4'>
      <Muted>
        Pick a type and write an inspiration. Fate births the world with its own
        dialect, regions, sky, unique resource and natives; watch it in the live
        feed.
      </Muted>
      <RadioGroup
        value={worldType}
        onValueChange={(value) => setWorldType(value as WorldType)}
        aria-label='World type'
        className='grid-cols-1 gap-2 sm:grid-cols-2'
      >
        {WORLD_TYPES.map((type) => {
          const look = index.look(type)
          const id = `world-type-${type}`
          return (
            <label
              key={type}
              htmlFor={id}
              className={cn(
                'flex min-w-0 cursor-pointer flex-col gap-2 rounded-lg border p-3 transition-colors hover:bg-accent',
                type === worldType && 'border-primary bg-accent'
              )}
            >
              <span className='flex min-w-0 items-center gap-2'>
                <RadioGroupItem id={id} value={type} />
                <Text as='span' weight='medium' truncate>
                  {look?.label ?? type}
                </Text>
              </span>
              <PaletteStrip
                palette={look?.palette.biome_colours ?? []}
                label={`${look?.label ?? type} palette`}
              />
            </label>
          )
        })}
      </RadioGroup>
      <FormRow
        label='Inspiration'
        description='Optional. Your draft is kept until the world is born.'
      >
        {(id) => (
          <div className='flex min-w-0 flex-1 flex-col gap-1'>
            <Textarea
              id={id}
              value={inspiration}
              maxLength={maxLength}
              placeholder='What is this world like: its land, its sky, the rule that makes it its own…'
              onChange={(event) => setInspiration(event.target.value)}
            />
            {maxLength !== undefined && (
              <Muted variant='caption'>{`${inspiration.length} / ${maxLength}`}</Muted>
            )}
          </div>
        )}
      </FormRow>
      <div className='flex min-w-0 flex-col gap-2'>
        <Label>Where should it be born?</Label>
        <ToggleGroup
          type='single'
          variant='outline'
          size='sm'
          value={placement}
          onValueChange={(value) => value && setPlacement(value as Placement)}
          className='flex-wrap'
        >
          {(Object.keys(PLACEMENT_LABEL) as Placement[]).map((key) => (
            <ToggleGroupItem key={key} value={key}>
              {PLACEMENT_LABEL[key]}
            </ToggleGroupItem>
          ))}
        </ToggleGroup>
        <Muted variant='caption'>{PLACEMENT_NOTE[placement]}</Muted>
      </div>
      {placement === 'star' && (
        <FormRow label='Star'>
          {(id) => (
            <Select
              value={star}
              onValueChange={setStarId}
              open={starOpen}
              onOpenChange={setStarOpen}
            >
              <SelectTrigger id={id} className='w-full'>
                <SelectValue placeholder='No star yet' />
              </SelectTrigger>
              <SelectContent>
                <StarOptions
                  stars={index.data.stars}
                  selected={star}
                  open={starOpen}
                  valueOf={(item) => String(item.id)}
                  label={(item) =>
                    `${item.name} · ${STAR_TYPE_LABEL[item.star_type]} · ${plural(index.planetsOf(item.id).length, 'planet', 'planets')}`
                  }
                />
              </SelectContent>
            </Select>
          )}
        </FormRow>
      )}
      {placement === 'moon' && (
        <FormRow label='Parent world'>
          {(id) => (
            <Select value={parent} onValueChange={setParentId}>
              <SelectTrigger id={id} className='w-full'>
                <SelectValue placeholder='No world yet' />
              </SelectTrigger>
              <SelectContent>
                {topLevel.map((item) => (
                  <SelectItem key={item.world.id} value={String(item.world.id)}>
                    {`${item.world.name} · ${item.type_label}`}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
        </FormRow>
      )}
      {placement === 'new' && (
        <FormRow label='New star type'>
          {(id) => (
            <Select
              value={newStarType}
              onValueChange={(value) =>
                setNewStarType(value as StarType | 'fate')
              }
            >
              <SelectTrigger id={id} className='w-full'>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value='fate'>Let Fate choose</SelectItem>
                {STAR_TYPES.map((value) => (
                  <SelectItem key={value} value={value}>
                    {STAR_TYPE_LABEL[value]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
        </FormRow>
      )}
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <CosmicActionButton
          actionId='create_world'
          label='Create the world'
          icon={Globe2}
          variant='default'
          cost={rules.get('createWorld')}
          pending={
            create.isPending ||
            (job !== undefined &&
              (job.status === 'queued' || job.status === 'running'))
          }
          blockedReason={blocked}
          onRun={() => create.mutate()}
        />
      </div>
      {job && (
        <JobProgress
          job={job}
          title='A world is being born'
          action={
            job.status !== 'queued' && job.status !== 'running' ? (
              <Button
                variant='ghost'
                size='icon-sm'
                aria-label='Dismiss'
                onClick={create.clearJob}
              >
                <X />
              </Button>
            ) : undefined
          }
        />
      )}
    </div>
  )
}
