import { useState } from 'react'
import { Skull, Trash2 } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Section } from '@/components/domain'
import { Muted } from '@/components/typography'
import { TypedConfirm } from '@/features/backups/TypedConfirm'
import { RESET_WORD } from '@/features/backups/api'
import { useResetWorld } from './api'

type ResetWorldProps = {
  hasWorld: boolean
  readOnly: boolean
}

export function ResetWorld({ hasWorld, readOnly }: ResetWorldProps) {
  const reset = useResetWorld()
  const [open, setOpen] = useState(false)
  return (
    <div className='rounded-xl border border-destructive/40 bg-destructive/5 p-5'>
      <Section
        title='Danger zone: reset the world'
        description='The world, its sons, its chronicle and its images are removed. A safety backup is taken first, so this too can be restored.'
        level={3}
        icon={Skull}
        tone='danger'
      >
        <Muted>
          After the reset the creation screen opens and a new genesis can begin.
        </Muted>
        <div>
          <Button
            variant='destructive'
            disabled={!hasWorld || readOnly}
            disabledReason={
              readOnly
                ? 'A guest world is read-only'
                : 'There is no world to reset'
            }
            onClick={() => setOpen(true)}
          >
            <Trash2 />
            Reset the world
          </Button>
        </div>
        <TypedConfirm
          open={open}
          onOpenChange={setOpen}
          title='Reset the whole world?'
          description='Everything is removed from the live database. The safety backup keeps a copy you can restore.'
          word={RESET_WORD}
          confirmText='Reset the world'
          loading={reset.isPending}
          onConfirm={(word) =>
            reset.mutate(word, {
              onSuccess: (result) => {
                setOpen(false)
                toast.success(
                  `World reset. Safety copy: ${result.safety_backup}`
                )
              },
              onError: (error) => toast.error(error.message),
            })
          }
        />
      </Section>
    </div>
  )
}
