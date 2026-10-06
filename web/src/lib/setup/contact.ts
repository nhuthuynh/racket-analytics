// "Looks like contact details" (ST-016; api-sprint-01 §5.4, shared with the domain rule
// `Participants.looks_like_contact_details`). A warning only: the nickname is still accepted.
const EMAIL = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

export function looksLikeContactDetails(nickname: string): boolean {
  const value = nickname.trim();
  if (EMAIL.test(value)) return true;
  // Phone: 7 or more digits in a row once spaces, '-', '.', '(', ')' and a leading '+' go.
  const compact = value.replace(/^\+/, '').replace(/[\s\-.()]/g, '');
  return /\d{7,}/.test(compact);
}
