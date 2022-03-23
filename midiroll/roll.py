import streamlit as st
import librosa
import librosa.display
import os
import mido
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.colors import colorConverter
import plotly.graph_objects as go
import plotly.express as px

from turtle import bgcolor
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
        Extract self.max_nch (default: 16) channel data from MIDI and return a list.
        Lyrics and meta data used in extra channels are not include in the list.

        Returns:
            list : [[ch1],[ch2]....[ch16]] # Note that empty channel is removed!
        """
        if verbose:
            print(self)

        mid = self
        events =  [[] for i in range(self.max_nch)]
        
        for track in mid.tracks:
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
                        print("error", type(msg))
        events = list(filter(None, events)) # remove emtpy channel
        self.nch = len(events)

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

        self.intensity_range = [100,0] # [min, max]
        self.note_range = [127,0] # [min, max]
        for idx, channel in enumerate(events):
            time_counter = 0
            volume = 100

            if verbose:
                print("channel", idx, "start")

            for msg in channel:
                if msg.type == "control_change":
                    if msg.is_cc(7):  # if msg.control == 7: Main Volume
                        volume = 100*msg.value //127  # [0, 100]
             
                    if msg.is_cc(11):  # if msg.control == 11: Expression Controller
                        # volume[0,100] x expression[0,127]/127
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
                    
                    if self.intensity_range[0] > intensity: # update minimum intensity
                        self.intensity_range[0] = intensity
                    if self.intensity_range[1] < intensity: # update maximum intensity
                        self.intensity_range[1] = intensity

                    if register_note[msg.note] != -1:  # not after note_off
                        last_end_time, last_intensity = register_note[msg.note]
                        roll[idx, msg.note,
                             last_end_time:note_on_end_time] = last_intensity

                    register_note[msg.note] = (note_on_end_time, intensity)

                    if self.note_range[0] > msg.note: # update minimum note
                        self.note_range[0] = msg.note
                    if  self.note_range[1] < msg.note: # update maximum note
                        self.note_range[1] = msg.note

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
                    # note_off_start_time = time_counter // self.sr
                    roll[idx, key, note_on_end_time:] = intensity
                register_note[idx] = -1

        return roll

    def _grp_init(self, figsize=(15, 9), xlim=None, ylim=None, bgcolor=bgcolor):
        """
        Display basic information and initialize graphics. 
        Called by draw_roll()
        """

        # change unit of time axis from ticks to seconds
        length_ticks = self.get_total_ticks()
        length_seconds = mido.tick2second(
            length_ticks, self.ticks_per_beat, self.get_tempo())
        ticks_per_sec = length_ticks/length_seconds

        st.sidebar.write('## midi file')

        st.sidebar.write("Num. of tracks: ", len(self.tracks))
        st.sidebar.write("Num. of active channels: ", self.nch)
        st.sidebar.write("intensity range [0, 100]: [{}, {}]".format(self.intensity_range[0], self.intensity_range[1]))
        st.sidebar.write("note range [0, 127]: [{}, {}]".format(self.note_range[0], self.note_range[1]))
        st.sidebar.write("ticks/beat: ", self.ticks_per_beat)
        st.sidebar.write("ticks/second: ", ticks_per_sec)
        st.sidebar.write("Tick length: [ticks]", length_ticks)
        st.sidebar.write("Time length [s]: ", length_seconds)
   
        xlim=st.sidebar.slider('Time range: ', min_value=0, max_value=int(length_seconds), value=(0,int(length_seconds)))

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
        plt.yticks([y*16 for y in range(8)], [y*16 for y in range(8)])

        ax.set_xlabel("time [s]")
        ax.set_ylabel("note")
        xlim_ticks=[0,length_ticks-1]
        if xlim != None:
            ticks_per_sec = xticks_interval/xticks_interval_sec
            print("ticks/second 2:", ticks_per_sec)
            xlim_ticks=np.array(xlim)*ticks_per_sec
            ax.set_xlim(xlim_ticks)

        if ylim == None:
            ylim=[0, 127]
        elif ylim == "Auto" or ylim == "auto":
            ylim=[self.note_range[0]-1, self.note_range[1]+1]
        ax.set_ylim(ylim)
            
        ax.set_xlabel("time [s]")
        ax.set_ylabel("note")
        
        #return fig, ax
        return fig, ax, xlim_ticks

    
    def _get_color_maps(self, cmap_list=None, bgcolor='black'):
        """ Define color map for each channel """
        if cmap_list==None:
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
        else:
            cmap = plt.cm.get_cmap(cmap_list)
            cmaps = [ cmap for i in range(self.nch) ]

        """
        make look up table (LUT) data, e.g., (K=3)
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
            alphas = np.linspace(0, 1, cmaps[i].N + 3) # about 3 extra rows, see the example above
            cmaps[i]._lut[:, -1] = alphas

        return cmaps   

    def draw_roll(self, figsize=(15, 9), xlim=None, ylim=None, cmap_list=None, bgcolor='black', colorbar=False):
        """Create piano roll image.

        Args:
            figsize (tuple or list): figure size
            
            xlim: Time range to be displayed [s]
                None (not specified) : Full range
                tuple or list : (xmin, xmax) [s]
            
            ylim: Range of notes to be displayed in vertical axis
                None (not specified) : Full range of notes
                "Auto" or "auto" : automatic range adjustment
                tuple or list : range of notes to be displayed [s]
 
            bgcolor (string): name of background color
            
            colorbar (boolean): enable colorbar of intensity
        """

        fig, ax1, xlim_ticks = self._grp_init(
            figsize=figsize, xlim=xlim, ylim=ylim, bgcolor=bgcolor)
        cmaps = self._get_color_maps(cmap_list=cmap_list, bgcolor=bgcolor)

        for i in range(self.nch):
            try:
                print("xlim_ticks", xlim_ticks)
                target_roll = self.roll[i, :, :int(xlim_ticks[1])]
                #target_roll = self.roll[i, :, :]

                max_intensity = np.max(np.array(target_roll))
                print("max_intensity:",max_intensity)
                im = ax1.imshow(self.roll[i], origin="lower",
                               interpolation='nearest', cmap=cmaps[i], aspect='auto', clim=[0, max_intensity])                
                
                if colorbar:
                    fig.colorbar(im)
            except IndexError:
                pass

        # draw color bar for channel color
        # if colorbar:
        #     cmap = mpl.colors.LinearSegmentedColormap.from_list(
        #         'my_cmap', colors, self.nch)
        #     ax2 = fig.add_axes([0.1, 0.9, 0.8, 0.05])
        #     cbar = mpl.colorbar.ColorbarBase(ax2, cmap=cmap,
        #                                      orientation='horizontal',
        #                                      ticks=list(range(self.nch)))
        
        ax1.set_title(self.fpath.name)
        plt.draw()
        plt.ion()
        with st.container():
            st.pyplot(fig)
        plt.savefig("outputs/"+self.fpath.name+".png", bbox_inches="tight")
        #plt.show(block=True)

