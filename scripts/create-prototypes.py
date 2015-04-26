#!/usr/bin/python
#
# create-prototypes - Create prototype instances from buildslave AMIs
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
INSTANCE_TYPES = {
    # f21-ia32 fails to boot on m1.medium due to kernel problems
    'i386': 'm1.small',
    'x86_64': 'm3.medium',
}
SECURITY_GROUP = 'openslide-buildslave'
INSTANCE_PROFILE = 'openslide-buildslave'

class ConfigError(Exception):
    pass


def create_instance(name):
    # Find instance
    images = conn.get_all_images(owners='self', filters={
        'tag:Name': name,
        'tag:Type': IMAGE_TYPE,
    })
    if not images:
        raise ConfigError('image not found')
    images.sort(key=lambda i: i.location)
    image = images[-1]
    if len(images) > 1:
        print >>sys.stderr, '%s: selecting %s' % (name, image.name)

    # Configure block device
    if len(image.block_device_mapping) != 1:
        raise ConfigError('found multiple block devices')
    device_node = image.block_device_mapping.keys()[0]
    mapping = BlockDeviceMapping()
    mapping[device_node] = BlockDeviceType(
        snapshot_id=image.block_device_mapping[device_node].snapshot_id,
        volume_type='gp2',
        delete_on_termination=True,
    )

    # EC2 doesn't let us launch an instance with a volume smaller than the
    # size listed in the image's block device mapping, so we have to create
    # a temporary image.
    timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
    temp_image_id = conn.register_image(name='temp-%s-%s' % (name, timestamp),
            architecture=image.architecture, kernel_id=image.kernel_id,
            ramdisk_id=image.ramdisk_id, root_device_name=device_node,
            block_device_map=mapping,
            virtualization_type=image.virtualization_type)
    for i in range(20, -1, -1):
        try:
            temp_image = conn.get_all_images([temp_image_id])[0]
        except EC2ResponseError:
            if i:
                time.sleep(2)
            else:
                raise
    while temp_image.state == 'pending':
        time.sleep(5)
        temp_image.update()

    # Create instance
    reservation = temp_image.run(
            instance_type=INSTANCE_TYPES[image.architecture],
            security_groups=[SECURITY_GROUP],
            instance_profile_name=INSTANCE_PROFILE)
    instance = reservation.instances[0]
    while instance.state == 'pending':
        time.sleep(5)
        instance.update()
    instance.add_tag('Name', name)

    # Delete temporary image
    temp_image.deregister()

    return instance.id, instance.public_dns_name


if __name__ == '__main__':
    if len(sys.argv) == 1:
        print >>sys.stderr, "Usage: %s image-names" % sys.argv[0]
        sys.exit(1)
    conn = boto.connect_ec2()
    for name in sys.argv[1:]:
        try:
            instance_id, hostname = create_instance(name)
            print '%s: %s, %s' % (name, instance_id, hostname)
        except ConfigError, e:
            print >>sys.stderr, '%s: %s' % (name, e)
