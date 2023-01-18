import inputstreamhelper

class InputstreamItem(object):
    content_type = ''
    manifest_type = ''
    license_type = ''
    server_certificate = ''
    license_key = ''
    mimetype = ''
    manifest_update_parameter = ''
    license_flags = ''
    addon = ''
    
    def check(self):
        return False

class HLSFFMPEG(InputstreamItem):
    addon = 'inputstream.ffmpeg'
    manifest_type = 'hls'
    mimetype = 'application/vnd.apple.mpegurl'

    def check(self):
        return True

class HLSDirect(InputstreamItem):
    addon = 'inputstream.ffmpegdirect'
    manifest_type = 'hls'
    mimetype = 'application/vnd.apple.mpegurl'

    def check(self):
        return True

class HLS(InputstreamItem):
    addon = 'inputstream.adaptive'
    manifest_type = 'hls'
    mimetype = 'application/vnd.apple.mpegurl'

    def check(self):
        return True

class MPD(InputstreamItem):
    addon = 'inputstream.adaptive'
    manifest_type = 'mpd'
    mimetype = 'application/dash+xml'

    def check(self):
        return True

class Playready(InputstreamItem):
    addon = 'inputstream.adaptive'
    manifest_type = 'ism'
    license_type = 'com.microsoft.playready'
    mimetype = 'application/vnd.ms-sstr+xml'

    def check(self):
        return True

class Widevine(InputstreamItem):
    addon = 'inputstream.adaptive'
    manifest_type = 'mpd'
    license_type = 'com.widevine.alpha'
    mimetype = 'application/dash+xml'

    def __init__(self, server_certificate=None, license_key=None, license_flags=None, content_type='application/octet-stream', challenge='R{SSM}', response='', manifest_update_parameter=None):
        self.server_certificate = server_certificate
        self.license_key = license_key
        self.license_flags = license_flags
        self.content_type = content_type
        self.challenge = challenge
        self.response = response
        self.manifest_update_parameter = manifest_update_parameter

    def check(self):
        return install_widevine()
    
def install_widevine():
    is_helper = inputstreamhelper.Helper('mpd', drm='com.widevine.alpha')    
    return is_helper._check_drm()