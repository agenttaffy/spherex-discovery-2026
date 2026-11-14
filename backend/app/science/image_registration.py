import numpy as np
from typing import Tuple, Dict, Any

def estimate_pixel_shift(
    img1: np.ndarray,
    img2: np.ndarray
) -> Tuple[float, float]:
    """
    Estimates relative pixel translation (dy, dx) between two images
    using 2D cross-correlation peak.
    Returns (dy, dx) of img2 relative to img1.
    Robust against NaN/Inf values and constant images.
    """
    if img1.shape != img2.shape:
        min_h = min(img1.shape[0], img2.shape[0])
        min_w = min(img1.shape[1], img2.shape[1])
        i1 = img1[:min_h, :min_w].copy()
        i2 = img2[:min_h, :min_w].copy()
    else:
        i1 = img1.copy()
        i2 = img2.copy()

    # Sanitize non-finite values
    mask1 = np.isfinite(i1)
    mask2 = np.isfinite(i2)
    
    if not np.any(mask1) or not np.any(mask2):
        return 0.0, 0.0

    mean1 = float(np.mean(i1[mask1]))
    mean2 = float(np.mean(i2[mask2]))
    i1[~mask1] = mean1
    i2[~mask2] = mean2

    # Check for constant/zero-variance images
    if np.std(i1) < 1e-6 or np.std(i2) < 1e-6:
        return 0.0, 0.0

    # Mean subtract
    i1_zero = i1 - np.mean(i1)
    i2_zero = i2 - np.mean(i2)

    # 2D FFT Cross-correlation: f2 * conj(f1) gives the shift of img2 relative to img1
    f1 = np.fft.fft2(i1_zero)
    f2 = np.fft.fft2(i2_zero)
    cross_corr = np.real(np.fft.ifft2(f2 * np.conj(f1)))

    # Find peak
    y_peak, x_peak = np.unravel_index(np.argmax(cross_corr), cross_corr.shape)

    # Wrap negative frequencies
    h, w = cross_corr.shape
    if y_peak > h // 2:
        y_peak -= h
    if x_peak > w // 2:
        x_peak -= w

    return float(y_peak), float(x_peak)
