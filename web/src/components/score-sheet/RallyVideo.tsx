'use client';

// Rally video V-01 (ST-037; FR-027; NFR-014, NFR-055). Plays the match video from the rally's
// start through a short-lived link fetched when the player asks (never stored in the page as a
// link). A link that stops working (expired or changed) says so; choosing the rally again
// fetches a new one. A codec this browser cannot decode is reported as such (QA-S2-UI-03). Focus moves to the video, so keyboard users land on its controls.
import { useEffect, useRef } from 'react';
import { classifyVideoFailure, type VideoFailure } from '@/lib/media/playback';
import type { RallyMedia } from '@/lib/tagging/types';
import { formatClock } from '@/lib/tagging/view';

export function RallyVideo({
  number,
  media,
  codec,
  onBroken,
}: {
  number: number;
  media: RallyMedia;
  /** The probed video codec of the match (`match.media.video_codec`), if known. */
  codec?: string | null;
  onBroken: (why: VideoFailure) => void;
}) {
  const video = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    video.current?.focus();
  }, [media.url]);

  return (
    <section className="stack rally-video" aria-labelledby="rally-video-title">
      <h2 id="rally-video-title">{`Rally ${number} video`}</h2>
      <video
        ref={video}
        key={media.url}
        src={media.url}
        controls
        playsInline
        preload="auto"
        className="quick-tag__player"
        onLoadedMetadata={(e) => {
          const v = e.currentTarget;
          v.currentTime = media.startMs / 1000;
          // The click that asked for the video is the user gesture; if the browser still
          // refuses, the controls stay and the player presses play.
          void v.play()?.catch(() => {});
        }}
        onError={(e) => {
          const v = e.currentTarget;
          onBroken(classifyVideoFailure(v.error, codec, (type) => v.canPlayType(type)));
        }}
      />
      <p>{`Starts at ${formatClock(media.startMs)}`}</p>
    </section>
  );
}
