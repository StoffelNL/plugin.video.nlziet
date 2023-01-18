import json, os, shutil, sys, time, xbmc, xbmcaddon, xbmcplugin

from functools import wraps
from resources.lib.api import api_clean_after_playback, api_get_info
from resources.lib.base.l1.constants import ADDON_ICON, ADDON_FANART, ADDON_ID, ADDON_NAME, ADDON_PROFILE, DEFAULT_USER_AGENT
from resources.lib.base.l2 import settings
from resources.lib.base.l2.log import log
from resources.lib.base.l3.language import _
from resources.lib.base.l3.util import encode_obj, json_rpc, load_file, remove_dir, remove_file, upnext_signal, write_file
from resources.lib.base.l4 import gui
from resources.lib.base.l4.exceptions import PluginError
from resources.lib.base.l5 import signals
from resources.lib.base.l6 import inputstream, router
from resources.lib.util import plugin_get_device_id
from urllib.parse import urlencode

## SHORTCUTS
url_for = router.url_for
dispatch = router.dispatch
############

def exception(msg=''):
    raise PluginError(msg)

# @plugin.route()
def route(url=None):
    def decorator(f, url):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            item = f(*args, **kwargs)

            if isinstance(item, Folder):
                item.display()
            elif isinstance(item, Item):
                item.play()
            else:
                resolve()

        router.add(url, decorated_function)
        return decorated_function
    return lambda f: decorator(f, url)

def resolve():
    if _handle() > 0:
        xbmcplugin.endOfDirectory(_handle(), succeeded=False, updateListing=False, cacheToDisc=False)

@signals.on(signals.ON_ERROR)
def _error(e):
    try:
        error = str(e)
    except:
        error = e.message.encode('utf-8')

    if not hasattr(e, 'heading') or not e.heading:
        e.heading = _(_.PLUGIN_ERROR, addon=ADDON_NAME)

    log.error(error)
    _close()

    gui.ok(error, heading=e.heading)
    resolve()

@signals.on(signals.ON_EXCEPTION)
def _exception(e):
    log.exception(e)
    _close()
    gui.exception()
    resolve()

@route('')
def _home(**kwargs):
    raise PluginError(_.PLUGIN_NO_DEFAULT_ROUTE)

@route('_ia_install')
def _ia_install(**kwargs):
    _close()
    inputstream.install_widevine()

def reboot():
    _close()
    xbmc.executebuiltin('RestartApp')

@signals.on(signals.AFTER_DISPATCH)
def _close():
    signals.emit(signals.ON_CLOSE)

@route('_settings')
def _settings(**kwargs):
    _close()
    settings.open()
    gui.refresh()

@route('_set_network_bandwidth')
def _set_network_bandwidth(**kwargs):
    method = 'settings.GetSettingValue'
    cursetting = json_rpc(method, {"setting":"network.bandwidth"})

    if not cursetting['value'] == int(settings.getInt(key='max_bandwidth')):
        method = 'settings.SetSettingValue'
        json_rpc(method, {"setting":"network.bandwidth","value": "{}".format(settings.getInt(key='max_bandwidth'))})
        write_file('bandwidth', data=cursetting['value'], isJSON=False)

    try:
        cursetting = xbmcaddon.Addon('inputstream.ffmpegdirect').getSetting('streamBandwidth')

        if not int(cursetting) == int(settings.getInt(key='max_bandwidth')):
            xbmcaddon.Addon('inputstream.ffmpegdirect').setSetting('streamBandwidth', str(settings.getInt(key='max_bandwidth')))
            write_file('bandwidth2', data=cursetting, isJSON=False)
    except:
        pass

@route('_restore_network_bandwidth')
def _restore_network_bandwidth(**kwargs):
    bandwidth = load_file('bandwidth', isJSON=False)

    if bandwidth:
        method = 'settings.SetSettingValue'
        json_rpc(method, {"setting":"network.bandwidth","value": "{}".format(bandwidth)})

    try:
        os.remove(os.path.join(ADDON_PROFILE, 'bandwidth'))
    except:
        pass

    bandwidth2 = load_file('bandwidth2', isJSON=False)

    if bandwidth2:
        try:
            xbmcaddon.Addon('inputstream.ffmpegdirect').setSetting('streamBandwidth', str(bandwidth2))
        except:
            pass

    try:
        os.remove(os.path.join(ADDON_PROFILE, 'bandwidth2'))
    except:
        pass

