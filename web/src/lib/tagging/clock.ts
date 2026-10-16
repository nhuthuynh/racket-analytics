// The rally clock (FR-050; MVP-02): where "Rally start" and "Rally end" take their times from.
// With a video that plays, the video's own time, so a rally can be found again in the video.
// When the video cannot play here (no link, a media error, a codec this browser cannot decode)
// its time does not move, so the page clock is used instead, carried on from the end of the last
// tagged rally: every mark is then at or after the last rally's end and later marks are later,
// as the tagging rules require (taggingReducer: a rally cannot start before the last one ended).
// Framework-free: the page clock is passed in.

/** The match video as the rally clock sees it: whether it plays here, and its time in ms. */
export interface VideoTime {
  plays: boolean;
  videoMs: number;
}

export class RallyClock {
  /** Added to the page clock so its times carry on from the last tagged rally's end. */
  private offsetMs = 0;

  constructor(private readonly pageNowMs: () => number) {}

  /** The time in ms for the next mark, given the video (null: none) and the last rally's end. */
  read(video: VideoTime | null, lastEndMs: number | null): number {
    if (video?.plays) return Math.floor(video.videoMs);
    const page = Math.floor(this.pageNowMs());
    if (lastEndMs !== null) this.offsetMs = Math.max(this.offsetMs, lastEndMs - page);
    return page + this.offsetMs;
  }
}
