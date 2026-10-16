// The rally clock (FR-050; MVP-02): where "Rally start" and "Rally end" take their times from.
// With a video that plays, the video's own time, so a rally can be found again in the video.
// When the video cannot play here (no link, a media error, a codec this browser cannot decode)
// its time does not move, so the page clock is used instead, carried on from the end of the last
// tagged rally: every mark is then at or after the last rally's end and later marks are later,
// as the tagging rules require (taggingReducer: a rally cannot start before the last one ended).
// Page-clock marks never pass the video's duration (PE-MVP02-R1-01), as the scorebook refuses a
// rally that ends after the video (I-within, time_after_video): the page clock is followed until
// the last END_RESERVE_MS of the video, then each mark is 1 ms after the one before, and when no
// time is left before the end of the video for a rally there is no mark (null).
// Framework-free: the page clock is passed in.

/** The match video as the rally clock sees it: whether it plays here, and its time in ms. */
export interface VideoTime {
  plays: boolean;
  videoMs: number;
}

/** The end of the video kept for page-clock marks once the page clock gets there (about 5,000 rallies). */
export const END_RESERVE_MS = 10_000;

export class RallyClock {
  /** Added to the page clock so its times carry on from the last tagged rally's end. */
  private offsetMs = 0;
  /** The last page-clock mark given, so marks squeezed into the reserve still go forward. */
  private lastMarkMs = -1;

  constructor(private readonly pageNowMs: () => number) {}

  /**
   * The time in ms for the next mark, given the video (null: none), the last rally's end and
   * the video's duration (null: not known, no upper bound). Null: no time is left before the
   * end of the video for another page-clock mark.
   */
  read(video: VideoTime | null, lastEndMs: number | null): number;
  read(video: VideoTime | null, lastEndMs: number | null, durationMs: number | null): number | null;
  read(video: VideoTime | null, lastEndMs: number | null, durationMs: number | null = null): number | null {
    if (video?.plays) return Math.floor(video.videoMs);
    const page = Math.floor(this.pageNowMs());
    if (lastEndMs !== null) this.offsetMs = Math.max(this.offsetMs, lastEndMs - page);
    let ms = page + this.offsetMs;
    if (durationMs !== null) {
      const reserveFrom = Math.max(0, durationMs - END_RESERVE_MS);
      if (ms > reserveFrom) ms = Math.max(reserveFrom, this.lastMarkMs + 1, lastEndMs ?? 0);
      if (ms >= durationMs) return null; // a mark at the very end leaves no room for the rally's end
    }
    this.lastMarkMs = Math.max(this.lastMarkMs, ms);
    return ms;
  }
}
