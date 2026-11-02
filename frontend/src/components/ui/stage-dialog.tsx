import * as React from 'react'
import * as DialogPrimitive from '@radix-ui/react-dialog'
import { cn } from '@/lib/utils'

function StageDialog(props: React.ComponentProps<typeof DialogPrimitive.Root>) {
  return <DialogPrimitive.Root data-slot='stage-dialog' {...props} />
}

function StageDialogContent({
  className,
  children,
  ...props
}: React.ComponentProps<typeof DialogPrimitive.Content>) {
  return (
    <DialogPrimitive.Portal>
      <DialogPrimitive.Overlay className='fixed inset-0 z-50 bg-black/80 backdrop-blur-sm data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:animate-in data-[state=open]:fade-in-0' />
      <DialogPrimitive.Content
        data-slot='stage-dialog-content'
        className={cn(
          'fixed inset-0 z-50 flex flex-col items-center justify-center overflow-x-hidden overflow-y-auto p-4 outline-none data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:animate-in data-[state=open]:fade-in-0',
          className
        )}
        {...props}
      >
        {children}
      </DialogPrimitive.Content>
    </DialogPrimitive.Portal>
  )
}

const StageDialogTitle = DialogPrimitive.Title
const StageDialogDescription = DialogPrimitive.Description

export {
  StageDialog,
  StageDialogContent,
  StageDialogDescription,
  StageDialogTitle,
}
