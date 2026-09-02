# DitherTop NonED Demo

Dithering essentials. **CPlusPlus TOP**. Perfect for learning and quick exports.

## Features
- **Bayer Ordered**: Fixed 2×2 matrix
- **White Noise**: 0 (off) or 0.8 (strong)
- **Blue Noise**: 0 or 0.8 preset
- **Grayscale Only**
- **Output Levels**: 3 or 8 colors
- **Downscale**: 0.4–0.6 (aspect preserved)
- **Post-Upscale**: Optional nearest-pixel upscale to input resolution

## Install
Copy `DitherTopNonEDDemo.dll` to your TouchDesigner plugins folder.

## Usage
1. Create a **CPlusPlus TOP**
2. Load `DitherTopNonEDDemo.dll`
3. Connect input texture
4. Choose **Mode** (Bayer/White Noise/Blue Noise)
5. Set **Noise Level** (0 or 0.8 only)
6. Pick **Levels** (3 or 8)
7. Adjust **Downscale** (0.4–0.6)
8. Toggle **Post-Upscale** to return to input resolution

## ⚠️ Important: Output Resolution
- **Post-Upscale ON**: Output matches input resolution (recommended)
- **Post-Upscale OFF**: Output is downscaled. Make sure to toggle **Nearest Pixel** option to ON in the following TOPs after dithering, otherwise they will interpolate and create unwanted blur.

## Tips
- **3 colors** = ultra-minimal (black, gray, white)
- **8 colors** = richer palette for full images
- Fixed 2×2 Bayer = consistent pixelation

---
*Upgrade to Full version for RGB mode & unlimited levels.*
