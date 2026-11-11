import {
  CLASS_FUNCTIONS,
  CONTROL_COMPONENTS,
  classViolation,
  tokensOf,
} from './classPolicy.js'

const MESSAGES = {
  arbitrary: 'Arbitrary Tailwind values ("{{token}}") are not allowed here; use a theme token or a component variant.',
  textSize: 'Text size class "{{token}}" is not allowed here; use a typography component.',
  typeTuning: 'Font weight, leading and tracking ("{{token}}") belong to typography components.',
  margin: 'Margin class "{{token}}" is not allowed here; lay out with flex or grid gap.',
  zIndex: 'z-index class "{{token}}" is not allowed here; stacking belongs to the overlay components.',
  controlBox: 'Control box class "{{token}}" restyles a control; pick its size variant instead.',
  numericSize: 'Numeric size "{{token}}" is not allowed here; use size-icon-*, size-control-* or size-portrait-*.',
  tabsWrap: 'A tab bar has a fixed height and scrolls sideways; "{{token}}" would push tabs out of sight.',
}

const TAB_BARS = new Set(['TabsList'])
const TAB_BAR_BREAKERS = /^(?:[a-z0-9-]+:)*(?:flex-wrap|flex-wrap-reverse|flex-col|grid|h-auto|overflow-hidden|overflow-y-auto)$/

function jsxName(node) {
  if (!node) return ''
  if (node.type === 'JSXIdentifier') return node.name
  if (node.type === 'JSXMemberExpression') return jsxName(node.property)
  return ''
}

function calleeName(node) {
  if (node.type === 'Identifier') return node.name
  if (node.type === 'MemberExpression' && node.property.type === 'Identifier')
    return node.property.name
  return ''
}

function stringParts(node, parts) {
  if (!node) return parts
  switch (node.type) {
    case 'Literal':
      if (typeof node.value === 'string') parts.push({ node, text: node.value })
      break
    case 'TemplateLiteral':
      for (const quasi of node.quasis) parts.push({ node: quasi, text: quasi.value.cooked ?? '' })
      for (const expression of node.expressions) stringParts(expression, parts)
      break
    case 'JSXExpressionContainer':
      stringParts(node.expression, parts)
      break
    case 'ConditionalExpression':
      stringParts(node.consequent, parts)
      stringParts(node.alternate, parts)
      break
    case 'LogicalExpression':
      stringParts(node.left, parts)
      stringParts(node.right, parts)
      break
    case 'ArrayExpression':
      for (const element of node.elements) stringParts(element, parts)
      break
    case 'ObjectExpression':
      for (const property of node.properties) {
        if (property.type !== 'Property') continue
        if (property.key.type === 'Literal') stringParts(property.key, parts)
        stringParts(property.value, parts)
      }
      break
    case 'CallExpression':
      if (CLASS_FUNCTIONS.has(calleeName(node.callee)))
        for (const argument of node.arguments) stringParts(argument, parts)
      break
    default:
      break
  }
  return parts
}

function reportClasses(context, valueNode, onControl) {
  for (const part of stringParts(valueNode, [])) {
    for (const token of tokensOf(part.text)) {
      const violation = classViolation(token, onControl)
      if (violation) context.report({ node: part.node, messageId: violation, data: { token } })
    }
  }
}

const classPolicy = {
  meta: { type: 'problem', messages: MESSAGES, schema: [] },
  create(context) {
    return {
      JSXAttribute(node) {
        if (node.name.name !== 'className' || !node.value) return
        const name = jsxName(node.parent.name)
        const onControl = CONTROL_COMPONENTS.has(name)
        reportClasses(context, node.value, onControl)
        if (TAB_BARS.has(name))
          for (const part of stringParts(node.value, []))
            for (const token of tokensOf(part.text))
              if (TAB_BAR_BREAKERS.test(token)) context.report({ node: part.node, messageId: 'tabsWrap', data: { token } })
      },
      CallExpression(node) {
        if (!CLASS_FUNCTIONS.has(calleeName(node.callee))) return
        if (node.parent.type === 'JSXExpressionContainer') return
        for (const argument of node.arguments) reportClasses(context, argument, false)
      },
    }
  },
}

const noInlineStyle = {
  meta: {
    type: 'problem',
    messages: {
      inlineStyle: 'Inline style is only allowed in geometry components (canvas, map, graph, cosmos scenes).',
    },
    schema: [],
  },
  create(context) {
    return {
      JSXAttribute(node) {
        if (node.name.name === 'style') context.report({ node, messageId: 'inlineStyle' })
      },
    }
  },
}

const RAW_COLOR = /#[0-9a-fA-F]{3,8}\b|\b(rgba?|hsla?|oklch|oklab|lab|lch|hwb|color-mix)\(/

const noRawColor = {
  meta: {
    type: 'problem',
    messages: {
      rawColor: 'Raw color "{{value}}" is not allowed here; use a theme token.',
    },
    schema: [],
  },
  create(context) {
    const check = (node, text) => {
      const match = RAW_COLOR.exec(text)
      if (match) context.report({ node, messageId: 'rawColor', data: { value: match[0] } })
    }
    return {
      Literal(node) {
        if (typeof node.value === 'string') check(node, node.value)
      },
      TemplateElement(node) {
        check(node, node.value.cooked ?? '')
      },
      JSXText(node) {
        check(node, node.value)
      },
    }
  },
}

