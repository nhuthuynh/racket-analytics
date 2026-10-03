// ESLint flat config (ST-002 gate: `eslint --max-warnings=0 .`).
import { dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { FlatCompat } from '@eslint/eslintrc';

const compat = new FlatCompat({ baseDirectory: dirname(fileURLToPath(import.meta.url)) });

const config = [
  {
    ignores: [
      '.next/**',
      'node_modules/**',
      'coverage/**',
      'playwright-report/**',
      'test-results/**',
      'next-env.d.ts',
    ],
  },
  ...compat.extends('next/core-web-vitals', 'next/typescript'),
  {
    rules: {
      // Titles and user text are rendered as text only (api-sprint-00 §8; ASVS 3.2.2).
      'react/no-danger': 'error',
      'no-restricted-syntax': [
        'error',
        {
          selector: "MemberExpression[property.name='innerHTML']",
          message: 'Render text with React, never innerHTML (ASVS 3.2.2).',
        },
      ],
    },
  },
  {
    // The domain-free formatting and upload-state modules must not import React or Next.
    files: ['src/lib/format.ts', 'src/lib/upload/progress.ts'],
    rules: {
      'no-restricted-imports': ['error', { patterns: ['react', 'react-*', 'next', 'next/*'] }],
    },
  },
];

export default config;
