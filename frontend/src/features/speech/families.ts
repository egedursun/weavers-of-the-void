import { MessageSquareQuote } from 'lucide-react'
import type { RecordFamily } from '@/features/entity/sections/recordLevers'

export const SPEECH: RecordFamily = {
  id: 'speech',
  section: 'section-speech',
  title: 'Humour and speech',
  description:
    'The humour of a people with its form, whom it may mock and whom not, where offence begins and how direct and silent its conversation is; and the speeches given in a town with their speaker, venue, aim, audience, skill, reach and effect.',
  icon: MessageSquareQuote,
  tone: 'gold',
  empty:
    'Nothing of humour or speech is kept for this thing yet. Peoples hold their humour, towns hear speeches and beings give them; gods, worlds and stars may be spoken of though they hold no humour of a people.',
  tables: {
    humour_styles: {
      create: 'humour_style:create',
      edit: 'humour_style:edit',
      remove: 'humour_style:delete',
    },
    speeches: {
      create: 'speech:create',
      edit: 'speech:edit',
      remove: 'speech:delete',
    },
  },
}
