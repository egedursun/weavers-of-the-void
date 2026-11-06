import { useState } from 'react'
import { Sparkles } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { naturalLawValues } from '@/api/generated/schema'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { FormRow } from '@/components/domain'
import { ActionButton } from '@/features/pantheon/ActionButton'
import { useWorldState } from '@/features/pantheon/api'
import { useGodGate, useRuleLookup } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { humanize, useLabels } from '@/features/pantheon/labels'

const FATE = 'fate'
const LAW_TYPES = new Set([FATE, 'law', 'natural_law'])

type RevelationDialogProps = {
  triggerLabel?: string
  triggerVariant?: 'default' | 'outline'
  triggerSize?: 'sm' | 'default'
}

export function RevelationDialog({
  triggerLabel = 'Reveal',
  triggerVariant = 'outline',
  triggerSize = 'default',
}: RevelationDialogProps) {
  const [open, setOpen] = useState(false)
  const [content, setContent] = useState('')
  const [entityType, setEntityType] = useState(FATE)
  const [mechanic, setMechanic] = useState(FATE)
  const [worldId, setWorldId] = useState(FATE)
  const { catalogue } = useLabels()
  const state = useWorldState()
  const worlds = state.data?.worlds ?? []
  const rule = useRuleLookup()
  const cost = rule('costs.revelation')
  const { reason } = useGodGate()
  const reveal = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/revelations', {
          body: {
            content: content.trim(),
            entity_type: entityType === FATE ? null : entityType,
            world_id: worldId === FATE ? null : Number(worldId),
            mechanic:
              LAW_TYPES.has(entityType) && mechanic !== FATE ? mechanic : null,
          },
        })
      ),
    success: 'The revelation is descending',
    onDone: () => {
      setContent('')
      setOpen(false)
    },
  })
  const blocked =
    reason({ cost, llm: true }) ??
    (content.trim() ? null : 'Your revelation must have content.')
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant={triggerVariant} size={triggerSize}>
          <Sparkles />
          {triggerLabel}
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create with your own hand</DialogTitle>
          <DialogDescription>
            Write an idea; it appears as a single record tied to the world's
            language, cosmology and existing records.
          </DialogDescription>
        </DialogHeader>
        <div className='flex min-w-0 flex-col gap-3'>
          <FormRow label='Your revelation'>
            {(id) => (
              <Textarea
                id={id}
                value={content}
                placeholder='Describe what you reveal: a being, a place, a law of nature, an event, a people…'
                onChange={(event) => setContent(event.target.value)}
              />
            )}
          </FormRow>
          <FormRow label='Type'>
            {(id) => (
              <Select value={entityType} onValueChange={setEntityType}>
                <SelectTrigger id={id} className='w-full'>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={FATE}>Let Fate choose</SelectItem>
                  {(catalogue?.entity_types ?? []).map((type) => (
                    <SelectItem key={type.key} value={type.key}>
                      {type.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          </FormRow>
          {LAW_TYPES.has(entityType) && (
            <FormRow label='Mechanism' description='Only for a law.'>
              {(id) => (
                <Select value={mechanic} onValueChange={setMechanic}>
                  <SelectTrigger id={id} className='w-full'>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value={FATE}>Let Fate choose</SelectItem>
                    {naturalLawValues
                      .filter((law) => law !== 'none')
                      .map((law) => (
                        <SelectItem key={law} value={law}>
                          {humanize(law)}
                        </SelectItem>
                      ))}
                  </SelectContent>
                </Select>
              )}
            </FormRow>
          )}
          {worlds.length > 1 && (
            <FormRow label='World'>
              {(id) => (
                <Select value={worldId} onValueChange={setWorldId}>
                  <SelectTrigger id={id} className='w-full'>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value={FATE}>Let Fate choose</SelectItem>
                    {worlds.map((world) => (
                      <SelectItem key={world.id} value={String(world.id)}>
                        {world.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            </FormRow>
          )}
        </div>
        <DialogFooter>
          <ActionButton
            label='Reveal'
            icon={Sparkles}
            variant='default'
            cost={cost}
            rule='costs.revelation'
            blocked={blocked}
            pending={reveal.isPending}
            onRun={() => reveal.mutate()}
          />
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
