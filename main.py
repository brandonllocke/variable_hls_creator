import argparse
import os

class File:
    def __init__(self):
        pass

class Directory:
    def __init__(self):
        pass

class Path:
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
    path = Path(args.path)
    if path.is_dir and path.exists:
        print('Is a dir')
    elif path.is_file and path.exists:
        print('Is a file')
    else:
        print('Either the file/directory doesn\'t exist or it\'s not ' +
              'the type of file that I can handle.')


main()
