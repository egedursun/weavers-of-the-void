import { useState } from 'react'
import { Save } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Switch } from '@/components/ui/switch'
import { Textarea } from '@/components/ui/textarea'
import { FormRow, Section } from '@/components/domain'
import { Muted } from '@/components/typography'
import { useLoreMutation } from '../api/mutations'
import { type EntityRecord } from '../api/types'
import { NAME_MAX, SUBTYPE_MAX } from '../constants'

export function EntityEditForm({
  entity,
  readOnlyReason,
}: {
  entity: EntityRecord
  readOnlyReason: string | null
}) {
  const [name, setName] = useState(entity.name)
  const [title, setTitle] = useState(entity.title ?? '')
  const [subtype, setSubtype] = useState(entity.subtype ?? '')
  const [description, setDescription] = useState(entity.description)
  const [water, setWater] = useState(entity.is_water)
  const [underworld, setUnderworld] = useState(entity.is_underworld)
  const region = entity.entity_type === 'region'
  const save = useLoreMutation({
    run: () =>
      unwrap(
        api.PATCH('/api/entities/{entity_id}', {
          params: { path: { entity_id: entity.id } },
          body: {
            name: name.trim(),
            title: title.trim() || null,
            subtype: subtype.trim() || null,
            description: description.trim(),
            ...(region && water !== entity.is_water ? { is_water: water } : {}),
            ...(region && underworld !== entity.is_underworld
              ? { is_underworld: underworld }
              : {}),
          },
        })
      ),
    success: `${name.trim()} updated`,
  })
  const changed =
    name.trim() !== entity.name ||
    (title.trim() || null) !== entity.title ||
    (subtype.trim() || null) !== entity.subtype ||
    description.trim() !== entity.description ||
    water !== entity.is_water ||
    underworld !== entity.is_underworld
  const reason =
    readOnlyReason ??
    (name.trim() === '' ? 'A record needs a name.' : null) ??
    (description.trim() === '' ? 'A record needs a description.' : null) ??
    (!changed ? 'Nothing has changed.' : null) ??
    (save.isPending ? 'Working on it.' : null)
  return (
    <Section
      id='section-edit'
      title='Rename and reshape'
      description='Renaming also fixes the old name in the chronicle, bonds and every text.'
    >
      <form
        className='flex min-w-0 flex-col gap-3'
        onSubmit={(event) => {
          event.preventDefault()
          if (reason === null) save.mutate()
        }}
      >
        <FormRow label='Name'>
          {(id) => (
            <Input
              id={id}
              maxLength={NAME_MAX}
              value={name}
              onChange={(event) => setName(event.target.value)}
            />
          )}
        </FormRow>
        <FormRow label='Title' description='Optional'>
          {(id) => (
            <Input
              id={id}
              maxLength={NAME_MAX}
              value={title}
              onChange={(event) => setTitle(event.target.value)}
            />
          )}
        </FormRow>
        <FormRow
          label='Kind'
          description='Optional subtype, such as harbour town'
        >
          {(id) => (
            <Input
              id={id}
              maxLength={SUBTYPE_MAX}
              value={subtype}
              onChange={(event) => setSubtype(event.target.value)}
            />
          )}
        </FormRow>
        <FormRow label='Description'>
          {(id) => (
            <Textarea
              id={id}
              value={description}
              onChange={(event) => setDescription(event.target.value)}
            />
          )}
        </FormRow>
        {region && (
          <>
            <FormRow
              label='Water'
              description='Drawn and treated as water: a sea, lake or strait.'
            >
              {(id) => (
                <Switch id={id} checked={water} onCheckedChange={setWater} />
              )}
            </FormRow>
            <FormRow
              label='Realm of the dead'
              description='An underworld where the souls of the dead gather.'
            >
              {(id) => (
                <Switch
                  id={id}
                  checked={underworld}
                  onCheckedChange={setUnderworld}
                />
              )}
            </FormRow>
          </>
        )}
        <div className='flex min-w-0 flex-wrap items-center gap-2'>
          <Button
            type='submit'
            disabled={reason !== null}
            disabledReason={reason ?? undefined}
          >
            <Save />
            Save changes
          </Button>
          {changed && <Muted variant='caption'>Unsaved changes</Muted>}
        </div>
      </form>
    </Section>
  )
}
