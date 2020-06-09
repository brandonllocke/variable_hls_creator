import argparse
import os

from pymediainfo import MediaInfo

class File:
    def __init__(self, path):
       self.path = path
       self.basename = os.path.basename(self.path)
       self.name, self.ext = os.path.splitext(self.basename)
       self._video_track = None
       self._audio_track = None

    def _parse_track(self, kind, attribute):
        media_info = MediaInfo.parse(self.path)
        for track in media_info.tracks:
            if track.track_type == kind:
                setattr(self, attribute, track.to_data())

    def _get_video_attribute(self, kind):
        if self._video_track is not None:
            return self._video_track.get(kind, None)
        else:
            self._parse_track('Video', '_video_track')
            return self._get_video_attribute(kind)

    def _get_audio_attribute(self, kind):
        if self._audio_track is not None:
            return self._audio_track.get(kind, None)
        else:
            self._parse_track('Audio', '_audio_track')
            return self._get_audio_attribute(kind)

    @property
    def is_a_video_file(self):
        supported_formats = ['.mkv', '.ogm', '.avi',
                '.mpeg', '.mpg', '.vob', '.mp4',
                '.mpgv', '.mpv', '.m1v', '.m2v',
                '.asf', '.wmv', '.qt', '.mov', '.ifo']
        return self.ext.lower() in supported_formats

    @property
    def height(self):
        return self._get_video_attribute('height')

    @property
    def width(self):
        return self._get_video_attribute('width')

    @property
    def vbitrate(self):
        nominal_bit_rate = self._get_video_attribute('nominal_bit_rate')
        if nominal_bit_rate is not None:
            return nominal_bit_rate
        return self._get_video_attribute('bit_rate')

    @property
    def abitrate(self):
        maximum_bit_rate = self._get_audio_attribute('maximum_bit_rate')
        if maximum_bit_rate is not None:
            return maximum_bit_rate
        return self._get_audio_attribute('bit_rate')


class Directory:
    def __init__(self):
        pass

class FilePath:
    def __init__(self, arg):
        self.absolute = os.path.abspath(arg)

    @property
    def exists(self):
        return os.path.exists(self.absolute)

    @property
    def is_dir(self):
        return os.path.isdir(self.absolute)

    @property
    def is_file(self):
        return os.path.isfile(self.absolute)

def main():
    parser = argparse.ArgumentParser(description='''Process a video file or
                                     group of video files in a directory and
                                     convert them to hls format.''')
    parser.add_argument('-p', '--path', nargs='?', required=True,
                        help='''The path to the file or directory for
                         converting.''')
    parser.add_argument('-r', '--recursive', action='store_true',
                        help='''Scan directory recursively and convert
                         all found files.''')
    parser.add_argument('-s', '--single-version', action='store_true',
                        help='''Only create a single version at the nearest
                         default size/bitrate.''')
    parser.add_argument('-n', '--no-convert', action='store_true',
                        help='''Do not scale or convert video at all.''')
    args = parser.parse_args()
    path = FilePath(args.path)
    if path.is_dir and path.exists and args.recursive:
        print('Is a dir')
    elif path.is_file and path.exists:
        file = File(path.absolute)
        print(file.abitrate)
    else:
        print('Either the file/directory doesn\'t exist or you called this on'
              ' a directory without calling "-r/--recursive".')


if __name__ == '__main__':
    main()
