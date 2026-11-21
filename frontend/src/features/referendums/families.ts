import { CheckSquare, Vote } from 'lucide-react'
import type { RecordFamily } from '@/features/entity/sections/recordLevers'

export const REFERENDUMS: RecordFamily = {
  id: 'referendums',
  section: 'section-referendums',
  title: 'Votes',
  description:
    'Questions put to the people rather than a person: what was asked about whom or what, who called the vote and by which right, the franchise it was open to, whether it binds and its threshold, what each side spent, the fraud that bent it, the turnout, the share for it, how it ended and whether its rulers ignored it.',
  icon: Vote,
  tone: 'info',
  empty:
    'No question has been put to the people here. A realm, a town or a league whose law lets some body vote can hold one; a realm without any franchise has no one to ask, and the subjects of each vote and those who called it see it here too.',
  tables: {
    referendums: {
      create: 'referendum:create',
      edit: 'referendum:edit',
      remove: 'referendum:delete',
      step: {
        action: 'referendum:decide',
        label: 'Decide this vote',
        field: 'record_id',
        icon: CheckSquare,
        ready: (values) =>
          String(values.result) === 'pending'
            ? null
            : 'Only a vote still to be held can be decided',
      },
    },
  },
}
