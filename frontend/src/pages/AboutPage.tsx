import React from 'react';
import { Telescope, BookOpen, Award, ExternalLink, ArrowRight } from 'lucide-react';

const targets = [
  { name: "Barnard's Star", note: 'High proper motion makes epoch-aware position comparison essential.' },
  { name: 'WISE 0855', note: 'A faint, fast-moving brown dwarf; its source identity is not confirmed in these cutouts.' },
  { name: 'RW Aurigae', note: 'A variable young system whose components are unresolved at SPHEREx sampling.' },
  { name: 'R Draconis', note: 'A Mira-type pulsating star. The current cached cube sample has no usable coverage.' },
  { name: 'Epsilon Indi B', note: 'The brown dwarf pair Ba/Bb remains unresolved in the tested SPHEREx data.' },
];

export const AboutPage: React.FC<{ onExplore?: () => void }> = ({ onExplore }) => (
  <div className="observatory-about-inner">
    <header className="observatory-about-hero">
      <div>
        <p className="observatory-about-label">NASA Space Apps Challenge 2026 · Planet X and SPHEREx</p>
        <h2>Read the sky <em>over time.</em></h2>
        <p>SPHEREx maps the whole sky in near-infrared light. This observatory helps you compare dated image fields, explore their spectral channels, and see where the evidence ends.</p>
        {onExplore && <button type="button" className="observatory-action" onClick={onExplore}>Explore observations <ArrowRight aria-hidden="true" /></button>}
      </div>
      <dl className="observatory-mission-specs">
        <div><dt>Wavelength range</dt><dd>0.75–5.0 <small>µm</small></dd></div>
        <div><dt>Nominal channel slots</dt><dd>102</dd></div>
        <div><dt>Detector arrays</dt><dd>6</dd></div>
        <div><dt>Sky survey</dt><dd>All sky</dd></div>
      </dl>
    </header>

    <section className="observatory-about-grid" aria-label="Mission and data notes">
      <article className="glass-card p-4 sm:p-5">
        <h3 className="observatory-telemetry-label"><Telescope aria-hidden="true" /> Instrument &amp; filters</h3>
        <p className="mt-3 text-sm text-slate-300 leading-relaxed">Six focal-plane arrays use linear variable filters to sample 102 nominal near-infrared channel slots. The Spectral Cube view displays co-added DR1 sky-pixel measurements; coverage and flags vary by coordinate, and two DR1 slots are blank.</p>
      </article>
      <article className="glass-card p-4 sm:p-5">
        <h3 className="observatory-telemetry-label"><BookOpen aria-hidden="true" /> What this app measures</h3>
        <p className="mt-3 text-sm text-slate-300 leading-relaxed">Image stretch changes display contrast only. The cached cube values are sky-pixel surface brightness, not source spectra. Current tests do not confirm target identity, target flux, motion, or variability.</p>
      </article>
    </section>

    <section className="observatory-about-targets">
      <h3><Award aria-hidden="true" /> Challenge targets</h3>
      <ul>{targets.map(target => <li key={target.name}><strong>{target.name}</strong><span>{target.note}</span></li>)}</ul>
    </section>

    <section className="observatory-about-sources" aria-label="Data citations and provenance">
      <h3>Data, citations &amp; provenance</h3>
      <p>SPHEREx products are accessed through the NASA/IPAC Infrared Science Archive. Read the app’s target validation and demo-data audit before interpreting a field sample as a detection.</p>
      <a href="https://doi.org/10.26131/IRSA678" target="_blank" rel="noreferrer">DR1 spectral images · DOI 10.26131/IRSA678 <ExternalLink aria-hidden="true" /></a>
      <a href="https://doi.org/10.26131/IRSA679" target="_blank" rel="noreferrer">DR1 all-sky spectral cube · DOI 10.26131/IRSA679 <ExternalLink aria-hidden="true" /></a>
      <a href="https://irsa.ipac.caltech.edu/Missions/spherex.html" target="_blank" rel="noreferrer">NASA/IPAC IRSA SPHEREx archive <ExternalLink aria-hidden="true" /></a>
      <a href="https://www.spaceappschallenge.org/2026/challenges/planet-x-and-spherex/" target="_blank" rel="noreferrer">Challenge brief <ExternalLink aria-hidden="true" /></a>
    </section>
  </div>
);
