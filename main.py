import argparse
import os

from ffmpy import FFmpeg
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


class Convert:

    # Based on: https://developer.roku.com/docs/specs/streaming.md#best-practices
    roku = {'1080_h': {'height': 1080, 'bitrate': 5800000},
            '1080_l': {'height': 1080, 'bitrate': 4300000},
            '720_h': {'height': 720, 'bitrate': 3500000},
            '720_l': {'height': 720, 'bitrate': 2750000},
            '404_h': {'height': 404, 'bitrate': 1750000},
            '404_l': {'height': 404, 'bitrate': 1100000},
            '288': {'height': 288, 'bitrate': 700000},
            '216': {'height': 216, 'bitrate': 400000}
            }
    roku_min = {'1080': {'height': 1080, 'bitrate': 4300000},
                '720': {'height': 720, 'bitrate': 2650000},
                '404': {'height': 404, 'bitrate': 1500000},
                '288': {'height': 288, 'bitrate': 800000},
                '216': {'height': 216, 'bitrate': 400000}
                }
    # Based on: https://www.linkedin.com/pulse/five-views-your-encoding-ladder-jan-ozer/
    apple = {'1080_h': {'height': 1080, 'bitrate': 7800000},
             '1080_m': {'height': 1080, 'bitrate': 6000000},
             '1080_l': {'height': 1080, 'bitrate': 4500000},
             '720': {'height': 720, 'bitrate': 3000000},
             '540': {'height': 540, 'bitrate': 2000000},
             '432': {'height': 432, 'bitrate': 1100000},
             '360': {'height': 360, 'bitrate': 365000},
             '234': {'height': 234, 'bitrate': 145000}
            }

    conversion_types = {'roku': roku,
                        'roku_min': roku_min,
                        'apple': apple,
                        }

    def __init__(self, file, single=False, schema='apple'):
        self.file = file
        self.schema = schema
        if single:
            self.single_version()
        else:
            self.multi_version()

    @property
    def single_output(self):
        return (
            f"-c:v libx264 -b:v {self.file.vbitrate} -c:a aac "
            f"-b:a {self.file.abitrate} -profile:v baseline "
            f"-level 3.0 -start_number 0 "
            f"-hls_time 10 -hls_list_size 0 -f hls"
            )


    @property
    def _conversion_dir(self):
        con_dir = str(self.file.path.split(
            self.file.basename)[0]) + str(self.file.name) + '/'
        if not os.path.exists(con_dir):
            os.mkdir(con_dir)
        return  con_dir

    @property
    def master_pl_path(self):
        return str(self.file.name) + '_master.m3u8'

    @property
    def boilerplate(self):
        return (f"-c:a aac -b:a {self.file.abitrate} -f hls "
                f"-master_pl_name {self.master_pl_path} "
                f"-hls_segment_filename '{self._conversion_dir}"
                f"{self.file.name}_%v_%03d.ts'"
               )

    @property
    def multi_output_path(self):
        return str(self._conversion_dir) + str(self.file.name) + '_%v.m3u8'

    @property
    def single_output_path(self):
        return str(self._conversion_dir) + str(self.file.name) + '.m3u8'

    @property
    def multi_output(self):
        var_num = 0
        variant_stream_bitrates = []
        stream_map = []
        var_stream_map = []
        conversion_schema = self.conversion_types[self.schema]
        for variant in conversion_schema:
            height = conversion_schema[variant]['height']
            bitrate = conversion_schema[variant]['bitrate']
            if (height <= self.file.height) and (
                    bitrate <= self.file.vbitrate):
                this_stream_bitrate = (
                        f"-b:v:{var_num} {bitrate} -s:v:{var_num} "
                        f"{int(height * 1.77777777777777777777777777777)}"
                        f"x{height} -c:v:{var_num} libx264"
                        )
                this_stream_map = f"v:{var_num},a:{var_num},name:{variant}"
                this_map = f"-map 0:v -map 0:a"
                variant_stream_bitrates.append(this_stream_bitrate)
                var_stream_map.append(this_stream_map)
                stream_map.append(this_map)
                var_num += 1
        variant_bitrate_str = ' '.join(variant_stream_bitrates)
        variant_map_str = ' '.join(var_stream_map)
        stream_map_str = ' '.join(stream_map)
        return (f'{variant_bitrate_str} {stream_map_str} '
                f'-var_stream_map "{variant_map_str}" {self.boilerplate}'
               )

    def single_version(self):
        ffmpeg = FFmpeg(inputs={str(self.file.path): None},
                        outputs={self.single_output_path: self.single_output}
                        )
        ffmpeg.run()
        return True

    def multi_version(self):
        ffmpeg = FFmpeg(inputs={str(self.file.path): None},
                        outputs={self.multi_output_path: self.multi_output}
                       )
        ffmpeg.run()
        return True

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
    parser.add_argument('-l', '--variant_ladder', nargs='?',
                        help='''Built variant ladder to use. Defaults to Apple.''')
    args = parser.parse_args()
    path = FilePath(args.path)
    if path.is_dir and path.exists and args.recursive:
        print('Is a dir')
    elif path.is_file and path.exists:
        Convert(File(path.absolute), single=args.single_version, schema=args.variant_ladder)
    else:
        print('Either the file/directory doesn\'t exist or a directory'
              ' was called without the "-r/--recursive" flag.')


if __name__ == '__main__':
    main()
