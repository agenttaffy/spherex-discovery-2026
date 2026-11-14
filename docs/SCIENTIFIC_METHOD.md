# SPHEREx Discovery — Scientific Method & Mathematical Formulations

## 1. SPHEREx Mission & Linear Variable Filter (LVF) Optics

SPHEREx (Spectro-Photometer for the History of the Universe, Epoch of Reionization and Ices) is an all-sky infrared spectral survey covering $0.75\,\mu\text{m}$ to $5.0\,\mu\text{m}$ across 102 spectral bands.

### Optical Architecture
SPHEREx features two identical telescopes with 20 cm apertures feeding six $2048 \times 2048$ pixel Teledyne H2RG infrared detector arrays (designated D1 through D6):
- **Detectors D1–D3:** Near-infrared beamsplitter channel ($0.75\,\mu\text{m} - 2.42\,\mu\text{m}$).
- **Detectors D4–D6:** Mid-infrared beamsplitter channel ($2.42\,\mu\text{m} - 5.00\,\mu\text{m}$).

### Linear Variable Filter Physics & Differencing Constraints
Unlike classical wide-field survey telescopes (e.g. Hubble, JWST, Rubin) equipped with discrete wideband glass filters, SPHEREx mounts **Linear Variable Filters (LVFs)** directly on top of the detector arrays. The filter passband varies continuously along one spatial dimension of each detector array:

$$\lambda(x) = \lambda_0 + \frac{d\lambda}{dx} \cdot x$$

Consequently:
1. **Intra-Detector Differencing:** Direct pixel-by-pixel temporal subtraction ($I_2 - I_1$) is **strictly valid only** between observations acquired with the **exact same detector band** (e.g., both D3 or both D4) and aligned celestial coordinates.
2. **Cross-Detector Prohibition:** Subtraction across differing detectors (e.g. D1 minus D4) subtracts physically disparate spectral windows ($0.8\,\mu\text{m}$ vs $3.5\,\mu\text{m}$), generating chromatic artifacts dominated by the intrinsic spectral energy distribution (SED) of background stars rather than true time variability.

---

## 2. Astrometric Coordinate System & WCS

Pixel positions $(x, y)$ are transformed to celestial equatorial coordinates $(\alpha, \delta)$ in the International Celestial Reference System (ICRS) using Astropy WCS and standard FITS World Coordinate System conventions:

$$\begin{pmatrix} x' \\ y' \end{pmatrix} = \begin{pmatrix} CD_{1\_1} & CD_{1\_2} \\ CD_{2\_1} & CD_{2\_2} \end{pmatrix} \begin{pmatrix} x - CRPIX1 \\ y - CRPIX2 \end{pmatrix}$$

$$\begin{pmatrix} \Delta\alpha \cos\delta \\ \Delta\delta \end{pmatrix} = \mathbf{Proj}^{-1}(x', y'; CRVAL1, CRVAL2)$$

The nominal pixel scale of SPHEREx is:
$$s_{\text{pix}} = 6.2\,\text{arcsec/pixel}$$

### Spherical RA Boundary Wrapping
When computing angular distances or checking eligibility across the celestial prime meridian ($\alpha = 0^\circ / 360^\circ$):
$$\Delta\alpha = (\alpha_1 - \alpha_2 + 180^\circ) \bmod 360^\circ - 180^\circ$$
$$d_{\text{ang}} = \sqrt{(\Delta\alpha \cos\bar{\delta})^2 + (\delta_1 - \delta_2)^2}$$

---

## 3. Sub-Pixel Image Registration (2D Fourier Phase Correlation)

Prior to differencing, subtle spacecraft pointing jitter and sub-pixel optical offsets between epochs are estimated using 2D Fourier phase cross-correlation:

Let $I_1(x, y)$ and $I_2(x, y)$ be two mean-subtracted observation images. Their 2D Fourier transforms are $\mathcal{F}_1 = \mathcal{F}\{I_1\}$ and $\mathcal{F}_2 = \mathcal{F}\{I_2\}$. The cross-power spectrum is:

