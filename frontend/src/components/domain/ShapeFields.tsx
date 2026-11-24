import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { FormRow } from './FormRow'
import { type Shape } from './useShape'

export function ShapeFields({
  shape,
  onChange,
  titled = false,
  described = true,
  blocked = null,
}: {
  shape: Shape
  onChange: (next: Shape) => void
  titled?: boolean
  described?: boolean
  blocked?: string | null
}) {
  return (
    <div
      data-domain='shape-fields'
      className='grid min-w-0 gap-2 sm:grid-cols-2'
    >
      <FormRow label='Name' description='Leave empty and the world names it.'>
        {(id) => (
          <Input
            id={id}
            value={shape.name}
            disabled={blocked !== null}
            onChange={(event) =>
              onChange({ ...shape, name: event.target.value })
            }
          />
        )}
      </FormRow>
      {titled && (
        <FormRow label='Title' description='How others address it.'>
          {(id) => (
            <Input
              id={id}
              value={shape.title}
              disabled={blocked !== null}
              onChange={(event) =>
                onChange({ ...shape, title: event.target.value })
              }
            />
          )}
        </FormRow>
      )}
      {described && (
        <div className='min-w-0 sm:col-span-2'>
          <FormRow
            label='Description'
            description='Leave empty and the world tells it.'
          >
            {(id) => (
              <Textarea
                id={id}
                value={shape.description}
                disabled={blocked !== null}
                onChange={(event) =>
                  onChange({ ...shape, description: event.target.value })
                }
              />
            )}
          </FormRow>
        </div>
      )}
    </div>
  )
}
