#!/usr/bin/python
#
# create-amis - Create buildslave AMIs from prototype instances
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
from boto.ec2.blockdevicemapping import BlockDeviceMapping, BlockDeviceType
from boto.exception import EC2ResponseError
from datetime import datetime
import sys
import time

IMAGE_TYPE = 'openslide-buildslave'
VOLUME_SIZE = 300  # GB

class ConfigError(Exception):
    pass


def create_image(name, terminate=False):
    # Find instance
    reservations = conn.get_all_instances(filters={'tag:Name': name})
    instances = [i for r in reservations for i in r.instances
            if i.state != 'terminated']
    if not instances:
        raise ConfigError('not found')
    elif len(instances) > 1:
        raise ConfigError('found %d instances' % len(instances))
    instance = instances[0]

    # Configure block device
    if len(instance.block_device_mapping) != 1:
        raise ConfigError('found multiple block devices')
    device_node = instance.block_device_mapping.keys()[0]
    mapping = BlockDeviceMapping()
    mapping[device_node] = BlockDeviceType(
        volume_type='gp2',
        size=VOLUME_SIZE,
        delete_on_termination=True,
    )

    # Create image
    timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
    image_id = conn.create_image(instance.id, '%s-%s' % (name, timestamp),
            block_device_mapping=mapping)
    for i in range(20, -1, -1):
        try:
            image = conn.get_all_images([image_id])[0]
        except EC2ResponseError:
            if i:
                time.sleep(2)
            else:
                raise
    while image.state == 'pending':
        time.sleep(5)
        image.update()

    # Add tags
    image.add_tag('Name', name)
    image.add_tag('Type', IMAGE_TYPE)
    for device in image.block_device_mapping.values():
        if device.snapshot_id is None:
            continue
        snapshot = conn.get_all_snapshots([device.snapshot_id])[0]
        snapshot.add_tag('Name', name)

    # Terminate instance, if requested
    if terminate:
        instance.terminate()

    return image_id


if __name__ == '__main__':
    if len(sys.argv) == 1:
        print >>sys.stderr, "Usage: %s [-t] instance-names" % sys.argv[0]
        print >>sys.stderr, "    -t  Terminate instances afterward"
        sys.exit(1)
    conn = boto.connect_ec2()
    instances = sys.argv[1:]
    try:
        instances.remove('-t')
        terminate = True
    except ValueError:
        terminate = False
    for name in instances:
        try:
            image_id = create_image(name, terminate)
            print '%s: %s' % (name, image_id)
        except ConfigError, e:
            print >>sys.stderr, '%s: %s' % (name, e)
