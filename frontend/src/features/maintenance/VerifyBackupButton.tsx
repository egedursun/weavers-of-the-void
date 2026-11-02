import { ShieldCheck } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { useVerifyBackup } from './api'

export function VerifyBackupButton({ file }: { file: string }) {
  const verify = useVerifyBackup()
  return (
    <Button
      variant='outline'
      size='sm'
      disabled={verify.isPending}
      disabledReason='Checking the backup.'
      aria-busy={verify.isPending || undefined}
      title='Open the backup and check that it is a sound world database'
      onClick={() =>
        verify.mutate(file, {
          onSuccess: (result) =>
            toast.success(`${result.file} is sound and can be restored.`),
          onError: (error) => toast.error(error.message),
        })
      }
    >
      <ShieldCheck />
      Verify
    </Button>
  )
}
