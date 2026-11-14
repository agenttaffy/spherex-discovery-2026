import numpy as np
from typing import Tuple, Dict, Any

def estimate_pixel_shift(
    img1: np.ndarray,
    img2: np.ndarray
) -> Tuple[float, float]:
    """
    Estimates relative pixel translation (dy, dx) between two images
    using 2D cross-correlation peak.
    """
    if img1.shape != img2.shape:
        min_h = min(img1.shape[0], img2.shape[0])
        min_w = min(img1.shape[1], img2.shape[1])
        i1 = img1[:min_h, :min_w]
        i2 = img2[:min_h, :min_w]
    else:
        i1 = img1
        i2 = img2

    # Mean subtract
    i1_zero = i1 - np.mean(i1)
    i2_zero = i2 - np.mean(i2)

    # 2D FFT Cross-correlation
    f1 = np.fft.fft2(i1_zero)
    f2 = np.fft.fft2(i2_zero)
    cross_corr = np.real(np.fft.ifft2(f1 * np.conj(f2)))

    # Find peak
    y_peak, x_peak = np.unravel_index(np.argmax(cross_corr), cross_corr.shape)

    # Wrap negative frequencies
    h, w = cross_corr.shape
    if y_peak > h // 2:
        y_peak -= h
    if x_peak > w // 2:
        x_peak -= w

    return float(y_peak), float(x_peak)
