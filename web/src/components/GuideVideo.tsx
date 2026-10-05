'use client';

// Guide video (ST-015; flows G-01; FR-020; NFR-033): native controls, captions on by default,
// no autoplay [DPA/DESIGN-08]. The checklist above is its text alternative [DPA/DESIGN-09], so
// when the video cannot load nothing is lost and the page says so. The video is never cached
// by the service worker (media rule).
import { useEffect, useRef, useState } from 'react';

const NETWORK_NO_SOURCE = 3;

export function GuideVideo() {
  const video = useRef<HTMLVideoElement>(null);
  const lastSource = useRef<HTMLSourceElement>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    // The error may have fired before hydration attached the listeners.
    const v = video.current;
    if (v && (v.error || v.networkState === NETWORK_NO_SOURCE)) setFailed(true);
    const source = lastSource.current;
    const onError = () => setFailed(true);
    source?.addEventListener('error', onError);
    return () => source?.removeEventListener('error', onError);
  }, []);

  // Captions on by default (SC 1.2.2; PD-R1-02). WebKit applies the system caption preference
  // instead of the track's `default`, leaving it "disabled" (CI run 37298471332). Turn it on
  // at mount, when the media loads and on the first play only, so a viewer who switches the
  // captions off afterwards keeps that choice.
  useEffect(() => {
    const v = video.current;
    if (!v) return;
    const show = () => {
      const tracks = v.textTracks as TextTrackList | undefined;
      if (!tracks) return;
      for (let i = 0; i < tracks.length; i += 1) {
        const t = tracks[i];
        if (t && t.kind === 'captions' && t.mode !== 'showing') t.mode = 'showing';
      }
    };
    show();
    v.addEventListener('loadedmetadata', show);
    v.addEventListener('play', show, { once: true });
    return () => {
      v.removeEventListener('loadedmetadata', show);
      v.removeEventListener('play', show);
    };
  }, []);

  return (
    <figure className="guide-video stack">
      <figcaption>Everything in the video is in the checklist above.</figcaption>
      {failed ? (
        <p className="notice notice--info" role="status">
          The video can&apos;t play right now. Everything in it is in the checklist above.
        </p>
      ) : null}
      <video
        ref={video}
        controls
        preload="metadata"
        playsInline
        poster="/guide/capture-guide-poster.jpg"
        width={640}
        height={360}
        className="guide-video__player"
        onError={() => setFailed(true)}
      >
        <source src="/guide/capture-guide.webm" type="video/webm" />
        <source
          ref={lastSource}
          src="/guide/capture-guide.mp4"
          type="video/mp4"
          onError={() => setFailed(true)}
        />
        <track kind="captions" src="/guide/capture-guide.en.vtt" srcLang="en" label="English" default />
      </video>
    </figure>
  );
}
