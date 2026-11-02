import { useState } from 'react'
import { Flame } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { Textarea } from '@/components/ui/textarea'
import { FormRow, Section } from '@/components/domain'
import { ActionButton } from '@/features/pantheon/ActionButton'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'

const MANIFESTO_MAX = 300

export function SonRebellion({ sonId, name }: { sonId: number; name: string }) {
  const [manifesto, setManifesto] = useState('')
  const { reason } = useGodGate()
  const force = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/sons/{son_id}/rebellion', {
          params: { path: { son_id: sonId } },
          body: { manifesto: manifesto.trim() },
        })
      ),
    onDone: () => setManifesto(''),
  })
  return (
    <Section
      title='Force a rebellion'
      description={`Make ${name} rise against you: his loyalty falls, his ambition grows and loyal siblings sour on him. It also happens on its own when his will outgrows his loyalty.`}
      level={3}
    >
      <FormRow
        label="The rebel's manifesto"
        description='Written in the chronicle.'
      >
        {(id) => (
          <Textarea
            id={id}
            value={manifesto}
            maxLength={MANIFESTO_MAX}
            onChange={(event) => setManifesto(event.target.value)}
          />
        )}
      </FormRow>
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <ActionButton
          label='Force the rebellion'
          icon={Flame}
          variant='destructive'
          blocked={
            reason() ??
            (manifesto.trim() === '' ? 'Write the manifesto first.' : null)
          }
          pending={force.isPending}
          confirm={{
            title: 'Force this rebellion?',
            description: `${name} becomes a rebel until you suppress or forgive him.`,
          }}
          onRun={() => force.mutate()}
        />
      </div>
    </Section>
  )
}
