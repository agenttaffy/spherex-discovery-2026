// verify_accessibility_and_responsive.mjs
// Automated verification of WCAG 2.2 AA accessibility, keyboard navigation, and responsive constraints

import fs from 'fs';
import path from 'path';

const ROOT_DIR = process.cwd();
const FRONTEND_SRC = path.join(ROOT_DIR, 'frontend', 'src');

console.log('============================================================');
console.log('SPHEREx Discovery Accessibility & Responsive Verification');
console.log('============================================================\n');

let passCount = 0;
let failCount = 0;

function assert(condition, message) {
  if (condition) {
    console.log(`[PASS] ${message}`);
    passCount++;
  } else {
    console.error(`[FAIL] ${message}`);
    failCount++;
  }
}

// 1. Check index.css for WCAG 2.2 Focus Indicators & Reduced Motion
const indexCss = fs.readFileSync(path.join(FRONTEND_SRC, 'index.css'), 'utf-8');
assert(indexCss.includes(':focus-visible'), 'index.css defines global :focus-visible indicators');
assert(indexCss.includes('prefers-reduced-motion'), 'index.css respects prefers-reduced-motion media query');
assert(indexCss.includes('min-width: 320px'), 'index.css defines 320px minimum viewport safety constraint');
assert(indexCss.includes('overflow-x: hidden'), 'index.css prevents horizontal document scroll');

// 2. Check CanvasViewer.tsx for Canvas Keyboard Controls and Announcements
const canvasViewer = fs.readFileSync(path.join(FRONTEND_SRC, 'components', 'viewer', 'CanvasViewer.tsx'), 'utf-8');
assert(canvasViewer.includes("handleKeyDown"), 'CanvasViewer implements handleKeyDown handler');
assert(canvasViewer.includes("ArrowUp") && canvasViewer.includes("ArrowDown") && canvasViewer.includes("ArrowLeft") && canvasViewer.includes("ArrowRight"), 'CanvasViewer implements Arrow key panning');
assert(canvasViewer.includes("'+'") || canvasViewer.includes("'='"), 'CanvasViewer implements "+" / "=" zoom in');
assert(canvasViewer.includes("'-'") || canvasViewer.includes("'_'"), 'CanvasViewer implements "-" / "_" zoom out');
assert(canvasViewer.includes("'0'"), 'CanvasViewer implements "0" reset view');
assert(canvasViewer.includes('aria-live="polite"'), 'CanvasViewer has aria-live="polite" region for screen reader announcements');
assert(canvasViewer.includes('tabIndex={0}'), 'CanvasViewer container has tabIndex={0} keyboard focusability');
assert(canvasViewer.includes('focus-visible:ring-2 focus-visible:ring-cyan-400'), 'CanvasViewer has high-visibility focus ring');
assert(canvasViewer.includes('role="tablist"') && canvasViewer.includes('role="tab"'), 'CanvasViewer viewer switcher uses role="tablist" and role="tab"');

// 3. Check SpectrumChart.tsx for Accessible Tabular Data View
const spectrumChart = fs.readFileSync(path.join(FRONTEND_SRC, 'components', 'science', 'SpectrumChart.tsx'), 'utf-8');
assert(spectrumChart.includes('<details'), 'SpectrumChart includes expandable <details> disclosure');
assert(spectrumChart.includes('View Accessible Data Table'), 'SpectrumChart includes "View Accessible Data Table" summary');
assert(spectrumChart.includes('role="table"'), 'SpectrumChart data table has role="table"');
assert(spectrumChart.includes('scope="col"'), 'SpectrumChart table headers have scope="col"');
assert(spectrumChart.includes('caption className="sr-only"'), 'SpectrumChart table includes screen-reader caption');

// 4. Check LightCurveChart.tsx for Accessible Tabular Data View
const lightCurveChart = fs.readFileSync(path.join(FRONTEND_SRC, 'components', 'science', 'LightCurveChart.tsx'), 'utf-8');
assert(lightCurveChart.includes('<details'), 'LightCurveChart includes expandable <details> disclosure');
assert(lightCurveChart.includes('View Accessible Data Table'), 'LightCurveChart includes "View Accessible Data Table" summary');
assert(lightCurveChart.includes('role="table"'), 'LightCurveChart data table has role="table"');
assert(lightCurveChart.includes('scope="col"'), 'LightCurveChart table headers have scope="col"');

