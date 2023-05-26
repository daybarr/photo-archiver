#!/usr/bin/env python
import argparse
import errno
import logging
import os
import pathlib
import re
import shutil
import sys

import exifread

logger = logging.getLogger(__name__)

DROPBOX_RE = re.compile(
r'''
^
(?P<year>\d\d\d\d)-
(?P<month>\d\d)-
\d\d
\ \d\d\.
\d\d\.
\d\d
(?:-\d+)?            # Optional integer suffix if same second
\.
[^\.]+               # Extension
$
''', re.X)

SAMSUNG_RE = re.compile(
r'''
^(?:IMG|VID)_
(?P<year>\d\d\d\d)
(?P<month>\d\d)
(?P<day>\d\d)
_
(?P<hour>\d\d)
(?P<minute>\d\d)
(?P<second>\d\d)
\.
(?P<extension>[^\.]+)
$
''', re.X)

EXIF_DATETIME_RE = re.compile(
r'''
^(?P<year>\d\d\d\d):
(?P<month>\d\d):
(?P<day>\d\d)
\ (?P<hour>\d\d):
(?P<minute>\d\d):
(?P<second>\d\d)
$''', re.X)

class Archiver(object):
    def __init__(self, src_dir, archive_dir):
        self.src_dir = os.path.abspath(src_dir)
        self.archive_dir = os.path.abspath(archive_dir)

    def dropbox_matcher(self, file_path, file_name):
        match = DROPBOX_RE.match(file_name)
        if match is None:
            return None

        return file_name, match.group('year'), match.group('month')

    def samsung_matcher(self, file_path, file_name):
        match = SAMSUNG_RE.match(file_name)
        if match is None:
            return None

        logger.debug('Samsung match: %r', match.groupdict())
        new_file_name = '{year}-{month}-{day} {hour}.{minute}.{second}.{extension}'.format(**
            match.groupdict())
        return new_file_name, match.group('year'), match.group('month')

    def exif_matcher(self, file_path, file_name):
        with open(file_path, 'rb') as fh:
            tags = exifread.process_file(fh)
        # logger.debug('Exif: %s', "\n".join(sorted(tags.keys())))
        tag = tags.get('EXIF DateTimeOriginal')
        if tag and tag.field_type == 2:
            logger.debug('datetime: %r', tag.values)
            match = EXIF_DATETIME_RE.match(tag.values)
            if match:
                extension = os.path.splitext(file_name)[1].lower()
                logger.debug('%r', match.groupdict())
                new_file_name = '{year}-{month}-{day} {hour}.{minute}.{second}{extension}'.format(
                    extension=extension, **match.groupdict())
                return new_file_name, match.group('year'), match.group('month')
        return None

    def archive_file(self, file_path, match_result):
        dest_file_name, year, month = match_result

        dest_dir_name = "{}-{}".format(year, month)
        dest_dir_path = os.path.join(self.archive_dir, dest_dir_name)
        dest_file_path = os.path.join(dest_dir_path, dest_file_name)

        logger.info('Moving %s => %s', file_path, dest_file_path)
        logger.debug('Creating target dir %s', dest_dir_path)
        pathlib.Path(dest_dir_path).mkdir(parents=True, exist_ok=True)
        logger.debug('Moving %s', file_path)
        shutil.move(file_path, dest_file_path)

    def run(self):
        matchers = (
            self.dropbox_matcher,
            self.samsung_matcher,
            self.exif_matcher
        )
        for file_name in os.listdir(self.src_dir):
            file_path = os.path.join(self.src_dir, file_name)
            if not os.path.isfile(file_path):
                continue
            print(file_path)
            for matcher in matchers:
                result = matcher(file_path, file_name)
                if result is not None:
                    self.archive_file(file_path, result)
                    break

def main(args):
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger('exifread').setLevel(logging.INFO)
    archiver = Archiver(args.source_dir, args.archive_dir)
    archiver.run()

def parse_args(argv):
    parser = argparse.ArgumentParser(description='Archive some photos')
    parser.add_argument(
        'source_dir', metavar='SRC_DIR',
        help='the directory to source photos from'
    )
    parser.add_argument(
        'archive_dir', metavar='DEST_DIR',
        help='the directory to move photos to in a date-based hierarchy'
    )
    return parser.parse_args(argv[1:])

if __name__ == "__main__":
    args = parse_args(sys.argv)
    main(args)