const RAW_ELEMENTS = {
  button: 'Button',
  input: 'Input',
  select: 'Select',
  textarea: 'Textarea',
  h1: 'PageTitle',
  h2: 'SectionTitle',
  h3: 'SectionTitle',
  h4: 'SectionTitle',
  h5: 'SectionTitle',
  h6: 'SectionTitle',
}

const noRawElements = {
  meta: {
    type: 'problem',
    messages: {
      rawElement: 'Use the {{replacement}} component instead of a raw <{{element}}>.',
    },
    schema: [],
  },
  create(context) {
    return {
      JSXOpeningElement(node) {
        const name = jsxName(node.name)
        const replacement = RAW_ELEMENTS[name]
        if (replacement)
          context.report({ node, messageId: 'rawElement', data: { element: name, replacement } })
      },
    }
  },
}

function isFalse(attribute) {
  const value = attribute.value
  return (
    value?.type === 'JSXExpressionContainer' &&
    value.expression.type === 'Literal' &&
    value.expression.value === false
  )
}

const disabledNeedsReason = {
  meta: {
    type: 'problem',
    messages: {
      missingReason: 'A disabled Button needs a disabledReason that tells the player why.',
    },
    schema: [],
  },
  create(context) {
    return {
      JSXOpeningElement(node) {
        if (jsxName(node.name) !== 'Button') return
        const attributes = node.attributes.filter((item) => item.type === 'JSXAttribute')
        const disabled = attributes.find((item) => item.name.name === 'disabled')
        if (!disabled || isFalse(disabled)) return
        if (attributes.some((item) => item.name.name === 'disabledReason')) return
        context.report({ node, messageId: 'missingReason' })
      },
    }
  },
}

const typedRequestBody = {
  meta: {
    type: 'problem',
    messages: {
      untypedBody:
        'A request body cast to never escapes the API types; send it through postAction or give it the schema type of its endpoint.',
    },
    schema: [],
  },
  create(context) {
    return {
      Property(node) {
        if (node.key.type !== 'Identifier' || node.key.name !== 'body') return
        const value = node.value
        if (value.type !== 'TSAsExpression' || value.typeAnnotation.type !== 'TSNeverKeyword') return
        const siblings = node.parent.type === 'ObjectExpression' ? node.parent.properties : []
        if (siblings.some((item) => item.type === 'Property' && item.key.type === 'Identifier' && item.key.name === 'bodySerializer')) return
        context.report({ node, messageId: 'untypedBody' })
      },
    }
  },
}

const SCENE_ELEMENTS = new Set([
  'mesh',
  'points',
  'group',
  'sprite',
  'instancedMesh',
  'line',
  'lineSegments',
  'lineLoop',
  'primitive',
  'Billboard',
  'Line',
  'Points',
  'Instances',
  'Instance',
])

const SCENE_CLICKS = new Set(['onClick', 'onDoubleClick', 'onContextMenu'])

const sceneTap = {
  meta: {
    type: 'problem',
    messages: {
      dragClick:
        'A click on a scene object also fires at the end of a drag; wrap the handler in onTap from @/lib/sceneTap.',
    },
    schema: [],
  },
  create(context) {
    return {
      JSXAttribute(node) {
        if (!SCENE_CLICKS.has(node.name.name)) return
        if (!SCENE_ELEMENTS.has(jsxName(node.parent.name))) return
        const value = node.value
        if (value?.type !== 'JSXExpressionContainer') return
        const tapped = (expression) =>
          (expression.type === 'CallExpression' && calleeName(expression.callee) === 'onTap') ||
          (expression.type === 'Identifier' && expression.name === 'undefined') ||
          (expression.type === 'ConditionalExpression' && tapped(expression.consequent) && tapped(expression.alternate))
        if (tapped(value.expression)) return
        context.report({ node, messageId: 'dragClick' })
      },
    }
  },
}

export const aeronaPlugin = {
  meta: { name: 'aerona' },
  rules: {
    'class-policy': classPolicy,
    'no-inline-style': noInlineStyle,
    'no-raw-color': noRawColor,
    'no-raw-elements': noRawElements,
    'disabled-needs-reason': disabledNeedsReason,
    'typed-request-body': typedRequestBody,
    'scene-tap': sceneTap,
  },
}

export const FEATURE_RULES = {
  'aerona/class-policy': 'error',
  'aerona/no-inline-style': 'error',
  'aerona/no-raw-color': 'error',
  'aerona/no-raw-elements': 'error',
  'aerona/disabled-needs-reason': 'error',
  'aerona/typed-request-body': 'error',
  'aerona/scene-tap': 'error',
}

export const GEOMETRY_FILES = [
  'src/features/{map,cosmos,graph}/**/*{Canvas,Scene,Layer,Marker,Overlay,3D}*.tsx',
  'src/features/{map,cosmos,graph}/**/scene3d/**/*.tsx',
]
