import { Languages } from 'lucide-react'
import type { RecordFamily } from '@/features/entity/sections/recordLevers'

export const INTERPRETATION: RecordFamily = {
  id: 'interpretation',
  section: 'section-interpretation',
  title: 'Words between tongues',
  description:
    'Exchanges carried by an interpreter between sides who share no tongue: the treaty, sermon, trial, trade or parley, its two sides and their tongues, who carried it and how faithfully, the error it carried if any and the side a slant favoured, and whether the error has come to light.',
  icon: Languages,
  tone: 'info',
  empty:
    'No exchange here was carried between tongues. Sides who share no tongue speak through those skilled in both, and the sides, the interpreter and the treaty or sermon itself each see what was carried.',
  tables: {
    interpretations: {
      create: 'interpretation:create',
      edit: 'interpretation:edit',
      remove: 'interpretation:delete',
    },
  },
}
