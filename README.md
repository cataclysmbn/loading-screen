# Loading screens

Loading screen images for [Cataclysm: Bright Nights](https://github.com/cataclysmbn/Cataclysm-BN).

To submit one, [open an issue](../../issues/new?template=loading-screen.yml) and attach the image. We try to be careful
with copyright issues: send only your own work or art you have the artist's permission to use, and nothing traced,
copied, AI-generated or NSFW.

Images are in Git LFS, laid out like the game's `data/` folder and named `<artist>_<title>.webp`:

- `data/json/loading/` for the base game
- `data/mods/<mod>/loading/` for a mod

Every merge to `main` goes into the [`nightly`](../../releases/tag/nightly) release. Run `just loading-screens` in a
Cataclysm-BN checkout to download it.
