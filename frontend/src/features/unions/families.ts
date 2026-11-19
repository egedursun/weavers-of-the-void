import { HeartHandshake } from 'lucide-react'
import type { RecordFamily } from '@/features/entity/sections/recordLevers'

export const UNIONS_AND_BIRTH: RecordFamily = {
  id: 'unions_and_birth',
  section: 'section-unions_and_birth',
  title: 'Unions and birth',
  description:
    'How a people holds relations in each context, who enforces its norms and by what sanction; its customs of restraint by role and occasion; the course of pregnancy and birth with its risk, attendants, place and the care after it; the standing of a child by its parents’ union and the way to change it; and the children it has recognised.',
  icon: HeartHandshake,
  tone: 'gold',
  empty:
    'Nothing of unions or birth is kept for this thing yet. Peoples hold norms, customs of restraint, the course of birth and rules of standing, and beings hold their recognition; gods, worlds and stars are not bound by the norms of a people.',
  tables: {
    intimacy_norms: {
      create: 'intimacy_norm:create',
      edit: 'intimacy_norm:edit',
      remove: 'intimacy_norm:delete',
    },
    restraint_customs: {
      create: 'restraint_custom:create',
      edit: 'restraint_custom:edit',
      remove: 'restraint_custom:delete',
    },
    reproductive_courses: {
      create: 'reproductive_course:create',
      edit: 'reproductive_course:edit',
      remove: 'reproductive_course:delete',
    },
    legitimacy_rules: {
      create: 'legitimacy_rule:create',
      edit: 'legitimacy_rule:edit',
      remove: 'legitimacy_rule:delete',
    },
    child_recognitions: {
      create: 'child_recognition:create',
      edit: 'child_recognition:edit',
      remove: 'child_recognition:delete',
    },
  },
}
