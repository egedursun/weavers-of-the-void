import {
  Ban,
  Brush,
  CloudSun,
  Crown,
  Drama,
  Flower2,
  Gem,
  Hammer,
  Heart,
  HeartCrack,
  Landmark,
  Leaf,
  Mountain,
  Palette,
  PawPrint,
  Scale,
  Shapes,
  Sparkles,
  Sun,
  ThumbsDown,
  ThumbsUp,
  Utensils,
  Wine,
} from 'lucide-react'
import { type Named } from '../environment/labels'

export const TASTES_ICON = Heart
export const ETHICS_ICON = Scale

export const PREFERENCE_KINDS: Record<string, Named> = {
  material: { label: 'Material', icon: Gem, tone: 'gold' },
  food: { label: 'Food', icon: Utensils, tone: 'success' },
  drink: { label: 'Drink', icon: Wine, tone: 'info' },
  creature: { label: 'Creature', icon: PawPrint, tone: 'verdigris' },
  plant: { label: 'Plant', icon: Leaf, tone: 'success' },
  colour: { label: 'Colour', icon: Palette, tone: 'gold' },
  shape: { label: 'Shape', icon: Shapes, tone: 'info' },
  art_form: { label: 'Art form', icon: Brush, tone: 'gold' },
  artwork_subject: { label: 'Subject of art', icon: Drama, tone: 'verdigris' },
  season: { label: 'Time of year', icon: Sun, tone: 'warning' },
  weather: { label: 'Weather', icon: CloudSun, tone: 'info' },
  terrain: { label: 'Land', icon: Mountain, tone: 'muted' },
  activity: { label: 'Pastime', icon: Flower2, tone: 'success' },
  craft: { label: 'Craft', icon: Hammer, tone: 'warning' },
  deity_aspect: { label: 'Aspect of the divine', icon: Sparkles, tone: 'gold' },
}

export const STANCES: Record<string, Named> = {
  required: { label: 'Required', icon: Crown, tone: 'gold' },
  admirable: { label: 'Admirable', icon: ThumbsUp, tone: 'success' },
  acceptable: { label: 'Acceptable', icon: Scale, tone: 'muted' },
  frowned_upon: { label: 'Frowned upon', icon: ThumbsDown, tone: 'warning' },
  shameful: { label: 'Shameful', icon: HeartCrack, tone: 'danger' },
  unthinkable: { label: 'Unthinkable', icon: Ban, tone: 'danger' },
}

export const HONOUR_ICON = Landmark
