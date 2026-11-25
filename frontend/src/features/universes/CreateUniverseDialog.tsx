import { useState } from 'react'
import { BookPlus, LoaderCircle } from 'lucide-react'
import { toast } from 'sonner'
import { plural } from '@/lib/units'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { FormRow, Medallion } from '@/components/domain'
import { Text } from '@/components/typography'
import { useCreateUniverse } from './api'
import { NAME_MAX, NOTES_MAX, cleanTags, nameProblem } from './universeModel'
import { useEnterUniverse } from './useEnterUniverse'

const FORM_ID = 'create-universe'

export function CreateUniverseDialog({
  open,
  onOpenChange,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const [name, setName] = useState('')
  const [notes, setNotes] = useState('')
  const [summary, setSummary] = useState('')
  const [tags, setTags] = useState('')
  const [touched, setTouched] = useState(false)
  const create = useCreateUniverse()
  const { enter, opening } = useEnterUniverse()
  const problem = nameProblem(name)
  const working = create.isPending || opening !== null
  const reset = () => {
    setName('')
    setNotes('')
    setSummary('')
    setTags('')
    setTouched(false)
  }
  const submit = () => {
    setTouched(true)
    if (problem !== null) return
    create.mutate(
      {
        name: name.trim(),
        summary: summary.trim(),
        notes: notes.trim(),
        tags: cleanTags(tags),
      },
      {
        onSuccess: (universe) => {
          toast.success(`${universe.name} stands on the shelf`)
          reset()
          onOpenChange(false)
          enter(universe, '/genesis')
        },
        onError: (error) => toast.error(error.message),
      }
    )
  }
  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!working) onOpenChange(next)
      }}
    >
      <DialogContent className='sm:max-w-xl'>
        <DialogHeader>
          <div className='flex min-w-0 items-center gap-3'>
            <Medallion icon={BookPlus} />
            <DialogTitle>Create a universe</DialogTitle>
          </div>
          <DialogDescription>
            A new, empty universe gets its own book on the shelf. You give it a
            name now and shape its birth on the next screen.
          </DialogDescription>
        </DialogHeader>
        <form
          id={FORM_ID}
          className='flex min-w-0 flex-col gap-4'
          onSubmit={(event) => {
            event.preventDefault()
            submit()
          }}
        >
          <FormRow
            label='Name'
            description={`Required, at most ${plural(NAME_MAX, 'character')}. You can rename it later.`}
          >
            {(id) => (
              <div className='flex w-full min-w-0 flex-col gap-1'>
                <Input
                  id={id}
                  autoFocus
                  value={name}
                  maxLength={NAME_MAX}
                  aria-invalid={(touched && problem !== null) || undefined}
                  onChange={(event) => setName(event.target.value)}
                />
                {touched && problem && (
                  <Text variant='caption' tone='destructive'>
                    {problem}
                  </Text>
                )}
              </div>
            )}
          </FormRow>
          <FormRow
            label='Summary'
            description='Optional. Left empty, it is written from the seed when the universe is born.'
          >
            {(id) => (
              <Textarea
                id={id}
                value={summary}
                maxLength={NOTES_MAX}
                onChange={(event) => setSummary(event.target.value)}
              />
            )}
          </FormRow>
          <FormRow
            label='Notes'
            description='Only for you: what this universe is for, or anything to remember.'
          >
            {(id) => (
              <Textarea
                id={id}
                value={notes}
                maxLength={NOTES_MAX}
                onChange={(event) => setNotes(event.target.value)}
              />
            )}
          </FormRow>
          <FormRow
            label='Tags'
            description='Separate tags with commas; they let you filter the shelves.'
          >
            {(id) => (
              <Input
                id={id}
                value={tags}
                onChange={(event) => setTags(event.target.value)}
              />
            )}
          </FormRow>
        </form>
        <DialogFooter>
          <Button
            type='button'
            variant='outline'
            disabled={working}
            disabledReason='The universe is being made.'
            onClick={() => onOpenChange(false)}
          >
            Cancel
          </Button>
          <Button
            act={create}
            type='submit'
            form={FORM_ID}
            disabled={working}
            disabledReason='The universe is being made.'
          >
            {working ? (
              <LoaderCircle className='animate-spin motion-reduce:animate-none' />
            ) : (
              <BookPlus />
            )}
            {working ? 'Making the universe' : 'Create and shape it'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
