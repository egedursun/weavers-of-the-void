import { Link } from '@tanstack/react-router'
import { BrainCircuit, Cpu, ImageIcon, Images } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { IntroNote, MiniStat } from '@/components/domain'
import { MissingImages } from '@/features/gallery/MissingImages'
import { useWorldState } from '@/features/overview/api'
import { useRoleModel } from '@/features/providers/api'
import { BulkImageGenPanel } from './BulkImageGenPanel'
import { ImageGenSettings } from './ImageGenSettings'
import { ImageStyleSettings } from './ImageStyleSettings'

export function ImagesSettingsPage() {
  const state = useWorldState()
  const model = useRoleModel('images') ?? ''
  const configured = model !== ''
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
          label='Image model'
          value={configured ? model : 'No model set'}
          tone={configured ? 'success' : 'warning'}
          hint={
            configured
              ? 'The first model of the image chain paints; the next ones step in when it cannot'
              : 'Add one under Team and workspace, Models'
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
      <div className='flex min-w-0 flex-wrap gap-2'>
        <Button variant='outline' asChild>
          <Link to='/gallery'>
            <Images />
            Open the gallery
          </Link>
        </Button>
        <Button variant='outline' asChild>
          <Link to='/workspace' search={{ part: 'providers' }}>
            <BrainCircuit />
            Choose the image model
          </Link>
        </Button>
      </div>
    </div>
  )
}
