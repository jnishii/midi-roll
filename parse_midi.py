import midiroll as mr

"""
convert midi file into csv, dump, and roll image
Usage:
    poetry run python parse_midi.py

"""

dir = "data/pedb2_v0.0.1.b/"
#target="bac-inv001-o-p2"
target = "bac-wtc101-p-a-p1"

mid = mr.MidiFile(dir, target, verbose=False)
mid.show_basic_info()
mid.draw_roll()
