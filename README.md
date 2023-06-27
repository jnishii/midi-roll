# midi-visualization
A revised version of python package for midi-visualization, originally distributed in [github.com/exeex/midi-vsualization](https://github.com/exeex/midi-visualization/).

## Updates from original version

I added some arguments to functions, and many corrections for the code.

- `mid.get_roll()`
    - `verbose=False`
- `mid.draw_roll()`
    - new args:
        - `figsize`
        - `xlim`
        - `ylim`
        - `colorbar=False`
    - put title on the top
    - save a fig as png

## install libraries

To install required libraries, just run:
```
poetry install
```

## MIDI Data

I'm using MIDI data from [EDB: Music Performance Expression with Phrase Structure](https://crestmuse.jp/pedb_edition2/).
Off course you can put the data under this repo, but I prefer to put them outside like:

```
-+- midi-roll/
 |
 +- data/pedb2_v0.0.1b/
```
and make a symlink:
```
cd midi-roll/
ln -sf ../data .
```
Then, you can easily access the data from the codes in this repo.


## Usage

For quick run,

```
poetry run streamlit run midiroll/roll.py
```


Just see the `__main__` block in the script like this:

```
mid = MidiFile("some_good_music.mid") # set file path
roll = mid.get_roll(verbose=False)
mid.draw_roll(figsize=(18,6),xlim=[0,10],colorbar=False)
```

## Links

- [EDB: Music Performance Expression with Phrase Structure](https://crestmuse.jp/pedb_edition2/)
- [audio visualize_app](https://github.com/root4kaido/audio_visualize_app)
