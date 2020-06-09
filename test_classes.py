import os

from ffmpy import FFmpeg
from pathlib import Path
from main import File, FilePath

def create_test_video_file(tmp_path):
    directory = tmp_path / 'videos'
    if not os.path.exists(directory):
        directory.mkdir()
    file = directory / 'test.mp4'
    ff = FFmpeg(outputs={str(file): '-f lavfi -i smptebars -f lavfi -i anullsrc=channel_layout=stereo:sample_rate=44100 -t 2 -vf scale=1920:1080 -b:v 1000k -b:a 192k -minrate 192k -maxrate 192k'})
    ff.run()
    return file

def create_test_nonvideo_file(tmp_path):
    directory = tmp_path / 'videos'
    if not os.path.exists(directory):
        directory.mkdir()
    file = directory / 'test.txt'
    Path(file).touch()
    return file

def create_test_filepath(tmp_path):
    directory = tmp_path / 'directory'
    if not os.path.exists(directory):
        directory.mkdir()
    file = directory / 'test.txt'
    Path(file).touch()
    return directory, file

def test_file_class(tmp_path):
    video_file = create_test_video_file(tmp_path)
    nonvideo_file = create_test_nonvideo_file(tmp_path)
    file = File(video_file)
    nfile = File(nonvideo_file)
    assert file.path == video_file
    assert file.basename == 'test.mp4'
    assert file.name == 'test'
    assert file.ext == '.mp4'
    assert file.is_a_video_file
    assert file.height == 1080
    assert file.width == 1920
    assert file.vbitrate == 1000000
    assert file.abitrate == 192000
    assert nfile.path == nonvideo_file
    assert not nfile.is_a_video_file

def test_filepath_class(tmp_path):
    test_directory, test_file = create_test_filepath(tmp_path)
    non_exist_file = test_directory / 'idontexist.txt'
    directory = FilePath(test_directory)
    file = FilePath(test_file)
    nefile = FilePath(non_exist_file)
    assert directory.absolute == str(test_directory)
    assert directory.exists
    assert directory.is_dir
    assert not directory.is_file
    assert file.absolute == str(test_file)
    assert file.exists
    assert not file.is_dir
    assert file.is_file
    assert nefile.absolute == str(non_exist_file)
    assert not nefile.exists
    assert not nefile.is_dir
    assert not nefile.is_file
