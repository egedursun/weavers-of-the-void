import { type ComponentType, Suspense, useRef } from 'react'
import { ArrowLeft, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { FrameCorners } from '@/components/ui/ornate'
import {
  Sheet,
  SheetClose,
  SheetContent,
  SheetDescription,
  SheetTitle,
} from '@/components/ui/sheet'
import { Skeleton } from '@/components/ui/skeleton'
import { DRAWER_KIND_ICON, Medallion } from '@/components/domain'
import { Label } from '@/components/typography'
import {
  DRAWER_KIND_LABEL,
  type DrawerKind,
  serializeEntry,
} from './drawerEntries'
import { useDrawerStack } from './useDrawerStack'

export type DrawerPageProps = {
  id?: string
}

export type DrawerPages = Record<DrawerKind, ComponentType<DrawerPageProps>>

function DrawerFallback() {
  return (
    <div className='flex flex-col gap-4'>
      <Skeleton className='h-control-lg w-2/3' />
      <Skeleton className='h-textarea w-full' />
    </div>
  )
}

export function DrawerStack({ pages }: { pages: DrawerPages }) {
  const { entries, top, back, close } = useDrawerStack()
  const Page = top ? pages[top.kind] : null
  const depth = entries.length
  const bodyRef = useRef<HTMLDivElement>(null)
  return (
    <Sheet open={top !== undefined} onOpenChange={(open) => !open && close()}>
      <SheetContent
        side='right'
        showCloseButton={false}
        data-layout='drawer'
        className='w-full gap-0 p-0 sm:max-w-drawer'
        onOpenAutoFocus={(event) => {
          event.preventDefault()
          bodyRef.current?.focus()
        }}
      >
        <FrameCorners frame='rail' />
        <div
          data-layout='drawer-header'
          className='relative flex h-topbar shrink-0 items-center gap-3 px-3'
        >
          {depth > 1 && (
            <Button
              variant='ghost'
              size='icon'
              aria-label='Back'
              onClick={back}
            >
              <ArrowLeft />
            </Button>
          )}
          {top && (
            <Medallion
              icon={DRAWER_KIND_ICON[top.kind]}
              tone='gold'
              size='sm'
            />
          )}
          <div className='flex min-w-0 flex-1 flex-col'>
            <SheetTitle className='min-w-0 truncate text-gilded'>
              {top ? DRAWER_KIND_LABEL[top.kind] : ''}
            </SheetTitle>
            <SheetDescription className='sr-only'>
              Record page opened from the current screen
            </SheetDescription>
          </div>
          {depth > 1 && <Label>{`${depth} open`}</Label>}
          <SheetClose asChild>
            <Button variant='ghost' size='icon' aria-label='Close'>
              <X />
            </Button>
          </SheetClose>
        </div>
        <div
          ref={bodyRef}
          tabIndex={-1}
          className='min-h-0 flex-1 overflow-y-auto outline-none'
        >
          <div className='flex min-w-0 flex-col gap-6 p-4 md:p-6'>
            {top && Page && (
              <Suspense fallback={<DrawerFallback />}>
                <Page key={serializeEntry(top)} id={top.id} />
              </Suspense>
            )}
          </div>
        </div>
      </SheetContent>
    </Sheet>
  )
}
