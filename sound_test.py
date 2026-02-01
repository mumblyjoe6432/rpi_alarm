import vlc
import time
import threading

sound = '/home/gabe/Music/alarms/mixkit-battleship-alarm-1001.mp3'
sound_filepath = '/home/gabe/Music/music_playlist/Hoobastank - Inside Of You.mp3'
sound_filepath = '/home/gabe/Music/golden_kpop_demon_hunters.mp3'

class VLCPlayer:
    def __init__(self, file_path):
        self.file_path = file_path
        self.player = vlc.MediaPlayer(file_path)
        self.play_thread = None
        self.stop_event = threading.Event()

    def _play(self):
        self.player.play()
        while not self.stop_event.is_set() and not self.player.get_state() == vlc.State.Ended:
            time.sleep(1)
        self.player.stop()

    def play(self):
        if not self.play_thread or not self.play_thread.is_alive():
            self.stop_event.clear()
            self.play_thread = threading.Thread(target=self._play)
            self.play_thread.start()

    def stop(self):
        if self.play_thread and self.play_thread.is_alive():
            self.stop_event.set()
            self.play_thread.join()

# Example usage:
audio_file_path = sound_filepath
player = VLCPlayer(audio_file_path)

# Start playing
player.play()
time.sleep(5)  # Play for 5 seconds (adjust as needed)

# Kill the playback (terminate the thread)
player.kill()



if __name__ == "__main__":
    ps()