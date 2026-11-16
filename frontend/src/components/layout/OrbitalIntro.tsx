import { useEffect, useRef } from 'react';
import { ArrowDown, ArrowRight, ArrowUpRight, Orbit } from 'lucide-react';
import './orbital-intro.css';

const photoSource = 'https://www.jpl.nasa.gov/images/pia26538-spherex-spacecraft-during-integration-and-testing/';

function easeBetween(progress: number, start: number, end: number) {
  const amount = Math.max(0, Math.min(1, (progress - start) / (end - start)));
  return amount * amount * (3 - 2 * amount);
}

export function OrbitalIntro() {
  const track = useRef<HTMLElement>(null);
  const stage = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const section = track.current;
    const scene = stage.current;
    if (!section || !scene) return;

    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
    let animationFrame = 0;

    const update = () => {
      animationFrame = 0;
      const { top, height } = section.getBoundingClientRect();
      const distance = height - scene.clientHeight;
      const progress = reducedMotion.matches || distance <= 0 ? 0 : Math.max(0, Math.min(1, -top / distance));
      scene.style.setProperty('--flight-progress', String(progress));
      scene.style.setProperty('--flight-camera', String(easeBetween(progress, 0, 1)));
      scene.style.setProperty('--flight-exit', String(easeBetween(progress, 0.55, 1)));
    };

    const queueUpdate = () => {
      if (!animationFrame) animationFrame = window.requestAnimationFrame(update);
    };

    update();
    window.addEventListener('scroll', queueUpdate, { passive: true });
    window.addEventListener('resize', queueUpdate);
    reducedMotion.addEventListener('change', queueUpdate);

    return () => {
      window.cancelAnimationFrame(animationFrame);
      window.removeEventListener('scroll', queueUpdate);
      window.removeEventListener('resize', queueUpdate);
      reducedMotion.removeEventListener('change', queueUpdate);
    };
  }, []);

  return (
    <section className="orbital-intro" id="orbital-intro" aria-labelledby="orbital-title" ref={track}>
      <div className="orbital-stage" ref={stage}>
        <div className="orbital-field">
          <div className="orbital-photo-window">
            <img
              className="orbital-camera"
              src="/images/spherex-testing-2800.webp"
              width={7104}
              height={4736}
              alt="The SPHEREx spacecraft on its side in a blue- and red-lit cleanroom, with three reflective shields around the telescope opening."
              fetchPriority="high"
            />
          </div>
          <div className="orbital-light" aria-hidden="true" />
          <div className="orbital-guide" aria-hidden="true"><i /><i /><i /></div>
          <div className="orbital-handoff" aria-hidden="true" />
        </div>
        <div className="orbital-layout">
          <header className="orbital-header">
            <span className="orbital-brand"><span><Orbit aria-hidden="true" /></span> SPHEREx Discovery</span>
            <a href="#observatory">Observatory <ArrowUpRight aria-hidden="true" /></a>
          </header>
          <div className="orbital-body">
            <div className="orbital-copy">
              <p className="orbital-label">NASA mission · Infrared sky survey</p>
              <h1 id="orbital-title">The sky <em>in motion.</em></h1>
              <p className="orbital-description">Explore the same patch of sky across different dates. Switch between real infrared observations to see what changes.</p>
              <a className="orbital-launch" href="#observatory">Enter observatory <span><ArrowRight aria-hidden="true" /></span></a>
            </div>
            <a className="orbital-photo-note" href={photoSource} target="_blank" rel="noreferrer">
              <span>
                <strong>SPHEREx during testing</strong>
                <span>NASA/JPL-Caltech/BAE Systems</span>
              </span>
              <ArrowUpRight aria-hidden="true" />
              <span className="sr-only">View original photo (opens in a new tab)</span>
            </a>
          </div>
          <div className="orbital-bottom">
            <a href="#observatory" className="orbital-scroll"><ArrowDown aria-hidden="true" /> Scroll to fly in</a>
            <div aria-hidden="true" className="orbital-progress" />
            <p><span>Infrared survey</span> 0.75–5.0 µm</p>
          </div>
        </div>
      </div>
    </section>
  );
}
