import { useActionCatalogue } from '@/features/command-palette/api'

export function useActionTitle(actionId: string): string {
  const catalogue = useActionCatalogue(actionId !== '')
  if (!actionId) return ''
  return catalogue.data?.find((action) => action.id === actionId)?.title ?? ''
}
