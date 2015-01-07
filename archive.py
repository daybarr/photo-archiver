#!/usr/bin/env python
from __future__ import print_function

import errno
import logging
import os
import re
import shutil

logger = logging.getLogger(__name__)

DROPBOX_RE = re.compile(r'''
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

SAMSUNG_RE = re.compile(r'''
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


def mkdir_p(dir_path):
    try:
        os.makedirs(dir_path)
    except os.error as err:
        if err.errno != errno.EEXIST:
            raise
        logger.debug('%s already exists', dir_path)

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

    def archive_file(self, file_path, match_result):
        dest_file_name, year, month = match_result

        dest_dir_name = "{}-{}".format(year, month)
        dest_dir_path = os.path.join(self.archive_dir, dest_dir_name)
        dest_file_path = os.path.join(dest_dir_path, dest_file_name)

        logger.info('Moving %s => %s', file_path, dest_file_path)
        logger.debug('Creating target dir %s', dest_dir_path)
        mkdir_p(dest_dir_path)
        logger.debug('Moving %s', file_path)
        shutil.move(file_path, dest_file_path)

    def run(self):
        matchers = (
            self.dropbox_matcher,
            self.samsung_matcher
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

def main(src_dir, archive_dir):
    logging.basicConfig(level=logging.DEBUG)
    archiver = Archiver(src_dir, archive_dir)
    archiver.run()

if __name__ == "__main__":
    main('.', '.')
