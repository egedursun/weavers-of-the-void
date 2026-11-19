import { ChevronsRight, Hammer } from 'lucide-react'
import type { RecordFamily } from '@/features/entity/sections/recordLevers'

export const PUBLIC_WORKS: RecordFamily = {
  id: 'public_works',
  section: 'section-public_works',
  title: 'Public works',
  description:
    'The public works a realm or town builds on a route, region or town: their kind, labour, stages done, budget, quality, condition and whether they stand, are building or have failed, with each finished stage, its labour, spending and quality; and the state enterprises it runs with their good, form, management, manager, output, revenue and corruption.',
  icon: Hammer,
  tone: 'gold',
  empty:
    'No public works or state enterprises are kept for this thing yet. Realms and towns build works and run enterprises, and routes, regions and towns hold the works built on them; beings, gods, worlds and stars hold none of their own, though a son may bless them.',
  tables: {
    public_works: {
      create: 'public_works:create',
      edit: 'public_works:edit',
      remove: 'public_works:delete',
      step: {
        action: 'public_works:advance',
        label: 'Carry these works a stage further',
        field: 'works_id',
        icon: ChevronsRight,
        ready: (values) =>
          values.status === 'building'
            ? null
            : 'Only works still being built can be carried a stage further',
      },
    },
    public_work_stages: {
      create: 'public_work_stage:create',
      edit: 'public_work_stage:edit',
      remove: 'public_work_stage:delete',
    },
    state_enterprises: {
      create: 'state_enterprise:create',
      edit: 'state_enterprise:edit',
      remove: 'state_enterprise:delete',
    },
  },
}
