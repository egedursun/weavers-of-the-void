import { useEffect } from 'react'
import { Eye, House } from 'lucide-react'
import { toast } from 'sonner'
import { setReadOnly } from '@/api/readOnly'
import { Button } from '@/components/ui/button'
import { Text } from '@/components/typography'
import { useDiscovery, useEndDiscovery } from './api'

export function DiscoveryBanner() {
  const discovery = useDiscovery()
  const end = useEndDiscovery()
  const active = discovery.data?.active ?? false
  useEffect(() => {
    setReadOnly(active)
  }, [active])
  if (!active) return null
  const guest = discovery.data?.guest
  const details = [
    guest?.creator ? `made by ${guest.creator}` : null,
    guest?.epoch ? `epoch ${guest.epoch}` : null,
  ]
    .filter(Boolean)
    .join(', ')
  return (
    <div
      data-layout='discovery-banner'
      role='status'
      className='flex min-w-0 flex-wrap items-center gap-x-3 gap-y-2 border-b border-warning/40 bg-warning/15 px-3 py-2 md:px-4'
    >
      <Eye aria-hidden='true' className='size-icon-md shrink-0 text-warning' />
      <Text
        as='span'
        weight='medium'
        truncate={2}
        className='min-w-0 flex-1 basis-48'
      >
        {`Discovery mode: ${guest?.name ?? 'a guest world'} is open read-only${details ? ` (${details})` : ''}. Your own world waits aside.`}
      </Text>
      <Button
        size='sm'
        disabled={end.isPending}
        disabledReason='Returning'
        onClick={() =>
          end.mutate(undefined, {
            onSuccess: () => {
              setReadOnly(false)
              toast.success('You returned to your own world')
            },
            onError: (error) => toast.error(error.message),
          })
        }
      >
        <House />
        Return to my world
      </Button>
    </div>
  )
}
