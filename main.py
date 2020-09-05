import argparse
import faster_than_walk
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
        self._general_info = None

    def _parse_track(self, kind, attribute):
        media_info = MediaInfo.parse(self.path)
        for track in media_info.tracks:
            if track.track_type == kind:
                setattr(self, attribute, track.to_data())

    def _get_video_attribute(self, kind):
        if self._video_track is not None:
            return self._video_track.get(kind, None)
        self._parse_track('Video', '_video_track')
        return self._get_video_attribute(kind)

    def _get_audio_attribute(self, kind):
        if self._audio_track is not None:
            return self._audio_track.get(kind, None)
        self._parse_track('Audio', '_audio_track')
        return self._get_audio_attribute(kind)

    def _get_general_attribute(self, kind):
        if self._general_info is not None:
            return self._general_info.get(kind, None)
        self._parse_track('General', '_general_info')
        return self._get_general_attribute(kind)

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
    def vbitrate(self):
        nominal_bit_rate = self._get_video_attribute('nominal_bit_rate')
        if nominal_bit_rate is not None:
            return nominal_bit_rate
        video_bit_rate = self._get_video_attribute('bitrate')
        if video_bit_rate is not None:
            return video_bit_rate
        overall_bitrate = self._get_general_attribute('overall_bit_rate')
        return overall_bitrate

    @property
    def abitrate(self):
        maximum_bit_rate = self._get_audio_attribute('maximum_bit_rate')
        if maximum_bit_rate is not None:
            return maximum_bit_rate
        bit_rate = self._get_audio_attribute('bit_rate')
        if bit_rate is not None:
            return bit_rate
        return 256000

    @property
    def aspect_ratio(self):
        ratio = self._get_video_attribute('display_aspect_ratio')
        return float(ratio)


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
                f"-master_pl_name '{self.master_pl_path}' -hls_list_size 0 "
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
        for variant in self.valid_variants:
            variant_stream_bitrates.append(variant.stream_bitrate(var_num))
            var_stream_map.append(variant.stream_map(var_num))
            stream_map.append(variant.map())
            var_num += 1
        return (
            f'{str(" ".join(variant_stream_bitrates))} '
            f'{str(" ".join(stream_map))} '
            f'-var_stream_map "{str(" ".join(var_stream_map))}" '
            f'{self.boilerplate}'
        ) 
    
    @property
    def valid_variants(self):
        valid_variants = []
        conversion_schema = self.conversion_types[self.schema]
        for variant in conversion_schema:
            variant = Variant(self.file, variant, conversion_schema[variant], self._conversion_dir)
            if variant.is_valid:
                valid_variants.append(variant)
        return valid_variants

    def single_version(self):
        ffmpeg = FFmpeg(inputs={str(self.file.path): None},
                        outputs={self.single_output_path: self.single_output}
                        )
        ffmpeg.run()
        return True

    def multi_version(self):
        self.multi_version_ffmpeg()
        for variant in self.valid_variants:
            variant.move_to_own_folder()
            variant.edit_master_pl(self.master_pl_path)

    def multi_version_ffmpeg(self):
        ffmpeg = FFmpeg(inputs={str(self.file.path): None},
                        outputs={self.multi_output_path: self.multi_output}
                       )
        ffmpeg.run()


class Variant:
    def __init__(self, file, variant, info, conversion_dir):
        self.file = file
        self.name = variant
        self.height = info['height']
        self.bitrate = info['bitrate']
        self.conversion_dir = conversion_dir
        self.folder = f'{self.conversion_dir}/{self.name}'

    @property
    def width(self):
        width = int(int(self.height) * self.file.aspect_ratio)
        if width % 2 == 0:
            return width
        return width + 1

    @property
    def is_valid(self):
        return (self.height <= self.file.height) and (
            self.bitrate <= self.file.vbitrate)

    def stream_bitrate(self, var_num):
        return (f"-b:v:{var_num} {self.bitrate} -s:v:{var_num} "
                f"{self.width}x{self.height} -c:v:{var_num} libx264")

    def stream_map(self, var_num):
        return f"v:{var_num},a:{var_num},name:{self.name}"

    def map(self):
        return f"-map 0:v -map 0:a"

    def move_to_own_folder(self):
        if not os.path.isdir(self.folder):
            os.mkdir(self.folder)
        files = self.get_files()
        for file in files:
            os.rename(file, f'{self.folder}/{os.path.basename(file)}')

    def get_files(self):
        files = []
        for file in faster_than_walk.walk(str(self.conversion_dir)):
            if file.endswith('ts'):
                if f'_{self.name}_' in os.path.basename(file):
                    files.append(file)
            elif file.endswith('m3u8'):
                if f'_{self.name}' in os.path.basename(file):
                    files.append(file)
        return files

    def edit_master_pl(self, master_pl_path):
        with open(f'{self.conversion_dir}/{master_pl_path}', 'r+') as master_pl:
            content = master_pl.read()
            old_path = f'{self.file.name}_{self.name}.m3u8'
            new_path = f'{self.name}/{self.file.name}_{self.name}.m3u8'
            content = content.replace(old_path, new_path)
            master_pl.seek(0)
            master_pl.write(content)
            master_pl.truncate()


class Directory:
    def __init__(self, path):
        self.path = path
        self.files = self._parse_files()

    def _parse_files(self):
        files = []
        for file in faster_than_walk.walk(str(self.path)):
            file = File(file)
            if file.is_a_video_file:
                files.append(file)
        return files

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
                        help='''Built variant ladder to use. 
                        Defaults to Apple.''')
    args = parser.parse_args()
    path = FilePath(args.path)
    if args.variant_ladder is None:
        args.variant_ladder = 'apple'
    if path.is_dir and path.exists and args.recursive:
        directory = Directory(path.absolute)
        for file in directory.files:
            Convert(file, single=args.single_version, 
                    schema=args.variant_ladder)
    elif path.is_file and path.exists:
        file = File(path.absolute)
        if file.is_a_video_file:
            Convert(file, single=args.single_version,
                    schema=args.variant_ladder)
        else:
            print('This isn\'t a supported video type.')
    else:
        print('Either the file/directory doesn\'t exist or a directory'
              ' was called without the "-r/--recursive" flag.')


if __name__ == '__main__':
    main()