@route('_set_settings_kodi')
def _set_settings_kodi(**kwargs):
    _close()

    try:
        method = 'settings.SetSettingValue'

        json_rpc(method, {"setting":"videoplayer.preferdefaultflag", "value": "true"})
        json_rpc(method, {"setting":"videoplayer.preferdefaultflag", "value": "true"})
        json_rpc(method, {"setting":"locale.audiolanguage", "value": "default"})
        json_rpc(method, {"setting":"locale.subtitlelanguage", "value":"default"})
        json_rpc(method, {"setting":"pvrmanager.preselectplayingchannel", "value": "false"})
        json_rpc(method, {"setting":"pvrmanager.syncchannelgroups", "value": "true"})
        json_rpc(method, {"setting":"pvrmanager.backendchannelorder", "value": "true"})
        json_rpc(method, {"setting":"pvrmanager.usebackendchannelnumbers", "value": "true"})
        json_rpc(method, {"setting":"epg.selectaction", "value":5})
        json_rpc(method, {"setting":"epg.pastdaystodisplay", "value":7})
        json_rpc(method, {"setting":"epg.futuredaystodisplay", "value":1})
        json_rpc(method, {"setting":"epg.hidenoinfoavailable", "value": "true"})
        json_rpc(method, {"setting":"epg.epgupdate", "value":720})
        json_rpc(method, {"setting":"epg.preventupdateswhileplayingtv", "value": "true"})
        json_rpc(method, {"setting":"epg.ignoredbforclient", "value": "true"})
        json_rpc(method, {"setting":"pvrrecord.instantrecordaction", "value":2})
        json_rpc(method, {"setting":"pvrpowermanagement.enabled", "value": "false"})
        json_rpc(method, {"setting":"pvrparental.enabled", "value": "false"})

        gui.notification(_.DONE_NOREBOOT)
    except:
        pass

@route('_reset')
def _reset(**kwargs):
    if not gui.yes_no(_.PLUGIN_RESET_YES_NO):
        return

    _close()

    try:
        method = 'Addons.SetAddonEnabled'
        json_rpc(method, {"addonid": ADDON_ID, "enabled": "false"})

        remove_dir(directory="cache", ext=False)
        remove_dir(directory="tmp", ext=False)

        for file in glob.glob(os.path.join(ADDON_PROFILE, "stream*")):
            remove_file(file=file, ext=True)

        for file in glob.glob(os.path.join(ADDON_PROFILE, "*.json")):
            remove_file(file=file, ext=True)

        for file in glob.glob(os.path.join(ADDON_PROFILE, "*.xml")):
            remove_file(file=file, ext=True)

        if not os.path.isdir(os.path.join(ADDON_PROFILE, "cache")):
            os.makedirs(os.path.join(ADDON_PROFILE, "cache"))

        if not os.path.isdir(os.path.join(ADDON_PROFILE, "tmp")):
            os.makedirs(os.path.join(ADDON_PROFILE, "tmp"))

        if not os.path.isdir(os.path.join(ADDON_PROFILE, "movies")):
            os.makedirs(os.path.join(ADDON_PROFILE, "movies"))

        if not os.path.isdir(os.path.join(ADDON_PROFILE, "shows")):
            os.makedirs(os.path.join(ADDON_PROFILE, "shows"))
    except:
        pass

    method = 'Addons.SetAddonEnabled'
    json_rpc(method, {"addonid": ADDON_ID, "enabled": "true"})

    gui.notification(_.PLUGIN_RESET_OK)
    signals.emit(signals.AFTER_RESET)
    gui.refresh()

def _handle():
    try:
        return int(sys.argv[1])
    except:
        return -1