// 5. Check Header.tsx for ARIA tablist and 320px responsive wrapping
const header = fs.readFileSync(path.join(FRONTEND_SRC, 'components', 'layout', 'Header.tsx'), 'utf-8');
assert(header.includes('role="tablist"'), 'Header navigation uses role="tablist"');
assert(header.includes('role="tab"'), 'Header navigation buttons use role="tab"');
assert(header.includes('flex-wrap'), 'Header wraps gracefully on narrow viewports');

// 6. Check App.tsx for Mobile Panel Switcher and Responsive Reflow
const app = fs.readFileSync(path.join(FRONTEND_SRC, 'App.tsx'), 'utf-8');
assert(app.includes('mobilePanel'), 'App implements mobilePanel state for deliberate panel stacking');
assert(app.includes('role="tablist"') && app.includes('mobilePanel === \'canvas\''), 'App implements mobile tabs for Canvas, Target, and Telemetry');
assert(app.includes('lg:flex'), 'App displays side-by-side multi-dock layout on lg (>=1024px) screens');

// 7. Check SearchControls and MetadataPanel responsive widths
const searchControls = fs.readFileSync(path.join(FRONTEND_SRC, 'components', 'controls', 'SearchControls.tsx'), 'utf-8');
const metadataPanel = fs.readFileSync(path.join(FRONTEND_SRC, 'components', 'metadata', 'MetadataPanel.tsx'), 'utf-8');
assert(searchControls.includes('w-full lg:w-80'), 'SearchControls uses responsive full width on mobile and 320px on desktop');
assert(metadataPanel.includes('w-full lg:w-80'), 'MetadataPanel uses responsive full width on mobile and 320px on desktop');

// 8. Check ComparisonView for Mode Switcher role="tablist", Diverging colormap, and Accessible Data Table
const comparisonView = fs.readFileSync(path.join(FRONTEND_SRC, 'components', 'viewer', 'ComparisonView.tsx'), 'utf-8');
assert(comparisonView.includes('role="tablist"'), 'ComparisonView operation mode switcher uses role="tablist"');
assert(comparisonView.includes('role="tab"'), 'ComparisonView operation mode buttons use role="tab"');
assert(comparisonView.includes('View Accessible Comparison Metrics Table'), 'ComparisonView includes accessible metrics table disclosure');
assert(comparisonView.includes('diffColormap'), 'ComparisonView supports diverging colormap toggle for difference frames');

// 9. Check GuidedTourModal and DiscoveryReportModal for Dialog accessibility
const tourModal = fs.readFileSync(path.join(FRONTEND_SRC, 'components', 'layout', 'GuidedTourModal.tsx'), 'utf-8');
const reportModal = fs.readFileSync(path.join(FRONTEND_SRC, 'components', 'science', 'DiscoveryReportModal.tsx'), 'utf-8');
assert(tourModal.includes('role="dialog"') && tourModal.includes('aria-modal="true"'), 'GuidedTourModal has role="dialog" and aria-modal="true"');
assert(reportModal.includes('role="dialog"') && reportModal.includes('aria-modal="true"'), 'DiscoveryReportModal has role="dialog" and aria-modal="true"');

// 10. Check SpectrumChart for 102-Channel accessible table support
assert(spectrumChart.includes('102-Channel Model'), 'SpectrumChart includes 102-channel spectrophotometric continuum accessible table toggle');
assert(spectrumChart.includes('tableDataset'), 'SpectrumChart manages accessible table dataset state between observed bands and continuum channels');

// 11. Check CanvasViewer dynamic announcements and boundary protection
assert(canvasViewer.includes('Offset: X='), 'CanvasViewer generates dynamic offset coordinates in announcements to prevent consecutive speech silence');
assert(canvasViewer.includes('Maximum zoom limit reached'), 'CanvasViewer announces zoom limit boundaries to screen readers');

// 12. Check App.tsx for URL observation deep linking synchronization
assert(app.includes("url.searchParams.set('obs', obs.id)"), 'App synchronizes active observation with URL search params on timeline navigation');

console.log('\n============================================================');
console.log(`Results: ${passCount} passed, ${failCount} failed`);
console.log('============================================================');

if (failCount > 0) {
  process.exit(1);
}
