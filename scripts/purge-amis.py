#!/usr/bin/python
#
# purge-amis - Delete old versions of buildslave AMIs
#
# Copyright (c) 2014 Benjamin Gilbert
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of version 2 of the GNU General Public License as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
# or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.
#

import boto

IMAGE_TYPE = 'openslide-buildslave'

if __name__ == '__main__':
    conn = boto.connect_ec2()
    images = conn.get_all_images(owners=['self'],
            filters={'tag:Type': IMAGE_TYPE})
    by_name = {}
    for image in images:
        by_name.setdefault(image.tags['Name'], []).append(image)
    for group in by_name.values():
        for image in sorted(group, key=lambda i: i.location)[:-1]:
            print 'Deleting', image.id
            image.deregister()
            for device in image.block_device_mapping.values():
                if device.snapshot_id:
                    conn.delete_snapshot(device.snapshot_id)
