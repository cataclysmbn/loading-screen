# Loading screens

Loading screen images for [Cataclysm: Bright Nights](https://github.com/cataclysmbn/Cataclysm-BN). Paths match game
`data/` folder:

- `data/json/loading/`: base game
- `data/mods/<mod>/loading/`: one mod

Name each file `<artist>_<title>.webp`. Game shows text before first `_` as artist name.

Each change to `main` updates [`nightly` release](../../releases/tag/nightly). Cataclysm-BN builds extract its archive
into game folder. To get images in a local Cataclysm-BN checkout, run `just loading-screens`.

## Submit an image

1. Open a [loading screen issue](../../issues/new?template=loading-screen.yml).
2. Drag image into Image field and check all boxes.
3. Open pull request link from bot comment. Pull request has your image as WebP, 128 KiB or less.
4. Maintainer reviews and merges it.

We try to be careful with copyright issues. Submit only images that you made or that artist allowed us to use. Do not
submit traced, copied, AI-generated or NSFW images.

## Check images

Images use Git LFS. Before you open a pull request by hand, run:

```sh
uv run scripts/loading_screen.py check data/json/loading/<artist>_<title>.webp
```
