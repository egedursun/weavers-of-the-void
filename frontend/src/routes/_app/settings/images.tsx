import { createFileRoute } from '@tanstack/react-router'
import { ImagesSettingsPage } from '@/features/images/ImagesSettingsPage'

export const Route = createFileRoute('/_app/settings/images')({
  component: ImagesSettingsPage,
})
