// NFR-050.8 (ST-078e; G05-07 `npm run test -- hydration-lock`): no form with a submit handler can
// be sent before hydration. In the server HTML React has not attached onSubmit yet, so a tap on an
// enabled submit button (or Enter in a lone text field) is a native GET submit: the answers land
// in the URL [AQS/SEC-05] and nothing the page means to do happens (CI-SIGNIN-HYDRATION, PR #105).
// One test per form, plus an inventory check: a new `onSubmit=` file must be added here.
import { readFileSync, readdirSync, statSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { render, screen, waitFor } from '@testing-library/react';
import type { ReactElement } from 'react';
import { renderToString } from 'react-dom/server';
import { describe, expect, it, vi } from 'vitest';
import { MatchSetup } from '@/components/MatchSetup';
import { SignInForm } from '@/components/SignInForm';
import { AgeQuestion } from '@/components/age/AgeQuestion';
import { PlanPreferences } from '@/components/plan/PlanPreferences';
import { PrivacySettings } from '@/components/settings/PrivacySettings';
import type { PrivacySettingsApi } from '@/components/settings/PrivacySettingsApi';
import { GameStartForm } from '@/components/tagging/GameStartForm';
import { FALLBACK_UPLOAD_POLICY } from '@/lib/api/types';

const SRC = path.join(path.dirname(fileURLToPath(import.meta.url)), '../../src');
const TEXT_TYPES = new Set(['', 'text', 'email', 'search', 'tel', 'url', 'password', 'number', 'date']);

function disabled(el: Element): boolean {
  return (el as HTMLButtonElement).disabled || el.closest('fieldset[disabled]') !== null;
}

/** Why the form could be sent natively, or null when it cannot. */
function nativeSubmitter(form: HTMLFormElement): string | null {
  const submitters = [...form.querySelectorAll('button, input[type="submit"], input[type="image"]')].filter(
    (el) => el.tagName !== 'BUTTON' || (el.getAttribute('type') ?? 'submit') === 'submit',
  );
  const open = submitters.find((el) => !disabled(el));
  if (open) return `enabled submit "${open.textContent?.trim() || open.getAttribute('value') || ''}"`;
  if (submitters.length > 0) return null; // implicit submission needs an enabled default button
  const fields = [...form.querySelectorAll('input')].filter((i) => TEXT_TYPES.has(i.getAttribute('type') ?? '') && !disabled(i));
  return fields.length === 1 ? 'implicit submit from its only text field' : null;
}

function serverForms(element: ReactElement): HTMLFormElement[] {
  const doc = new DOMParser().parseFromString(`<body>${renderToString(element)}</body>`, 'text/html');
  return [...doc.querySelectorAll('form')];
}

function expectLockedBeforeHydration(element: ReactElement, { forms = 1 } = {}) {
  const found = serverForms(element);
  expect(found).toHaveLength(forms);
  expect(found.map(nativeSubmitter)).toEqual(found.map(() => null));
}

const privacyApi = (): PrivacySettingsApi => ({
  retention: vi.fn(async () => ({ kind: 'ok' as const, value: { days: 90, choices: [30, 90, 365, null] } })),
  saveRetention: vi.fn(async (days) => ({ kind: 'ok' as const, value: { days, choices: [30, 90, 365, null] } })),
  reviewVideos: vi.fn(async () => ({ kind: 'ok' as const, value: [] })),
  consent: vi.fn(async () => ({ kind: 'ok' as const, value: { optIn: false } })),
  saveConsent: vi.fn(async (optIn) => ({ kind: 'ok' as const, value: { optIn } })),
});

const FORMS = {
  'components/SignInForm.tsx': () => <SignInForm api={{ requestLink: vi.fn() }} />,
  'components/age/AgeQuestion.tsx': () => <AgeQuestion api={{ confirmAge: vi.fn(), requestLink: vi.fn() }} navigate={vi.fn()} />,
  'components/plan/PlanPreferences.tsx': () => <PlanPreferences initial={null} api={{ generatePlan: vi.fn() }} navigate={vi.fn()} />,
  'components/tagging/GameStartForm.tsx': () => <GameStartForm game={1} mySide="A" label={(s) => `Side ${s}`} onStart={vi.fn()} />,
  'components/MatchSetup.tsx': () => <MatchSetup api={{ createMatch: vi.fn() }} policy={FALLBACK_UPLOAD_POLICY} navigate={vi.fn()} />,
  'components/settings/PrivacySettings.tsx': () => <PrivacySettings features={{ retention: true, consent: true }} api={privacyApi()} onSignedOut={vi.fn()} />,
} as const;

function sourceFiles(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const full = path.join(dir, name);
    if (statSync(full).isDirectory()) return sourceFiles(full);
    return /\.tsx$/.test(name) ? [full] : [];
  });
}

