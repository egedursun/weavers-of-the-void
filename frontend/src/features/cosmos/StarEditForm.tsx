import { useState } from 'react'
import { Save } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { type components } from '@/api/generated/schema'
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
import { type StarRecord, type StarType } from './api'
import { STAR_TYPES, STAR_TYPE_LABEL } from './model/labels'
import { useCosmicAction } from './useCosmicAction'

const BRIGHTNESS_MAX = 100

type StarBody = components['schemas']['PatchStarsStarIdBody']

export function StarEditForm({ star }: { star: StarRecord }) {
  const [name, setName] = useState(star.name)
  const [type, setType] = useState<StarType>(star.star_type)
  const [brightness, setBrightness] = useState(String(star.brightness))
  const [x, setX] = useState(String(star.x))
  const [y, setY] = useState(String(star.y))
  const [description, setDescription] = useState(star.description ?? '')
  const [prompt, setPrompt] = useState(star.image_prompt ?? '')
  const body: StarBody = {}
  if (name.trim() !== star.name) body.name = name.trim()
  if (type !== star.star_type) body.star_type = type
  if (Number(brightness) !== star.brightness)
    body.brightness = Number(brightness)
  if (Number(x) !== star.x) body.x = Number(x)
  if (Number(y) !== star.y) body.y = Number(y)
  if (description !== (star.description ?? '')) body.description = description
  if (prompt !== (star.image_prompt ?? '')) body.image_prompt = prompt
  const bright = Number(brightness)
  const invalid = !name.trim()
    ? 'A star needs a name.'
    : !Number.isInteger(bright) || bright < 0 || bright > BRIGHTNESS_MAX
      ? 'Brightness runs from 0 to 100.'
      : !Number.isFinite(Number(x)) || !Number.isFinite(Number(y))
        ? 'Position must be two numbers.'
        : Object.keys(body).length === 0
          ? 'Nothing has changed yet.'
          : undefined
  const edit = useCosmicAction({
    run: () =>
      unwrap(
        api.PATCH('/api/stars/{star_id}', {
          params: { path: { star_id: star.id } },
          body,
        })
      ),
    success: `${star.name} edited`,
  })
  return (
    <div className='flex min-w-0 flex-col gap-4'>
      <FormRow label='Name'>
        {(id) => (
          <Input
            id={id}
            value={name}
            maxLength={60}
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
      <FormRow label='Brightness' description='0 to 100.'>
        {(id) => (
          <Input
            id={id}
            type='number'
            min={0}
            max={BRIGHTNESS_MAX}
            inputMode='numeric'
            value={brightness}
            onChange={(event) => setBrightness(event.target.value)}
          />
        )}
      </FormRow>
      <FormRow
        label='Position'
        description='x and y in the plane of the cosmos.'
      >
        {(id) => (
          <>
            <Input
              id={id}
              aria-label='x'
              type='number'
              step='any'
              value={x}
              onChange={(event) => setX(event.target.value)}
            />
            <Input
              aria-label='y'
              type='number'
              step='any'
              value={y}
              onChange={(event) => setY(event.target.value)}
            />
          </>
        )}
      </FormRow>
      <FormRow label='Description'>
        {(id) => (
          <Textarea
            id={id}
            value={description}
            maxLength={600}
            onChange={(event) => setDescription(event.target.value)}
          />
        )}
      </FormRow>
      <FormRow label='Image prompt' description='Leave blank to delete.'>
        {(id) => (
          <Textarea
            id={id}
            value={prompt}
            onChange={(event) => setPrompt(event.target.value)}
          />
        )}
      </FormRow>
      <div className='flex min-w-0 flex-wrap gap-2'>
        <CosmicActionButton
          actionId='star:edit'
          label='Save the star'
          icon={Save}
          variant='default'
          pending={edit.isPending}
          blockedReason={invalid}
          onRun={() => edit.mutate()}
        />
      </div>
    </div>
  )
}
