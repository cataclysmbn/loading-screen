# Loading screens

Loading screen images for [Cataclysm: Bright Nights](https://github.com/cataclysmbn/Cataclysm-BN). Release
builds copy `data/` from this repository into the game's `data/`, so files here use the game's paths:

- `data/json/loading/` for the base game
- `data/mods/<mod>/loading/` for a mod

The game shows the part of the file name before the first `_` as the artist: `<artist>_<title>.webp`.

## Submitting an image

Open a [loading screen issue](../../issues/new?template=loading-screen.yml) and attach the image. A bot converts it
to WebP under 128 KiB and opens a pull request. A maintainer reviews and merges it.

We try to be careful with copyright issues. Submit only images that you made or that the artist allowed us to use,
with no traced or copied material, no AI generation and nothing NSFW.

## Checking images

Images are stored with Git LFS. To check files before opening a pull request by hand:

```sh
uv run scripts/loading_screen.py check data/json/loading/<artist>_<title>.webp
```
