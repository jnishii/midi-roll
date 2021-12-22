# midi-visualization
A revised version of python package for midi-visualization, originally distributed in [github.com/exeex/midi-vsualization](https://github.com/exeex/midi-visualization/).

## Updates from original version

I added some arguments to functions, and some minor corrections for the code.

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

## Usage

Just see the `__main__` block in the script like this:

```
mid = MidiFile("some_good_music.mid") # set file path
roll = mid.get_roll(verbose=False)
mid.draw_roll(figsize=(18,6),xlim=[0,10],colorbar=False)
```
