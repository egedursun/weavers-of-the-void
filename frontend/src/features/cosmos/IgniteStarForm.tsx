import { useState } from 'react'
import { Sparkle } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { FormRow } from '@/components/domain'
import { CosmicActionButton } from './CosmicActionButton'
import { type StarType } from './api'
import { type CosmosIndex } from './model/cosmosModel'
import { STAR_TYPES, STAR_TYPE_LABEL } from './model/labels'
import { type RuleBook } from './model/rules'
import { useCosmicAction } from './useCosmicAction'

const NAME_MAX = 60
const DESCRIPTION_MAX = 300
const VOID = 'void'

export function IgniteStarForm({
  index,
  rules,
  galaxyId,
  onGalaxy,
}: {
  index: CosmosIndex
  rules: RuleBook
  galaxyId?: number
  onGalaxy?: (galaxyId: number) => void
}) {
  const [name, setName] = useState('')
  const [type, setType] = useState<StarType>('yellow_dwarf')
  const [description, setDescription] = useState('')
  const [sky, setSky] = useState(VOID)
  const ignite = useCosmicAction({
    writes: [{ lever: 'cosmic:hang_star' }],
    run: () =>
      unwrap(
        api.POST('/api/cosmic/hang-star', {
          body: {
            name: name.trim(),
            star_type: type,
            description: description.trim() || null,
            world_id: sky === VOID ? null : Number(sky),
            galaxy_id:
              sky === VOID && galaxyId !== undefined && galaxyId > 0
                ? galaxyId
                : null,
          },
        })
      ),
    success: 'A new star ignited',
    onDone: (response) => {
      setName('')
      setDescription('')
      const placed = response.values?.galaxy_id
      if (typeof placed === 'number') onGalaxy?.(placed)
    },
  })
  return (
    <div className='flex min-w-0 flex-col gap-4'>
      <FormRow label='Name' description='Leave blank and Fate names it.'>
        {(id) => (
          <Input
            id={id}
            value={name}
            maxLength={NAME_MAX}
            onChange={(event) => setName(event.target.value)}
          />
        )}
      </FormRow>
      <FormRow label='Type'>
        {(id) => (
          <Select
            value={type}
            onValueChange={(value) => setType(value as StarType)}
          >
            <SelectTrigger id={id} className='w-full'>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {STAR_TYPES.map((value) => (
                <SelectItem key={value} value={value}>
                  {STAR_TYPE_LABEL[value]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
      </FormRow>
      <FormRow
        label='Where it hangs'
        description='A star in the void of the galaxy shown, or a star set in one world’s sky; a world with no sun comes to circle it.'
      >
        {(id) => (
          <Select value={sky} onValueChange={setSky}>
            <SelectTrigger id={id} className='w-full'>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={VOID}>In the void</SelectItem>
              {index.worlds.map((item) => (
                <SelectItem key={item.world.id} value={String(item.world.id)}>
                  {`In the sky of ${item.world.name}`}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
      </FormRow>
      <FormRow label='Description'>
        {(id) => (
          <Textarea
            id={id}
            value={description}
            maxLength={DESCRIPTION_MAX}
            placeholder='What kind of light it gives, and what it means to those beneath it…'
            onChange={(event) => setDescription(event.target.value)}
          />
        )}
      </FormRow>
      <div className='flex min-w-0 flex-wrap gap-2'>
        <CosmicActionButton
          act={ignite}
          actionId='cosmic:hang_star'
          label='Ignite'
          icon={Sparkle}
          variant='default'
          cost={rules.get('igniteStar')}
          pending={ignite.isPending}
          onRun={() => ignite.mutate()}
        />
      </div>
    </div>
  )
}
