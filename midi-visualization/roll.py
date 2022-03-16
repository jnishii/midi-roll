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
        self.nchannel = 16

        mido.MidiFile.__init__(self, midifile)
        #self.midifile = re.split('/',midifile)[-1]
        fpath=Path(midifile)
        self.midifile=fpath.stem

        self.events = self.get_events(verbose)
        self.roll = self.get_roll(self.events)

        return self

    def get_tempo(self):
        try:
            return self.meta["set_tempo"]["tempo"]
        except:
            return 500000

    def get_total_ticks(self):
        max_ticks = 0
        for channel in range(self.nchannel):
            ticks = sum(msg.time for msg in self.events[channel])
            if ticks > max_ticks:
                max_ticks = ticks
        return max_ticks

    def get_events(self, verbose=False):
        """
        Extract self.nchannel (default: 16) channel data from MIDI and return a list.
        Lyrics and meta data used in extra channels are not include in the list.

        Returns:
            list : [[ch1],[ch2]....[ch16]]
        """
        if verbose:
            print(self)

        events = [[] for x in range(self.nchannel)]

        # Iterate all event in the midi and extract to 16 channel form
        for track in self.tracks:
            for msg in track:
                try:
                    channel = msg.channel
                    events[channel].append(msg)
                except AttributeError:
                    try:
                        if type(msg) != type(mido.UnknownMetaMessage):
                            self.meta[msg.type] = msg.dict()
                        else:
                            pass
                    except:
                        print("error",type(msg))

        return events

    def get_roll(self, events, verbose=False):
        """
        Convert event (channel) data to piano roll
        """
        length = self.get_total_ticks() # get total length in tick unit

        roll = np.zeros((self.nchannel, 128, length // self.sr), dtype="int8")
        note_register = [int(-1) for x in range(128)]   # array for the state (on/off) of each key
        timbre_register = [1 for x in range(self.nchannel)]        # array for the state (program_change) of each channel

        for idx, channel in enumerate(events):
            time_counter = 0
            volume = 100
            # Volume would change by control change event (cc) cc7 & cc11
            # Volume 0-100 is mapped to 0-127

            if verbose:
                print("channel", idx, "start")

            for msg in channel:
                if msg.type == "control_change":
                    #if msg.control == 7: # Main Volume [0,127]
                    if msg.is_cc(7): # Main Volume
                        volume = msg.value # [0, 127]
                    
                    #if msg.control == 11: # Expression Controller
                    if msg.is_cc(11): # Expression Controller [0,127]
                        volume = volume * msg.value // 127 # volume[0,127] x expression[0,100](%)

                if msg.type == "program_change":
                    timbre_register[idx] = msg.program
                    if verbose:
                        print("channel", idx, "pc", msg.program, "time", time_counter, "duration", msg.time)

                if msg.type == "note_on":
                    if verbose:
                        print("on ", msg.note, "time", time_counter, "duration", msg.time, "velocity", msg.velocity)
                    
                    # note_on_start_time = time_counter // self.sr
                    note_on_end_time = (time_counter + msg.time) // self.sr
                    intensity = volume * msg.velocity // 127

                    if note_register[msg.note] != -1: # first sound for each note
                        last_end_time = note_register[msg.note][0]  # note_on end time of last note
                        last_intensity = note_register[msg.note][1] # intensity of last note 
                        
                        roll[ idx, msg.note, last_end_time:note_on_end_time ] = last_intensity

                    note_register[msg.note] = (note_on_end_time, intensity)

                if msg.type == "note_off":
                    if verbose:
                        print("off", msg.note, "time", time_counter, "duration", msg.time, "velocity", msg.velocity)
                    
                    # note_off_start_time = time_counter // self.sr
                    note_off_end_time = (time_counter + msg.time) // self.sr
                    
                    last_end_time = note_register[msg.note][0] # note_on end time of last note
                    last_intensity = note_register[msg.note][1] # intensity of last note 
					
                    # fill in color
                    roll[ idx, msg.note, last_end_time:note_off_end_time ] = last_intensity

                    note_register[msg.note] = -1  # reinitialize register

                time_counter += msg.time

            # if there is a note not closed at the end of a channel, close it
            for key, data in enumerate(note_register):
                if data != -1:
                    note_on_end_time = data[0]
                    intensity = data[1]
                    # print(key, note_on_end_time)
                    note_off_start_time = time_counter // self.sr
                    roll[idx, key, note_on_end_time:] = intensity
                note_register[idx] = -1

        return roll

    def get_roll_image(self):
        plt.ioff()

        K = self.nchannel

        transparent = colorConverter.to_rgba('black')
        colors = [mpl.colors.to_rgba(mpl.colors.hsv_to_rgb((i / K, 1, 1)), alpha=1) for i in range(K)]
        cmaps = [mpl.colors.LinearSegmentedColormap.from_list('my_cmap', [transparent, colors[i]], 128) for i in
                 range(K)]

        for i in range(K):
            cmaps[i]._init()  # create the _lut array, with rgba values
            # create your alpha array and fill the colormap with them.
            # here it is progressive, but you can create whathever you want
            alphas = np.linspace(0, 1, cmaps[i].N + 3)
            cmaps[i]._lut[:, -1] = alphas

        fig = plt.figure(figsize=(4, 3))
        a1 = fig.add_subplot(111)
        a1.axis("equal")
        a1.set_facecolor("black")

        array = []

        for i in range(K):
            try:
                img = a1.imshow(self.roll[i], interpolation='nearest', cmap=cmaps[i], aspect='auto')
                array.append(img.get_array())
            except IndexError:
                pass
        return array

    def _grp_init(self, figsize=(15,9), xlim=None, ylim=None):
        plt.rcParams["font.size"] = 20
        fig = plt.figure(figsize=figsize)
        ax = fig.add_subplot(111)
        ax.axis("equal")
        ax.set_facecolor("black")

        # change unit of time axis from tick to second
        tick = self.get_total_ticks()
        second = mido.tick2second(tick, self.ticks_per_beat, self.get_tempo())
        print("filename: ", self.filename)
        print("Tick length: {} [ticks]".format(tick))
        print("Time length: {} [s]".format(second))
        print("ticks/beat: ", self.ticks_per_beat)

        ticks_per_sec = tick/second
        print("ticks/second: ", ticks_per_sec)

        if xlim!=None:
            second=xlim[1]-xlim[0]

        x_label_period_sec = second // 10 if second > 10 else second/10 # [ms]
        print("x_label_period_sec: ", x_label_period_sec)

        x_label_interval = mido.second2tick(x_label_period_sec, self.ticks_per_beat, self.get_tempo()) / self.sr
        print("x_label_interval: {} [ticks/label]".format(x_label_interval))
 
        nxlabel=int(tick//x_label_interval)
        plt.xticks(
            [int(x * x_label_interval) for x in range(nxlabel)], 
            [round(x * x_label_period_sec, 2) for x in range(nxlabel)]
            )

        # change scale and label of y axis
        plt.yticks([y*self.nchannel for y in range(8)], [y*self.nchannel for y in range(8)])
        ax.set_xlabel("time [s]")
        if xlim!=None:
            ticks_per_sec=x_label_interval/x_label_period_sec
            print("ticks/second 2:", ticks_per_sec)
            ax.set_xlim(np.array(xlim)*ticks_per_sec)

        if ylim!=None:
            ax.set_ylim(ylim)

        return fig, ax

    def draw_roll(self, figsize = (15,9), xlim=None, ylim=None, colorbar=False):
        #roll = self.get_roll()
        fig, a1=self._grp_init(figsize=figsize, xlim=xlim, ylim=ylim)

        # build colors
        channel_nb = self.nchannel
        transparent = colorConverter.to_rgba('black')
        colors = [
            mpl.colors.to_rgba(mpl.colors.hsv_to_rgb((i / channel_nb, 1, 1)), alpha=1) 
            for i in range(channel_nb)
            ]
        cmaps = [
            mpl.colors.LinearSegmentedColormap.from_list('my_cmap', [transparent, colors[i]], 128) 
            for i in range(channel_nb)
            ]

        # build color maps
        for i in range(channel_nb):
            cmaps[i]._init()
            # create your alpha array and fill the colormap with them.
            alphas = np.linspace(0, 1, cmaps[i].N + 3)
            # create the _lut array, with rgba values
            cmaps[i]._lut[:, -1] = alphas


        # draw piano roll and stack image on a1
        for i in range(channel_nb):
            try:
                a1.imshow(self.roll[i], origin="lower", interpolation='nearest', cmap=cmaps[i], aspect='auto')
            except IndexError:
                pass

        # draw color bar
        if colorbar:
            colors = [mpl.colors.hsv_to_rgb((i / channel_nb, 1, 1)) for i in range(channel_nb)]
            cmap = mpl.colors.LinearSegmentedColormap.from_list('my_cmap', colors, self.nchannel)
            a2 = fig.add_axes([0.1, 0.9, 0.8, 0.05])
            cbar = mpl.colorbar.ColorbarBase(a2, cmap=cmap,
                                        orientation='horizontal',
                                        ticks=list(range(16)))
        a1.set_title(self.filename)
        plt.draw()
        plt.ion()
        plt.savefig("outputs/"+self.filename+".png", bbox_inches="tight")
        plt.show(block=True)



if __name__ == "__main__":
    dir="data/pedb2_v0.0.1.b/"
    #target="bac-inv001-o-p2"
    target="bac-wtc101-p-a-p1"
    path="{0}/{1}/{1}.mid".format(dir,target)
    mid = MidiFile(path)

    # events = mid.get_events()
    # roll = mid.get_roll(verbose=False)

    # draw piano roll by pyplot
    mid.draw_roll(figsize=(18,6),xlim=[2,15],ylim=[44,92],colorbar=False)
    #mid.draw_roll(figsize=(18,6), colorbar=False)
