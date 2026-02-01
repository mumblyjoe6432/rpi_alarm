import vlc
import logging
import threading
import os, time
import random

class sound_blaster:
    """
    Description:
    This class controls the sound for the Rpi
    
    Usage:
    music_handle = sound_blaster(music_dir, alarm_filepath)
    You can then control the PWM by:
    led_handle.set_pwm(50) #Set a duty cycle of 50

    Inputs:
    music_dir - The path to a directory with music mp3s
    alarm_filepath - The path to an mp3 with the music for the alarm

    Outputs:
    None
    """

    def __init__(self, music_dir, alarm_filepath):
        """
        Description:
        Initialization of the switch class
        
        Inputs:
        music_dir - The path to a directory with music mp3s
        alarm_filepath - The path to an mp3 with the music for the alarm

        Outputs:
        None
        """

        self.music_dir = music_dir
        self.alarm_filepath = alarm_filepath
        self.instance = vlc.Instance()
        self.media_list_player = self.instance.media_list_player_new()
        self.play_thread = None
        logging.info("Sound controller initialized")

    def __del__(self):
        """
        Description:
        Destructor for the class, ensures all threads are stopped
        
        Inputs:
        None

        Outputs:
        None
        """

        self.stop()

    def _play(self, file_list, repeat_count=0, total_playtime=0):
        """
        Description:
        Plays music files in order. Can determine a total time to play or a number of
        repeats of the music
        
        Inputs:
        file_list - A list of the music mp3s
        repeat_count - Number of times to play the music
        total_playtime - Total time to play the music, overrides the repeat_count

        Outputs:
        None
        """

        total_duration = 0
        self.media_list = self.instance.media_list_new()
        self.media_list_player.set_media_list(self.media_list)
        for file_path in file_list:
            media = self.instance.media_new(file_path)
            self.media_list.add_media(media)
            total_duration += media.get_duration() / 1000  # Duration in seconds

        self.media_list_player.set_playback_mode(vlc.PlaybackMode.loop)  # Set loop mode
        self.media_list_player.play()

        if total_playtime > 0:
            # If total playtime is set, just wait for that total playtime
            time.sleep(total_playtime)
        elif repeat_count > 0:
            # If repeat_count is set, wait for the total duration of the playlist multiplied by the repeat count
            time.sleep(total_duration * repeat_count)

    def play_files(self, file_list, shuffle=False, repeat_count=0, total_playtime=0):
        """
        Description:
        Starts the thread that plays music
        
        Inputs:
        file_list - A list of the music mp3s
        shuffle - Will shuffle the music if True
        repeat_count - Number of times to play the music
        total_playtime - Total time to play the music, overrides the repeat_count

        Outputs:
        None
        """

        if shuffle:
            random.shuffle(file_list)
        if not self.play_thread or not self.play_thread.is_alive():
            logging.info(f"Started the music player")
            self.play_thread = threading.Thread(target=self._play, args=(file_list, repeat_count, total_playtime))
            self.play_thread.start()

    def stop(self):
        """
        Description:
        Stops the thread that is playing music
        
        Inputs:
        None

        Outputs:
        None
        """

        logging.info(f"Stopped the music player")
        self.media_list_player.stop()

    def is_playing(self):
        """
        Description:
        Asks if music is being played
        
        Inputs:
        None

        Outputs:
        True if music is playing, False if not
        """

        return self.media_list_player.get_state() == vlc.State.Playing
    
    def play_directory(self, directory, shuffle=True):
        """
        Description:
        Plays music from a directory
        
        Inputs:
        directory - A directory with only mp3 files inside to be played
        shuffle - True if random order is desired

        Outputs:
        None
        """

        song_filenames = os.listdir(directory)
        song_filepaths = []
        for song_filename in song_filenames:
            song_filepaths.append(directory + '/' + song_filename)
        self.play_files(song_filepaths, shuffle=shuffle)
        logging.info(f"Music started from directory {directory}")

    def play_music_dir(self):
        """
        Description:
        Plays the music from the music_dir that was specified when the class
        was instantiated
        
        Inputs:
        None

        Outputs:
        None
        """

        logging.info(f"Playing music")
        self.play_directory(self.music_dir)

    def play_alarm(self):
        """
        Description:
        Plays the file that was specified as the alarm_filepath when the
        class was instantiated
        
        Inputs:
        None

        Outputs:
        None
        """

        logging.info(f"Playing alarm sound")
        self.play_files([self.alarm_filepath], total_playtime=3600)
    
    def _set_volume(self, level):
        """
        Description:
        Private helper to clamp and set the VLC audio volume.
        
        Inputs:
        level - requested volume (0–100)
        
        Outputs:
        None
        """
        try:
            level_val = int(level)
        except (TypeError, ValueError):
            logging.warning("sound_blaster: invalid volume value passed (ignored): %r", level)
            return

        # clamp
        if level_val < 0:
            logging.warning("sound_blaster: volume value less than 0: %r. Volume will be set to 0", level)
            level_val = 0
        elif level_val > 100:
            logging.warning("sound_blaster: volume value more than 100: %r. Volume will be set to 100", level)
            level_val = 100

        try:
            self.media_list_player.get_media_player().audio_set_volume(level_val)
        except Exception:
            # don’t crash if VLC isn’t ready
            pass

        self._volume = level_val
        logging.info(f"Volume set to {level_val}%")

    @property
    def volume(self):
        """
        Description:
        Current audio volume (0–100). Returns the last value actually set.
        
        Inputs:
        None

        Outputs:
        volume - int from 0–100
        """
        return getattr(self, "_volume", 50)

    @volume.setter
    def volume(self, value):
        """
        Description:
        Set audio volume (0–100). Automatically clamps out-of-range values and updates VLC.
        
        Inputs:
        value - new volume (0–100)

        Outputs:
        None
        """
        self._set_volume(value)