def getfiles(folder_path):
    files = [f for f in os.listdir(folder_path)] # if f.endswith('.mid)]
    return (files)

def file_selector(folder_path):
    filenames = os.listdir(folder_path)
    selected_filename = st.selectbox('Select a file', filenames)
    return os.path.join(folder_path, selected_filename)

def show_wav(file):
    wav,sr = librosa.load(file)
    wav_seconds=int(len(wav)/sr)
    st.sidebar.write('## audio file')
    st.sidebar.write('sampling rate [Hz]: ', sr)
    st.audio(file)

def main():
    dir = "data/pedb2_v0.0.1.b/"
    #target="bac-inv001-o-p2"
    target = "bac-wtc101-p-a-p1"

    st.set_page_config(layout='wide')

    files = getfiles(dir)
    target = st.sidebar.selectbox('Select file to visualize', files)

    path_wav = "{0}/{1}/{1}.wav".format(dir, target)
    show_wav(path_wav)


    path_mid = "{0}/{1}/{1}.mid".format(dir, target)
    mid = MidiFile(path_mid)

    # events = mid.get_events()
    # roll = mid.get_roll(verbose=False)

    # cmap_list: colormap name
    # https://matplotlib.org/stable/tutorials/colors/colormaps.html
    #mid.draw_roll(figsize=(18, 6), xlim=[2, 15], ylim=[44, 92], cmap_list='Purples', bgcolor='white', colorbar=True)
    mid.draw_roll(figsize=(20, 4), xlim=None, ylim=[30,92], cmap_list='Purples', bgcolor='white', colorbar=None)

if __name__ == "__main__":
    main()
