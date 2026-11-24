import { Hammer } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Label } from '@/components/typography'
import { LoreForge } from '@/features/entity/lore/forge/LoreForge'
import {
  FORGE_KIND,
  FORGE_KINDS,
} from '@/features/entity/lore/forge/forgeModel'
import {
  CreateBeastDialog,
  CreateSpeciesDialog,
} from '@/features/entity/wilds/CreateWilds'
import {
  FoundSettlementDialog,
  RaiseRegionDialog,
  ShapeMortalDialog,
  ShapeRecordDialog,
  ShapeSonDialog,
  SummonOuterBeingDialog,
} from './ShapeDialogs'

export function CreateHub() {
  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button variant='outline' size='sm' data-surface='CreateHub'>
          <Hammer />
          Create
        </Button>
      </DialogTrigger>
      <DialogContent className='sm:max-w-2xl'>
        <DialogHeader>
          <DialogTitle>Create with your own hand</DialogTitle>
          <DialogDescription>
            Shape beings, lands, powers, creatures and lore; every value can be
            set before it enters the world.
          </DialogDescription>
        </DialogHeader>
        <div className='flex min-w-0 flex-col gap-4'>
          <div className='flex min-w-0 flex-col gap-2'>
            <Label variant='overline'>Beings</Label>
            <div className='flex min-w-0 flex-wrap gap-2'>
              <ShapeMortalDialog />
              <ShapeSonDialog />
              <ShapeRecordDialog kind='spirit' />
              <SummonOuterBeingDialog />
            </div>
          </div>
          <div className='flex min-w-0 flex-col gap-2'>
            <Label variant='overline'>Lands</Label>
            <div className='flex min-w-0 flex-wrap gap-2'>
              <RaiseRegionDialog />
              <FoundSettlementDialog />
            </div>
          </div>
          <div className='flex min-w-0 flex-col gap-2'>
            <Label variant='overline'>Heavens and powers</Label>
            <div className='flex min-w-0 flex-wrap gap-2'>
              <ShapeRecordDialog kind='celestial' />
              <ShapeRecordDialog kind='natural_law' />
              <ShapeRecordDialog kind='cult' />
            </div>
          </div>
          <div className='flex min-w-0 flex-col gap-2'>
            <Label variant='overline'>Wilds</Label>
            <div className='flex min-w-0 flex-wrap gap-2'>
              <CreateSpeciesDialog />
              <CreateBeastDialog />
            </div>
          </div>
          <div className='flex min-w-0 flex-col gap-2'>
            <Label variant='overline'>Lore</Label>
            <div className='flex min-w-0 flex-wrap gap-2'>
              {FORGE_KINDS.map((kind) => (
                <LoreForge
                  key={kind}
                  kind={kind}
                  triggerLabel={FORGE_KIND[kind].label}
                />
              ))}
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
