from turtle import bgcolor
import mido
import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
from matplotlib.colors import colorConverter
import re
from pathlib import Path


class MidiFile(mido.MidiFile):

    def __init__(self, midifile, verbose=False):
        self.sr = 10   # down sampling rate from MIDI to time axis
        self.meta = {}
        self.max_nch = 16

        print("Filename: ", midifile)
        mido.MidiFile.__init__(self, midifile)
        self.fpath = Path(midifile)

        self.events = self.get_events(verbose)
        self.roll = self.get_roll(self.events)


    def get_tempo(self):
        try:
            return self.meta["set_tempo"]["tempo"]
        except:
            return 500000

    def get_total_ticks(self):
        max_ticks = 0
        for channel in range(self.nch):
            ticks = sum(msg.time for msg in self.events[channel])
            if ticks > max_ticks:
                max_ticks = ticks
        return max_ticks

    def get_events(self, verbose=False):
        """
        Extract self.nch (default: 16) channel data from MIDI and return a list.
        Lyrics and meta data used in extra channels are not include in the list.

        Returns:
            list : [[ch1],[ch2]....[ch16]]
        """
        if verbose:
            print(self)

        events = [[]]*self.max_nch
        self.nch=0

        # Iterate all event in the midi and extract to 16 channel form
        for track in self.tracks:
            for msg in track:
                try:
                    channel = msg.channel
                    events[channel].append(msg)
                    self.nch=channel+1
                except AttributeError:
                    try:
                        if type(msg) != type(mido.UnknownMetaMessage):
                            self.meta[msg.type] = msg.dict()
                        else:
                            pass
                    except:
                        print("error", type(msg))
        
        return events

    def get_roll(self, events, verbose=False):
        """
        Convert event (channel) data to piano roll data
        """
        length_ticks = self.get_total_ticks()  # get total length in tick unit

        roll = np.zeros(
            (self.nch, 128, length_ticks // self.sr), dtype="int8")
        register_note = [int(-1)]*128         # register the state (on/off) of each key
        register_timbre = np.ones(self.nch)  # register the state (program_change) of each channel
        for idx, channel in enumerate(events):
            time_counter = 0
            volume = 100

            if verbose:
                print("channel", idx, "start")

            for msg in channel:
                if msg.type == "control_change":
                    if msg.is_cc(7):  # if msg.control == 7: Main Volume
                        volume = msg.value //127  # [0, 127]

                    if msg.is_cc(11):  # if msg.control == 11: Expression Controller
                        # volume[0,127] x expression[0,127]/127
                        volume *= msg.value // 127

                if msg.type == "program_change":
                    register_timbre[idx] = msg.program
                    if verbose:
                        print("channel", idx, "pc", msg.program, "time",
                              time_counter, "duration", msg.time)

                if msg.type == "note_on":
                    if verbose:
                        print("on ", msg.note, "time", time_counter,
                              "duration", msg.time, "velocity", msg.velocity)

                    # note_on_start_time = time_counter // self.sr
                    note_on_end_time = (time_counter + msg.time) // self.sr
                    intensity = volume * msg.velocity // 127

                    if register_note[msg.note] != -1:  # not after note_off
                        last_end_time, last_intensity = register_note[msg.note]
                        roll[idx, msg.note,
                             last_end_time:note_on_end_time] = last_intensity

                    register_note[msg.note] = (note_on_end_time, intensity)

                if msg.type == "note_off":
                    if verbose:
                        print("off", msg.note, "time", time_counter,
                              "duration", msg.time, "velocity", msg.velocity)

                    # note_off_start_time = time_counter // self.sr
                    note_off_end_time = (time_counter + msg.time) // self.sr
                    last_end_time, last_intensity = register_note[msg.note]
                    roll[idx, msg.note,
                         last_end_time:note_off_end_time] = last_intensity

                    register_note[msg.note] = -1  # reinitialize register

                time_counter += msg.time

            # if there is a note not closed at the end of a channel, close it
            for key, data in enumerate(register_note):
                if data != -1:
                    note_on_end_time = data[0]
                    intensity = data[1]
                    # print(key, note_on_end_time)
                    note_off_start_time = time_counter // self.sr
                    roll[idx, key, note_on_end_time:] = intensity
                register_note[idx] = -1

        return roll

    def _grp_init(self, figsize=(15, 9), xlim=None, ylim=None, bgcolor='black'):
        """
        Display basic information and initialize graphics. 
        Called by draw_roll()
        """

        # change unit of time axis from ticks to seconds
        length_ticks = self.get_total_ticks()
        length_seconds = mido.tick2second(
            length_ticks, self.ticks_per_beat, self.get_tempo())
        ticks_per_sec = length_ticks/length_seconds

        print("# of channels: ", self.nch)
        print("Tick length: {} [ticks]".format(length_ticks))
        print("Time length: {} [s]".format(length_seconds))
        print("ticks/beat: ", self.ticks_per_beat)
        print("ticks/second: ", ticks_per_sec)

        # Initialize graphics
        plt.rcParams["font.size"] = 20
        fig = plt.figure(figsize=figsize)
        ax = fig.add_subplot(111)
        ax.axis("equal")
        ax.set_facecolor(bgcolor)

        # set x-range and define xtick interval
        if xlim != None:
            length_seconds = xlim[1]-xlim[0]

        xticks_interval_sec = length_seconds // 10 if length_seconds > 10 else length_seconds/10
        xticks_interval = mido.second2tick(
            xticks_interval_sec, self.ticks_per_beat, self.get_tempo()) / self.sr  # [ticks/interval]
        print("xticks_interval_sec: ", xticks_interval_sec)
        print("xticks_interval: {} [ticks/label]".format(xticks_interval))

        nxticks = int(length_ticks//xticks_interval)
        plt.xticks(
            [int(x * xticks_interval) for x in range(nxticks)],
            [round(x * xticks_interval_sec, 2) for x in range(nxticks)]
        )
        plt.yticks([y*self.nch for y in range(8)],
                   [y*self.nch for y in range(8)])

        ax.set_xlabel("time [s]")
        ax.set_ylabel("note")
        if xlim != None:
            ticks_per_sec = xticks_interval/xticks_interval_sec
            print("ticks/second 2:", ticks_per_sec)
            ax.set_xlim(np.array(xlim)*ticks_per_sec)

        if ylim != None:
            ax.set_ylim(ylim)

        return fig, ax

    def draw_roll(self, figsize=(15, 9), xlim=None, ylim=None, bgcolor='black', colorbar=False):
        # define color maps
        transparent = colorConverter.to_rgba(bgcolor)
        colors = [
            mpl.colors.to_rgba(mpl.colors.hsv_to_rgb(
                (i / self.nch, 1, 1)), alpha=1)
            for i in range(self.nch)
        ]
        cmaps = [
            mpl.colors.LinearSegmentedColormap.from_list(
                'my_cmap', [transparent, colors[i]], 128)
            for i in range(self.nch)
        ]

        """
        make look up table (LUT) data like (K=3)
            array([[0. , 0. , 0. , 0. ],
                [0.5, 0. , 0. , 0.2],
                [1. , 0. , 0. , 0.4],
                [0. , 0. , 0. , 0.6],
                [1. , 0. , 0. , 0.8],
                [0. , 0. , 0. , 1. ]])
            The first 3 rows are colormap, and the last 3 rows are the colours
            for data low and high out-of-range values and for masked values.
            https://stackoverflow.com/questions/18035411/meaning-of-the-colormap-lut-list-in-matplotlib-color
        """
        for i in range(self.nch):
            cmaps[i]._init()
            # create look up table (_lut array) with rgba values
            # 3 extra rows are necessary (see the example above)
            alphas = np.linspace(0, 1, cmaps[i].N + 3)
            cmaps[i]._lut[:, -1] = alphas

        # create and stack piano roll image on ax1
        fig, ax1 = self._grp_init(figsize=figsize, xlim=xlim, ylim=ylim, bgcolor=bgcolor)
        for i in range(self.nch):
            try:
                ax1.imshow(self.roll[i], origin="lower",
                          interpolation='nearest', cmap=cmaps[i], aspect='auto')
            except IndexError:
                pass

        # draw color bar
        if colorbar:
            cmap = mpl.colors.LinearSegmentedColormap.from_list(
                'my_cmap', colors, self.nch)
            ax2 = fig.add_axes([0.1, 0.9, 0.8, 0.05])
            cbar = mpl.colorbar.ColorbarBase(ax2, cmap=cmap,
                                             orientation='horizontal',
                                             ticks=list(range(self.nch)))
        # ax1.set_title(self.fpath.name)
        # plt.draw()
        # plt.ion()
        # plt.savefig("outputs/"+self.fpath.name+".png", bbox_inches="tight")
        # plt.show(block=True)


def main():
    dir = "data/pedb2_v0.0.1.b/"
    #target="bac-inv001-o-p2"
    target = "bac-wtc101-p-a-p1"
    path = "{0}/{1}/{1}.mid".format(dir, target)
    mid = MidiFile(path)

    # events = mid.get_events()
    # roll = mid.get_roll(verbose=False)

    mid.draw_roll(figsize=(18, 6), xlim=[2, 15], ylim=[44, 92], bgcolor='black', colorbar=False)
    #mid.draw_roll(figsize=(18,6), colorbar=False)


if __name__ == "__main__":
    main()