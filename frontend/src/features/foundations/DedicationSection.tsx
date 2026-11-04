import { useState } from 'react'
import {
  Anchor,
  Church,
  Lock,
  Save,
  Sparkles,
  TriangleAlert,
  Unlink,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import { EmptyState, EntityLink, Medallion, Section } from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { Adjust } from '@/features/wars/military/parts'
import { useDedication } from './api'
import { HoldToggle, SonSelect } from './parts'

export function DedicationSection({
  structureId,
  readOnlyReason,
}: {
  structureId: number
  readOnlyReason?: string | null
}) {
  const view = useDedication(structureId)
  const { reason } = useGodGate()
  const blocked = readOnlyReason ?? reason()
  const [son, setSon] = useState('')
  const [hold, setHold] = useState(true)
  const dedicate = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/structure:dedicate', {
          body: { structure_id: structureId, son_id: Number(son), hold },
        })
      ),
  })
  const lift = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/structure:undedicate', {
          body: { structure_id: structureId },
        })
      ),
  })
  const busy =
    blocked ?? (dedicate.isPending || lift.isPending ? 'Working…' : null)
  const data = view.data
  return (
    <Section
      id='section-dedication'
      title='Dedication'
      description='The god this work was raised for. A dedicated work brings its god fame and existence, and can anchor them.'
      icon={Church}
    >
      {view.isPending && <Muted>Reading the dedication…</Muted>}
      {view.isError && (
        <EmptyState
          icon={TriangleAlert}
          title='The dedication could not be read'
          description={view.error.message}
        />
      )}
      {data && (
        <div
          data-surface='StructureDedication'
          className='flex min-w-0 flex-col gap-4'
        >
          <div className='flex min-w-0 items-center gap-3 rounded-xl border bg-card p-4'>
            <Medallion
              icon={data.son ? Church : Sparkles}
              tone={data.son ? 'gold' : 'muted'}
              size='sm'
            />
            <div className='flex min-w-0 flex-1 flex-col'>
              <Text weight='semibold' truncate>
                {data.son ? (
                  <>
                    Dedicated to{' '}
                    <EntityLink kind='son' id={String(data.son.id)}>
                      {data.son.name}
                    </EntityLink>
                  </>
                ) : (
                  'Dedicated to no god'
                )}
              </Text>
              <Muted variant='caption'>
                {data.son
                  ? 'Every age it adds to its god’s fame and existence.'
                  : 'Dedicate it and its god gains fame, existence and a possible anchor.'}
              </Muted>
            </div>
            <div className='flex shrink-0 flex-wrap gap-1.5'>
              {data.anchors_son && (
                <Badge size='sm' variant='default'>
                  <Anchor aria-hidden='true' />
                  Their anchor
                </Badge>
              )}
              {data.held && (
                <Badge size='sm' variant='outline'>
                  <Lock aria-hidden='true' />
                  Held
                </Badge>
              )}
            </div>
          </div>
          <Adjust
            label='Dedicate'
            title='Dedication'
            note='Raise it for another god or lift the dedication. Lifting it also frees its god from it as an anchor.'
          >
            <div className='grid min-w-0 grid-cols-1 items-end gap-3 sm:grid-cols-3'>
              <div className='min-w-0 sm:col-span-2'>
                <SonSelect
                  label='God'
                  value={son}
                  onChange={setSon}
                  disabled={busy !== null}
                />
              </div>
              <label className='flex min-w-0 items-center gap-2 rounded-lg border bg-background p-2.5'>
                <Switch
                  checked={hold}
                  onCheckedChange={setHold}
                  aria-label='Hold the dedication'
                />
                <Text as='span'>Hold it</Text>
              </label>
            </div>
            <div className='flex min-w-0 flex-wrap gap-2'>
              <Button
                size='sm'
                disabled={busy !== null || son === ''}
                disabledReason={
                  busy ?? (son === '' ? 'Choose a god' : undefined)
                }
                onClick={() => dedicate.mutate(undefined)}
              >
                <Save />
                Dedicate
              </Button>
              <Button
                size='sm'
                variant='outline'
                disabled={busy !== null || data.son === null}
                disabledReason={
                  busy ?? (data.son ? undefined : 'Not dedicated')
                }
                onClick={() => lift.mutate(undefined)}
              >
                <Unlink />
                Lift the dedication
              </Button>
            </div>
            <HoldToggle
              kind='dedicated_son_id'
              nodeId={structureId}
              held={data.held}
              blocked={blocked}
              what='the dedication'
            />
          </Adjust>
        </div>
      )}
    </Section>
  )
}
