# Calmdesk widgets

Community widgets for [Calmdesk](https://github.com/rom5n/calmdesk). Everything merged here
shows up in the Community section of the Calmdesk gallery, where users install it in one click.

## Adding your widget

1. Build a widget package with [widgine](https://github.com/rom5n/widgine): a folder with
   `widget.toml` and `layout.xml`. Try it with `widget-dev <folder>`.
2. Fill in the store fields in `widget.toml`:
   ```toml
   id = "com.yourname.weather"   # the folder name must be the same
   author = "Your Name"
   version = "1.0.0"             # raise it for every update
   icon = "assets/icon.svg"      # square SVG, or PNG of at least 64x64 px
   homepage = "https://..."      # optional
   ```
3. Copy the folder to `packages/<id>/` and open a pull request. CI checks the package with
   `widget-dev --check`, and checks the fields and the icon.
4. After review and merge, CI publishes it. Calmdesk reads the index once a day.

To update a widget, change its folder and raise `version`. Users see "Update available" on its
tile.

## Rules

- Packages are declarative (layout and assets, no code), at most 20 MB.
- One folder per id; an id belongs to the author who added it first.
- Ids starting with `dev.widget-engine.` or `dev.widgine.` are reserved for Calmdesk.

## License

Each package keeps its author's license; put a `LICENSE` file in its folder. The tools in this
repository are MIT.
