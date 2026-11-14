import pytest
import numpy as np
from app.science.image_registration import estimate_pixel_shift

def test_identical_images():
    img = np.zeros((20, 20), dtype=np.float32)
    img[10, 10] = 50.0
    dy, dx = estimate_pixel_shift(img, img)
    assert dy == 0.0
    assert dx == 0.0

def test_known_shift_recovery():
    img1 = np.zeros((30, 30), dtype=np.float32)
    img1[15, 15] = 100.0
    img2 = np.zeros((30, 30), dtype=np.float32)
    img2[17, 18] = 100.0  # shifted +2 y, +3 x
    
    dy, dx = estimate_pixel_shift(img1, img2)
    assert dy == -2.0
    assert dx == -3.0

def test_different_dimensions():
    img1 = np.zeros((25, 20), dtype=np.float32)
    img1[10, 10] = 20.0
    img2 = np.zeros((30, 25), dtype=np.float32)
    img2[10, 10] = 20.0
    
    dy, dx = estimate_pixel_shift(img1, img2)
    assert dy == 0.0
    assert dx == 0.0

def test_nan_and_inf_robustness():
    img1 = np.zeros((20, 20), dtype=np.float32)
    img1[10, 10] = 30.0
    img1[0, 0] = np.nan
    img1[1, 1] = np.inf

    img2 = np.zeros((20, 20), dtype=np.float32)
    img2[10, 10] = 30.0
    img2[19, 19] = np.nan

    dy, dx = estimate_pixel_shift(img1, img2)
    assert dy == 0.0
    assert dx == 0.0

def test_constant_image():
    img1 = np.ones((20, 20), dtype=np.float32) * 5.0
    img2 = np.ones((20, 20), dtype=np.float32) * 5.0
    dy, dx = estimate_pixel_shift(img1, img2)
    assert dy == 0.0
    assert dx == 0.0