#Plugin.Item()
class Item(gui.Item):
    def __init__(self, cache_key=None, playback_error=None, *args, **kwargs):
        super(Item, self).__init__(self, *args, **kwargs)
        self.cache_key = cache_key
        self.playback_error = playback_error

    def get_li(self):
        return super(Item, self).get_li()

    def play(self):
        try:
            if 'seekTime' in self.properties or sys.argv[3] == 'resume:true':
                self.properties.pop('ResumeTime', None)
                self.properties.pop('TotalTime', None)
        except:
            pass

        device_id = plugin_get_device_id

        if not device_id:
            method = 'settings.GetSettingValue'
            cursetting = {}
            cursetting['debug.extralogging'] = json_rpc(method, {"setting":"debug.extralogging"})['value']
            cursetting['debug.showloginfo'] = json_rpc(method, {"setting":"debug.showloginfo"})['value']
            cursetting['debug.setextraloglevel'] = json_rpc(method, {"setting":"debug.setextraloglevel"})['value']

            method = 'settings.SetSettingValue'
            json_rpc(method, {"setting":"debug.extralogging", "value": "true"})
            json_rpc(method, {"setting":"debug.showloginfo", "value": "true"})
            json_rpc(method, {"setting":"debug.setextraloglevel", "value":[64]})

        if settings.getBool(key='disable_subtitle'):
            self.properties['disable_subtitle'] = 1

        li = self.get_li()
        handle = _handle()

        #if 'seekTime' in self.properties:
            #li.setProperty('ResumeTime', str(self.properties['seekTime']))

            #if 'totalTime' in self.properties:
            #    li.setProperty('TotalTime', str(self.properties['totalTime']))
            #else:
            #    li.setProperty('TotalTime', '999999')

        player = MyPlayer()

        playbackStarted = False
        seekTime = False
        replay_pvr = False

        if handle > 0:
            if 'Replay' in self.properties or 'PVR' in self.properties:
                replay_pvr = True
                self.properties.pop('Replay', None)
                self.properties.pop('PVR', None)
                xbmcplugin.setResolvedUrl(handle, True, li)
            else:
                xbmcplugin.setResolvedUrl(handle, False, li)
                player.play(self.path, li)
        else:
            player.play(self.path, li)

        currentTime = 0
        upnext = settings.getBool('upnext_enabled')

        while player.is_active:
            if xbmc.getCondVisibility("Player.HasMedia") and player.is_started:
                if playbackStarted == False:
                    playbackStarted = True

                if upnext:
                    upnext = False
                    result = json_rpc("XBMC.GetInfoLabels", {"labels":["VideoPlayer.DBID", "VideoPlayer.TvShowDBID"]})

                    if result and len(str(result['VideoPlayer.DBID'])) > 0 and len(str(result['VideoPlayer.TvShowDBID'])) > 0:
                        result2 = json_rpc("VideoLibrary.GetEpisodes", {"tvshowid": int(result['VideoPlayer.TvShowDBID']), "properties":[ "title", "plot", "rating", "firstaired", "playcount", "runtime", "season", "episode", "showtitle", "fanart", "thumbnail", "art"]})
                        nextep = 0
                        current_episode = dict()
                        next_episode = dict()

                        if result2:                       
                            for result3 in result2['episodes']:
                                if nextep == 0 and int(result3['episodeid']) == int(result['VideoPlayer.DBID']):                                    
                                    current_episode=dict(
                                        episodeid=result3['episodeid'],
                                        tvshowid=int(result['VideoPlayer.TvShowDBID']),
                                        title=result3["title"],
                                        art=result3["art"],
                                        season=result3["season"],
                                        episode=result3["episode"],
                                        showtitle=result3["showtitle"],
                                        plot=result3["plot"],
                                        playcount=result3["playcount"],
                                        rating=result3["rating"],
                                        firstaired=result3["firstaired"],
                                        runtime=result3["runtime"]
                                    )
                                    
                                    nextep = 1
                                elif nextep == 1:                                   
                                    params = []
                                    params.append(('_', 'play_dbitem'))
                                    params.append(('id', result3['episodeid']))

                                    path = 'plugin://{0}/?{1}'.format(ADDON_ID, urlencode(encode_obj(params)))
                                    
                                    next_info = dict(
                                        current_episode=current_episode,
                                        next_episode=dict(
                                            episodeid=result3['episodeid'],
                                            tvshowid=int(result['VideoPlayer.TvShowDBID']),
                                            title=result3["title"],
                                            art=result3["art"],
                                            season=result3["season"],
                                            episode=result3["episode"],
                                            showtitle=result3["showtitle"],
                                            plot=result3["plot"],
                                            playcount=result3["playcount"],
                                            rating=result3["rating"],
                                            firstaired=result3["firstaired"],
                                            runtime=result3["runtime"]
                                        ),
                                        play_url=path,
                                        #notification_time=60, 
                                        #notification_offset=notification_offset,
                                    )
                                    
                                    upnext_signal(sender=ADDON_ID, next_info=next_info)
                                    #upnext_signal(sender=ADDON_ID)
                                    break

                if not device_id:
                    player.stop()

                if 'disable_subtitle' in self.properties:
                    player.showSubtitles(False)
                    self.properties.pop('disable_subtitle', None)

                if 'seekTime' in self.properties:
                    seekTime = True
                    xbmc.Monitor().waitForAbort(1)
                    player.seekTime(int(self.properties['seekTime']))
                    self.properties.pop('seekTime', None)

                if not replay_pvr and not seekTime and 'Live' in self.properties and 'Live_ID' in self.properties and 'Live_Channel' in self.properties:
                    id = self.properties['Live_ID']
                    channel = self.properties['Live_Channel']

                    self.properties.pop('Live', None)
                    self.properties.pop('Live_ID', None)
                    self.properties.pop('Live_Channel', None)

                    wait = 60

                    end = load_file(file='stream_end', isJSON=False)

                    if end:
                        calc_wait = int(end) - int(time.time()) + 30

                        if calc_wait > 60:
                            wait = calc_wait

                    while not xbmc.Monitor().waitForAbort(wait) and xbmc.getCondVisibility("Player.HasMedia") and player.is_started:
                        info = None

                        try:
                            info = api_get_info(id=id, channel=channel)
                        except:
                            pass

                        if info:
                            info2 = {
                                'plot': str(info['description']),
                                'title': str(info['label1']),
                                'tagline': str(info['label2']),
                                'duration': info['duration'],
                                'credits': info['credits'],
                                'cast': info['cast'],
                                'director': info['director'],
                                'writer': info['writer'],
                                'genre': info['genres'],
                                'year': info['year'],
                            }

                            li.setInfo('video', info2)

                            li.setArt({'thumb': info['image'], 'icon': info['image'], 'fanart': info['image_large'] })

                            try:
                                player.updateInfoTag(li)
                            except:
                                pass

                            wait = 60
                            end = load_file(file='stream_end', isJSON=False)

                            if end:
                                calc_wait = int(end) - int(time.time()) + 30

                                if calc_wait > 60:
                                    wait = calc_wait

            xbmc.Monitor().waitForAbort(1)

            try:
                currentTime = player.getTime()
            except:
                pass

        if playbackStarted == True:
            api_clean_after_playback(int(currentTime))

            try:
                if settings.getInt(key='max_bandwidth') > 0:
                    _restore_network_bandwidth()
            except:
                pass

        if not device_id:
            json_rpc(method, {"setting":"debug.showloginfo", "value": cursetting['debug.showloginfo']})
            json_rpc(method, {"setting":"debug.setextraloglevel", "value": str(', '.join([str(elem) for elem in cursetting['debug.setextraloglevel']]))})
            json_rpc(method, {"setting":"debug.extralogging", "value": cursetting['debug.setextraloglevel']})

