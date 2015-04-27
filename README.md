This repository contains infrastructure for automatically building and
testing OpenSlide.


## Buildmaster configuration

### stunnel

Buildslave connections to the master are wrapped with stunnel and
authenticated with a PKI (and also with Buildbot-level buildslave
passwords).  Use easy-rsa to set up the PKI.  On Debian, the
master-side stunnel configuration looks like this:

```
pid = /var/run/stunnel4/stunnel.pid
setuid = stunnel4
setgid = stunnel4

[openslide_buildbot]
CAfile = /etc/stunnel/buildbot-ca.crt
cert = /etc/stunnel/buildbot.crt
key = /etc/stunnel/buildbot.key
verify = 2
options = NO_SSLv2
options = NO_SSLv3
accept  = 2000
connect = 9989
```


### Buildbot

1. Create a user account to run the buildmaster.
2. Clone this repo into the account's home directory.
3. Install `libaprutil`.
4. Download a source tarball of Buildbot.
5. Use quilt to apply the patches from the
   [buildbot-patches](buildbot-patches) directory:

    ```
cd buildbot-0.8.xx
ln -s .../openslide-automation/buildbot-patches patches
quilt push -a
```
6. `pip install` the unpacked source tree into a virtualenv in the
   user account's home directory.


### nginx

```
server {
    listen 443 ssl default_server;
    server_name buildbot.openslide.org;

    location /results/ {
        root [...]/openslide-automation/buildmaster/public_html;
    }

    location /snapshots/ {
        root [...]/openslide-automation/buildmaster/public_html;
    }

    location / {
        proxy_pass http://localhost:8010;
        # Ensure log streaming works correctly
        proxy_buffering off;
    }
}
```


### buildmaster/local.ini

```
[email]
## Email addresses for notifications.  Multiple addresses can be supplied,
## separated by commas.
# Notified on buildslave problems
admins: <emails>
# Notified on nightly snapshot build failures
snapshot-builds: <emails>
# Notified when release tasks complete
release-tasks: <emails>

[github]
secret: <webhook-HMAC-secret>

[aws]
account: <AWS-account-number>
access-key: <AWS-access-key-id>
secret-key: <AWS-secret-access-key>

[slaves]
<buildslave-name>: <buildslave-password>
```


### buildmaster/changehook.password

```
buildbot:<GitHub-changehook-password>
```


### buildmaster/users

`htpasswd`-format file with username/password pairs for website login.


### cron

```
@reboot $HOME/env/bin/buildbot start $HOME/openslide-automation/buildmaster
# Garbage-collect old logs/build artifacts
0 0 * * * $HOME/openslide-automation/scripts/prune-buildmaster.sh $HOME/openslide-automation/buildmaster
```


### GitHub

The GitHub organization is configured with a webhook:

| Field | Value |
|-------|-------|
| Payload URL | `https://buildbot:<GitHub-changehook-password>@buildbot.openslide.org/change_hook/github` |
| Content Type | `application/json` |
| Secret | `<webhook-HMAC-secret>` |
| Events | Just the push event |


## Buildslave configuration

Setup notes are
[on the wiki](https://github.com/openslide/openslide/wiki/Buildbot).
