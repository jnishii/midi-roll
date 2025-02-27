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

## Environments

Currently I'm using pyenv 3.10.13 with poetry.

1. Install pyenv 3.10.13. Ask Google if you're not familiar with pyenv.
2. Install libraries using poetry:
```
poetry install
```

## MIDI Data

I'm using MIDI data from [EDB: Music Performance Expression with Phrase Structure](https://crestmuse.jp/pedb_edition2/).
You can put the data under this repo, but I prefer to put them outside like:

```
-+- midi-roll/
 |
 +- data/pedb2_v0.0.1b/
```
and make a symlink
```
cd midi-roll/
ln -sf ../data .
```
Then, you can easily access the data from the codes in this repo.


## Codes

- `midiroll/roll.py`
    - Get piano-roll image using user friendly web interface.
    - For quick run,
        ```
        poetry run streamlit run midiroll/roll.py
        ```
        or
        ```
        make run
        ```
- midi_analysis.ipynb
    - Analyse inter-note intervals
- music21.ipynb
    - Some graph examples by [music21](https://web.mit.edu/music21/doc/usersGuide/usersGuide_22_graphing.html)


To use ipynb files, run jupyter lab:
```
poetry run jupyter lab
```
or
```
make jupyter
```




## Links

- [EDB: Music Performance Expression with Phrase Structure](https://crestmuse.jp/pedb_edition2/)
- [audio visualize_app](https://github.com/root4kaido/audio_visualize_app)