class MyPlayer(xbmc.Player):
    def __init__(self):
        self.is_active = True
        self.is_started = False

    def onPlayBackPaused(self):
        pass

    def onPlayBackResumed(self):
        pass

    def onPlayBackStarted(self):
        self.is_started = True

    def onPlayBackEnded(self):
        self.is_active = False

    def onPlayBackStopped(self):
        self.is_active = False

    def sleep(self, s):
        xbmc.sleep(s)

#Plugin.Folder()
class Folder(object):
    def __init__(self, items=None, title=None, content='videos', updateListing=False, cacheToDisc=True, sort_methods=None, thumb=None, fanart=None, no_items_label=_.NO_ITEMS):
        self.items = items or []
        self.title = title
        self.content = content
        self.updateListing = updateListing
        self.cacheToDisc = cacheToDisc
        self.sort_methods = sort_methods or [xbmcplugin.SORT_METHOD_UNSORTED]
        self.thumb = thumb or ADDON_ICON
        self.fanart = fanart or ADDON_FANART
        self.no_items_label = no_items_label

    def display(self):
        handle = _handle()
        items = [i for i in self.items if i]

        if not items and self.no_items_label:
            items.append(Item(
                label = _(self.no_items_label, _label=True),
                is_folder = False,
            ))

        for item in items:
            item.art['thumb'] = item.art.get('thumb') or self.thumb
            item.art['fanart'] = item.art.get('fanart') or self.fanart

            li = item.get_li()
            xbmcplugin.addDirectoryItem(handle, item.path, li, item.is_folder)

        if self.content: xbmcplugin.setContent(handle, self.content)
        if self.title: xbmcplugin.setPluginCategory(handle, self.title)

        for sort_method in self.sort_methods:
            xbmcplugin.addSortMethod(handle, sort_method)

        xbmcplugin.endOfDirectory(handle, succeeded=True, updateListing=self.updateListing, cacheToDisc=self.cacheToDisc)

    def add_item(self, *args, **kwargs):
        position = kwargs.pop('_position', None)

        item = Item(*args, **kwargs)

        if position == None:
            self.items.append(item)
        else:
            self.items.insert(int(position), item)

        return item

    def add_items(self, items):
        if isinstance(items, list):
            self.items.extend(items)
        elif isinstance(items, Item):
            self.items.append(items)
        else:
            raise Exception('add_items only accepts an Item or list of Items')