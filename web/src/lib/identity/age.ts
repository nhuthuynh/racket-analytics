// Identity context, FR-003 age gate (ST-068b; api-sprint-04 §4; OQ-05 accepted, ADR 0023).
// The web never decides who is admitted: the API gates every route until the answer. Texts are
// the PM-4 interim register (docs/requirements/interim-wording-sprint-04.md W-A01..W-A09,
// pending legal review P16); the minimum age is AGE_MINIMUM=18 (api-sprint-04 §11).
export const AGE_MINIMUM = 18;
export const AGE_QUESTION_PATH = '/welcome/age';

/** What the API did with an answer: an adult, a refused pending sign-in, or an existing account. */
export type AgeOutcome = 'adult' | 'under_age' | 'confirmation_required';

export const AGE_WORDING = {
  question: `Are you ${AGE_MINIMUM} or over?`, // W-A01
  hint: `You need to be ${AGE_MINIMUM} or over to have an account. We do not store your birth date.`, // W-A02
  yes: `Yes, I am ${AGE_MINIMUM} or over`, // W-A03
  no: `No, I am under ${AGE_MINIMUM}`, // W-A04
  nothingChosen: 'Choose yes or no', // W-A05
  underHeading: "You can't have an account yet", // W-A06
  underWhy: `You need to be ${AGE_MINIMUM} or over to use this app.`, // W-A07, first sentence
  noAccountMade: 'We did not make an account for you.', // W-A07, pending sign-in only
  underInstead: `You are welcome to come back when you turn ${AGE_MINIMUM}.`, // W-A08
  footage: `Don't upload matches with anyone under ${AGE_MINIMUM}. Film only people who agree to be filmed.`, // W-A09
} as const;
