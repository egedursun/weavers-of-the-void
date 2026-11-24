import { DoorOpen } from 'lucide-react'
import type { RecordFamily } from '@/features/entity/sections/recordLevers'

export const DEPARTURES: RecordFamily = {
  id: 'departures',
  section: 'section-departures',
  title: 'Leaving office',
  description:
    'Offices left by choice: who left which office of a realm or the headship of which organisation, by abdication, retirement, resignation, withdrawal to religion or exile, in whose favour, on which conditions, after how many years, the standing they keep and whether they came back.',
  icon: DoorOpen,
  tone: 'warning',
  empty:
    'No one has left an office here by choice. Rulers, officials and heads of organisations of any kind leave by abdication, retirement, resignation, withdrawal or exile, and their leavings show in their own entry, the realm or organisation they left and the one they handed it to. The offices of sons over domains follow divine rules and are not left this way.',
  tables: {
    departures: {
      create: 'departure:create',
      edit: 'departure:edit',
      remove: 'departure:delete',
    },
  },
}