$$R(u, v) = \frac{\mathcal{F}_1(u, v) \cdot \mathcal{F}_2^*(u, v)}{|\mathcal{F}_1(u, v) \cdot \mathcal{F}_2^*(u, v)|}$$

The spatial translation $(\Delta y, \Delta x)$ is given by the coordinate of the maximum of the inverse Fourier transform:
$$r(y, x) = \mathcal{F}^{-1}\{R(u, v)\}$$
$$(\Delta y, \Delta x) = \arg\max_{y, x} r(y, x)$$

---

## 4. Differential Imaging & Normalization

The calibrated temporal difference image is computed directly in physical surface brightness units of $\text{MJy/sr}$:

$$D(x, y) = I_2(x, y) - I_1(x, y)$$

To display difference images without clipping positive transients (brightened/new sources) or negative residuals (dimmed/departed sources), the floating-point difference is normalized to an 8-bit visual buffer centered on mid-gray:

$$U(x, y) = \text{clip}\left(128.0 + \frac{D(x, y)}{3.0 \cdot \sigma} \cdot 127.0, \, 0, \, 255\right)$$

Where $\sigma$ is the robust standard deviation of finite background pixels in $D(x, y)$:
- **$U = 128$ (Mid-gray):** Zero temporal change.
- **$U > 128$ (White):** Flux increase or new incoming source in Epoch 2.
- **$U < 128$ (Dark):** Flux decrease or departed source from Epoch 1.

---

## 5. Candidate Motion & Proper Motion Vector Formulation

When a point source moves across the sky between Epoch 1 ($t_1$) and Epoch 2 ($t_2$), it produces a characteristic **dipole signature** in $D(x, y)$ with centroid positions $(x_1, y_1)$ and $(x_2, y_2)$.

### Centroid Displacement
The sub-pixel centroid is determined via intensity-weighted center of mass in a local $5 \times 5$ window:
$$\bar{x} = \frac{\sum_i x_i \cdot \max(I_i - I_{\text{bg}}, 0)}{\sum_i \max(I_i - I_{\text{bg}}, 0)}$$

The displacement vector in pixel units:
$$\Delta x = x_2 - x_1, \quad \Delta y = y_2 - y_1$$
$$\Delta r_{\text{pix}} = \sqrt{(\Delta x)^2 + (\Delta y)^2}$$

### Angular Proper Motion
$$\Delta\theta_{\text{arcsec}} = \Delta r_{\text{pix}} \cdot s_{\text{pix}}$$
$$\Delta t_{\text{years}} = \frac{|\text{MJD}_2 - \text{MJD}_1|}{365.25}$$
$$\mu = \frac{\Delta\theta_{\text{arcsec}}}{\Delta t_{\text{years}}} \quad [\text{arcsec/year}]$$
$$\mu_{\text{mas}} = \mu \times 1000 \quad [\text{mas/year}]$$

### Position Angle
Position angle $\theta_{PA}$ measured from celestial North through East:
$$\theta_{PA} = \left(\text{degrees}\left(\operatorname{atan2}(-\Delta x, -\Delta y)\right) + 360^\circ\right) \bmod 360^\circ$$

---

## 6. Circular Aperture Photometry & Variability Index

For pulsating and variable stars (e.g. RW Aurigae, R Draconis), flux is measured within circular aperture $r \le r_{\text{ap}}$ with local background estimated in annulus $r_{\text{in}} \le r \le r_{\text{out}}$:

$$F_{\text{net}} = \sum_{r \le r_{\text{ap}}} I(r) - N_{\text{ap}} \cdot \operatorname{median}\left(I_{\text{annulus}}\right)$$

### Variability Index
Across $N$ epochs $\{F_1, F_2, \dots, F_N\}$:
$$\bar{F} = \frac{1}{N} \sum_{i=1}^N F_i, \quad \sigma_F = \sqrt{\frac{1}{N-1} \sum_{i=1}^N (F_i - \bar{F})^2}$$
$$\text{VarIndex} = \frac{\sigma_F}{|\bar{F}|}$$

A source is flagged as **CONFIRMED VARIABLE** when $\text{VarIndex} > 0.12$ or $\Delta F = \max(F) - \min(F) > 1.5\,\text{MJy/sr}$.
