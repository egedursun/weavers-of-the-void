import globals from 'globals'
import js from '@eslint/js'
import pluginQuery from '@tanstack/eslint-plugin-query'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import { defineConfig } from 'eslint/config'
import tseslint from 'typescript-eslint'
import {
  FEATURE_RULES,
  GEOMETRY_FILES,
  aeronaPlugin,
} from './eslint/aeronaPlugin.js'

export default defineConfig(
  { ignores: ['dist', 'src/components/ui', 'e2e/screenshots', 'e2e/.results'] },
  {
    extends: [
      js.configs.recommended,
      ...tseslint.configs.recommended,
      ...pluginQuery.configs['flat/recommended'],
    ],
    files: ['**/*.{ts,tsx}'],
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
    },
    plugins: {
      'react-hooks': reactHooks,
      'react-refresh': reactRefresh,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      'react-refresh/only-export-components': [
        'warn',
        { allowConstantExport: true, allowExportNames: ['Route'] },
      ],
      'no-console': 'error',
      'no-unused-vars': 'off',
      '@typescript-eslint/no-unused-vars': [
        'error',
        {
          args: 'all',
          argsIgnorePattern: '^_',
          caughtErrors: 'all',
          caughtErrorsIgnorePattern: '^_',
          destructuredArrayIgnorePattern: '^_',
          varsIgnorePattern: '^_',
          ignoreRestSiblings: true,
        },
      ],

      '@typescript-eslint/consistent-type-imports': [
        'error',
        {
          prefer: 'type-imports',
          fixStyle: 'inline-type-imports',
          disallowTypeAnnotations: false,
        },
      ],

      'no-duplicate-imports': 'error',
      'no-warning-comments': 'error',
      'no-inline-comments': 'error',
      'multiline-comment-style': 'off',
    },
  },
  {
    files: ['**/*.d.ts'],
    rules: {
      '@typescript-eslint/no-unused-vars': 'off',
    },
  },
  {
    files: ['src/features/**/*.{ts,tsx}', 'src/routes/**/*.{ts,tsx}'],
    plugins: { aerona: aeronaPlugin },
    rules: FEATURE_RULES,
  },
  {
    files: GEOMETRY_FILES,
    rules: { 'aerona/no-inline-style': 'off' },
  },
  {
    files: [
      'eslint/**/*.js',
      'scripts/**/*.mjs',
      'e2e/**/*.ts',
      'playwright.config.ts',
    ],
    languageOptions: { globals: globals.node },
  }
)
