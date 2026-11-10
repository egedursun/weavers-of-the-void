import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Brush, Palette, Save } from 'lucide-react'
import { toast } from 'sonner'
import { queryKeys } from '@/api/queryKeys'
import { formatInteger } from '@/lib/format'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { ConfirmDialog, Section } from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { useWorldState } from '@/features/overview/api'
import { usePatchSettings, useWorldSettings } from '@/features/settings/api'
import { ImageStylePicker } from './ImageStylePicker'
import { imageKeys, restyleBulk, useImageGenStatus } from './api'
import {
  type ImageStyle,
  imageStyleLabel,
  imageStyleProblem,
} from './imageStyles'

type Draft = { style: ImageStyle; custom: string }

export function ImageStyleSettings() {
  const settings = useWorldSettings(true)
  const status = useImageGenStatus()
  const state = useWorldState()
  const patch = usePatchSettings()
  const queryClient = useQueryClient()
  const [draft, setDraft] = useState<Draft | null>(null)
  const [confirming, setConfirming] = useState(false)
  const restyle = useMutation({
    mutationFn: restyleBulk,
    onSuccess: () => {
      toast.success('Repainting started')
      void queryClient.invalidateQueries({ queryKey: imageKeys.all })
      void queryClient.invalidateQueries({ queryKey: queryKeys.world.all })
    },
    onError: (error) => toast.error(error.message),
  })

  if (settings.isPending) return <Skeleton className='h-96 w-full' />
  if (settings.isError)
    return <Text tone='destructive'>{settings.error.message}</Text>

  const saved: Draft = {
    style: settings.data.image_style,
    custom: settings.data.image_style_custom,
  }
  const current = draft ?? saved
  const customChanged =
    current.style === 'custom' && current.custom.trim() !== saved.custom.trim()
  const dirty = current.style !== saved.style || customChanged
  const problem = imageStyleProblem(current.style, current.custom)
  const readOnly = state.data?.read_only ?? false
  const offStyle = status.data?.off_style ?? 0
  const queue = status.data?.status
  const saveReason = readOnly
    ? 'A guest world is open read-only.'
    : (problem ?? (dirty ? null : 'This is already the world style.'))
  const restyleReason = readOnly
    ? 'A guest world is open read-only.'
    : dirty
      ? 'Save the new style first.'
      : queue && !queue.available
        ? (queue.reason ?? 'The image worker is not available right now.')
        : queue?.bulk.running
          ? 'A bulk run is already going.'
          : offStyle === 0
            ? 'Every generated image is already in this style.'
            : null
  const save = () => {
    patch.mutate(
      {
        automatic_mortal_agents: false,
        image_style: current.style,
        image_style_custom:
          current.style === 'custom' ? current.custom.trim() : '',
      },
      {
        onSuccess: (result) => {
          setDraft(null)
          toast.success(result.message || 'Image style saved')
          void queryClient.invalidateQueries({ queryKey: imageKeys.all })
        },
        onError: (error) => toast.error(error.message),
      }
    )
  }
  return (
    <Section
      title='Image style'
      description='How every portrait and scene of this world is painted. New images follow it; earlier ones stay until you repaint them.'
      surface='card'
      level={3}
      icon={Palette}
      id='image-style'
      actions={
        <Button
          onClick={save}
          disabled={saveReason !== null || patch.isPending}
          disabledReason={saveReason ?? 'Saving.'}
        >
          <Save />
          Save style
        </Button>
      }
    >
      <div className='flex min-w-0 flex-col gap-4'>
        <div className='flex min-w-0 flex-wrap items-center gap-2'>
          <Muted variant='caption'>Current style</Muted>
          <Badge variant='outline' className='max-w-full'>
            <span className='truncate'>
              {imageStyleLabel(saved.style, saved.custom)}
            </span>
          </Badge>
          {dirty && <Badge variant='warning'>Unsaved change</Badge>}
          <Badge
            variant={settings.data.image_generation ? 'success' : 'secondary'}
          >
            {settings.data.image_generation
              ? 'The image worker is ready'
              : 'The image worker is off; the style waits for it'}
          </Badge>
        </div>
        <ImageStylePicker
          value={current.style}
          custom={current.custom}
          onChange={(style) => setDraft({ ...current, style })}
          onCustomChange={(custom) => setDraft({ ...current, custom })}
        />
        <div className='flex min-w-0 flex-col gap-2 rounded-lg border bg-muted/40 p-3'>
          <Text weight='medium'>
            {offStyle > 0
              ? `${formatInteger(offStyle)} generated images are in another style`
              : 'Every generated image matches the world style'}
          </Text>
          <Muted variant='caption'>
            Repainting paints each of them again from its own prompt in the
            current style and makes the new image the cover. The earlier images
            stay in each gallery; uploaded images are never touched.
          </Muted>
          <Button
            variant='outline'
            className='self-start'
            disabled={restyleReason !== null || restyle.isPending}
            disabledReason={restyleReason ?? 'Working on it.'}
            onClick={() => setConfirming(true)}
          >
            <Brush />
            {`Repaint ${formatInteger(offStyle)} images in this style`}
          </Button>
        </div>
        <ConfirmDialog
          open={confirming}
          onOpenChange={setConfirming}
          title={`Repaint ${formatInteger(offStyle)} images?`}
          desc='The worker paints one image at a time; your own requests still go first. You can stop at any time from Image generation below.'
          confirmText='Repaint'
          isLoading={restyle.isPending}
          handleConfirm={() => {
            setConfirming(false)
            restyle.mutate()
          }}
        />
      </div>
    </Section>
  )
}