describe('hydration lock: no form can be sent before hydration (NFR-050.8)', () => {
  it('the checker finds an enabled submit button and a lone text field (negative controls)', () => {
    const [open] = serverForms(<form onSubmit={() => undefined}><button type="submit">Go</button></form>);
    const [lone] = serverForms(<form onSubmit={() => undefined}><input name="q" /></form>);
    const [locked] = serverForms(<form onSubmit={() => undefined}><fieldset disabled><button>Go</button></fieldset></form>);
    expect(nativeSubmitter(open!)).toBe('enabled submit "Go"');
    expect(nativeSubmitter(lone!)).toBe('implicit submit from its only text field');
    expect(nativeSubmitter(locked!)).toBeNull();
  });

  it('every source file with an onSubmit form is covered here', () => {
    const withForms = sourceFiles(SRC)
      .filter((file) => /onSubmit=/.test(readFileSync(file, 'utf8')))
      .map((file) => path.relative(SRC, file).split(path.sep).join('/'))
      .sort();
    expect(withForms).toEqual(Object.keys(FORMS).sort());
  });

  it('SignInForm (A-01): locked in the server HTML, sendable once mounted', () => {
    expectLockedBeforeHydration(FORMS['components/SignInForm.tsx']());
    render(FORMS['components/SignInForm.tsx']());
    expect(screen.getByRole('button', { name: 'Send me a link' })).toBeEnabled();
  });

  it('AgeQuestion (A-06): locked in the server HTML, sendable once mounted', () => {
    expectLockedBeforeHydration(FORMS['components/age/AgeQuestion.tsx']());
    render(FORMS['components/age/AgeQuestion.tsx']());
    expect(screen.getByRole('button', { name: 'Continue' })).toBeEnabled();
  });

  it('PlanPreferences (P-02): locked in the server HTML, sendable once mounted', () => {
    expectLockedBeforeHydration(FORMS['components/plan/PlanPreferences.tsx']());
    render(FORMS['components/plan/PlanPreferences.tsx']());
    expect(screen.getByRole('button', { name: /plan/i })).toBeEnabled();
  });

  it('GameStartForm: locked in the server HTML, sendable once mounted', () => {
    expectLockedBeforeHydration(FORMS['components/tagging/GameStartForm.tsx']());
    render(FORMS['components/tagging/GameStartForm.tsx']());
    expect(screen.getByRole('button', { name: 'Start game 1' })).toBeEnabled();
  });

  it('MatchSetup (U-01): locked in the server HTML, sendable once mounted', () => {
    expectLockedBeforeHydration(FORMS['components/MatchSetup.tsx']());
    render(FORMS['components/MatchSetup.tsx']());
    expect(screen.getByRole('button', { name: 'Continue' })).toBeEnabled();
  });

  it('PrivacySettings (R-01): no form in the server HTML (loading), both forms sendable once loaded', async () => {
    expectLockedBeforeHydration(FORMS['components/settings/PrivacySettings.tsx'](), { forms: 0 });
    render(FORMS['components/settings/PrivacySettings.tsx']());
    await waitFor(() => expect(screen.getAllByRole('button', { name: /save/i })).toHaveLength(2));
    for (const button of screen.getAllByRole('button', { name: /save/i })) expect(button).toBeEnabled();
  });
});
