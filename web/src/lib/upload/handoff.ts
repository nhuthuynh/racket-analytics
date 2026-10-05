// Hands the File chosen on Q-06 to the match page after "Create match and upload" (ST-016 →
// ST-017). In memory only: a File cannot be stored, and nothing about it is written to browser
// storage [AQS/SEC-05]. Taken once.
const pending = new Map<string, File>();

export function handOff(matchId: string, file: File): void {
  pending.clear();
  pending.set(matchId, file);
}

export function takeHandOff(matchId: string): File | null {
  const file = pending.get(matchId) ?? null;
  pending.delete(matchId);
  return file;
}
