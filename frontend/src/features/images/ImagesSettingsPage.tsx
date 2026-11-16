import { Link } from '@tanstack/react-router'
import { Cpu, ImageIcon, Images } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { IntroNote, MiniStat } from '@/components/domain'
import { MissingImages } from '@/features/gallery/MissingImages'
import { useWorldState } from '@/features/overview/api'
import { BulkImageGenPanel } from './BulkImageGenPanel'
import { ImageGenSettings } from './ImageGenSettings'
import { ImageStyleSettings } from './ImageStyleSettings'
import { useHealth } from './api'

export function ImagesSettingsPage() {
  const health = useHealth()
  const state = useWorldState()
  const configured = health.data?.image_worker_configured ?? false
  return (
    <div className='flex min-w-0 flex-col gap-6'>
      <IntroNote>
        Choose how the world is painted, paint every record that still has no
        image, watch the queue and see which records are missing one. New
        records are also painted by themselves at the end of every epoch.
      </IntroNote>
      <div className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-3'>
        <MiniStat
          icon={Cpu}
          label='Image worker'
          value={configured ? 'Connected' : 'Not configured'}
          tone={configured ? 'success' : 'warning'}
          hint={
            configured
              ? 'Images are painted by the worker'
              : 'Run make worker-start or set AERONA_IMAGE_WORKER_URL'
          }
        />
        <MiniStat
          icon={ImageIcon}
          label='Images in the world'
          value={state.data?.image_count ?? 0}
          tone='gold'
        />
        <MiniStat
          icon={Images}
          label='Records without an image prompt'
          value={state.data?.promptless_count ?? 0}
          tone='muted'
        />
      </div>
      <ImageStyleSettings />
      <ImageGenSettings />
      <BulkImageGenPanel />
      <MissingImages type={null} />
      <Button variant='outline' asChild className='self-start'>
        <Link to='/gallery'>
          <Images />
          Open the gallery
        </Link>
      </Button>
    </div>
  )
}
